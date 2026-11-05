#!/usr/bin/env python3
"""Portable streaming stage recorder. No project imports or service credentials."""
import hashlib
import json
import os
from pathlib import Path
import resource
import re
import signal
import subprocess
import sys
import threading
import time


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    data = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    with Path(path).open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def validate_stage_name(name):
    # Single ASCII path component; version dots are legal, traversal/separators are not.
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,119}', name):
        raise ValueError('invalid stage name')


def display_output(line):
    # Display only: legacy Actions commands can be recognized anywhere in a line.
    # Escape CR too so the runner cannot split away the modern-command prefix.
    text = line.decode('utf-8', errors='replace').replace('\r', r'\r')
    return '| ' + text.replace('##[', r'##\x5b')


class Recorder:
    def __init__(self, directory, deadline=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.deadline = deadline
        self.receipts = []

    def run(self, name, argv, cwd, env, timeout=1800, stdout_file=None, required_text=None):
        """Emit full textual output with a harmless prefix; preserve raw bytes locally."""
        validate_stage_name(name)
        folder = self.directory / name
        folder.mkdir(exist_ok=False)
        started = time.time()
        cpu0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        if self.deadline is not None:
            timeout = min(timeout, max(0.01, self.deadline - time.monotonic()))
        prepared = {'schema': 'eth-ci-stage/1', 'name': name, 'argv': list(map(str, argv)),
                    'cwd': str(cwd), 'started_utc_epoch': started, 'timeout_seconds': timeout,
                    'stdout_is_export': stdout_file is not None,
                    'child_cpu_scope': 'Reaped subprocesses only; excludes systemd-managed service CPU. Read systemd runtime/CPU accounting in raw log.'}
        write_json(folder / 'prepared.json', prepared)
        print('STAGE_START ' + json.dumps(prepared, sort_keys=True), flush=True)
        raw = (folder / 'raw.log').open('xb')
        export = Path(stdout_file).open('xb') if stdout_file else None
        proc = None
        reason = None
        errors = []
        def pump(stream, destination, echo):
            try:
                for line in iter(stream.readline, b''):
                    destination.write(line)
                    destination.flush()
                    os.fsync(destination.fileno())
                    if echo:
                        # Neutralize both Actions command syntaxes in display; retain raw bytes above.
                        sys.stdout.write(display_output(line))
                        sys.stdout.flush()
            except BaseException as e:
                errors.append(repr(e))
            finally:
                stream.close()
        try:
            proc = subprocess.Popen(list(map(str, argv)), cwd=cwd, env=env,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE if export else subprocess.STDOUT,
                                    start_new_session=True)
            workers = [threading.Thread(target=pump, args=(proc.stdout, export or raw, not export), daemon=True)]
            if export:
                workers.append(threading.Thread(target=pump, args=(proc.stderr, raw, True), daemon=True))
            for worker in workers:
                worker.start()
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                reason = 'stage timeout'
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                code = 124
            for worker in workers:
                worker.join(timeout=10)
                if worker.is_alive():
                    errors.append('output pipe remained open after child exit')
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    worker.join(timeout=5)
            if errors:
                reason = '; '.join(errors)
                code = 125
        except BaseException as e:
            reason = repr(e)
            code = 125
            if proc is not None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
            if isinstance(e, KeyboardInterrupt):
                reason = 'recorder interrupted'
        finally:
            raw.close()
            if export:
                export.close()
        cpu1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        if required_text is not None and code == 0:
            if required_text.encode() not in (folder / 'raw.log').read_bytes().splitlines():
                code, reason = 125, 'required exact success line missing'
        receipt = dict(prepared, exit_code=code, reason=reason,
                       wall_seconds=time.time() - started,
                       child_cpu_seconds=(cpu1.ru_utime + cpu1.ru_stime - cpu0.ru_utime - cpu0.ru_stime),
                       raw_log_sha256=sha(folder / 'raw.log'),
                       raw_log_bytes=(folder / 'raw.log').stat().st_size)
        if stdout_file:
            receipt['export'] = {'path': str(stdout_file), 'sha256': sha(stdout_file),
                                 'size_bytes': Path(stdout_file).stat().st_size}
        write_json(folder / 'finished.json', receipt)
        self.receipts.append(receipt)
        print('STAGE_RECEIPT ' + json.dumps(receipt, sort_keys=True), flush=True)
        if code:
            raise subprocess.CalledProcessError(code, argv)
        return receipt
