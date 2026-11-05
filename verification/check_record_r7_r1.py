#!/usr/bin/env python3
"""R7 staging-only recorder transport/timeout controls; no proof tools or services."""
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'ci/record.py'
CANDIDATE = HERE / 'ci-repair-candidate-r7/ci/record.py'
ORIGINAL_SHA = '1a7c9f9d8bbf7de0458e83ea0385a280c05db970b2e87493f3e85a6c06c361c0'
CANDIDATE_SHA = '753330742a44e50bd48ed4a0cd6b55b5998938475e7cb463c56e4e65979075f6'
CHUNK = 4 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    data = value if isinstance(value, bytes) else (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    wall = time.perf_counter()
    cpu = time.process_time()
    children0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    assert sha(ORIGINAL.read_bytes()) == ORIGINAL_SHA
    assert sha(CANDIDATE.read_bytes()) == CANDIDATE_SHA
    sys.dont_write_bytecode = True
    original = load(ORIGINAL, 'original_transport_recorder')
    candidate = load(CANDIDATE, 'candidate_transport_recorder')
    output = HERE / 'record-r7-controls-r1'
    output.mkdir(exist_ok=False)
    results = []
    env = {'PATH': os.defpath, 'LANG': 'C'}

    def run_case(label, module, payload, stderr=b'', exit_code=0, delay=0,
                 timeout=10, binary=True, required=None, inject_fsync=False):
        folder = output / label
        folder.mkdir()
        save(folder / 'payload.bin', payload)
        save(folder / 'stderr.bin', stderr)
        export = folder / 'export.bin' if binary else None
        child = (
            "import os,pathlib,sys,time; "
            "sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes()); sys.stdout.buffer.flush(); "
            "sys.stderr.buffer.write(pathlib.Path(sys.argv[2]).read_bytes()); sys.stderr.buffer.flush(); "
            "time.sleep(float(sys.argv[3])); sys.exit(int(sys.argv[4]))"
        )
        argv = [sys.executable, '-c', child, str(folder / 'payload.bin'),
                str(folder / 'stderr.bin'), str(delay), str(exit_code)]
        recorder = module.Recorder(folder / 'records')
        display = io.StringIO()
        fsync_calls = []
        real_fsync = os.fsync

        def counted_fsync(fd):
            if export is not None and export.exists():
                descriptor = os.fstat(fd)
                expected = export.stat()
                if (descriptor.st_dev, descriptor.st_ino) == (expected.st_dev, expected.st_ino):
                    fsync_calls.append(descriptor.st_size)
                    if inject_fsync:
                        raise OSError('injected export fsync failure')
            return real_fsync(fd)

        os.fsync = counted_fsync
        try:
            with contextlib.redirect_stdout(display):
                try:
                    receipt = recorder.run(label, argv, folder, env, timeout=timeout,
                                           stdout_file=export, required_text=required)
                    raised = None
                except subprocess.CalledProcessError as error:
                    raised = error.returncode
                    receipt = recorder.receipts[-1]
        finally:
            os.fsync = real_fsync
        save(folder / 'display.txt', display.getvalue().encode())
        raw = (folder / 'records' / label / 'raw.log').read_bytes()
        assert receipt['raw_log_sha256'] == sha(raw)
        assert receipt['raw_log_bytes'] == len(raw)
        expected_code = 125 if inject_fsync else 124 if delay else exit_code
        if required is not None and required.encode() not in raw.splitlines() and expected_code == 0:
            expected_code = 125
        assert receipt['exit_code'] == expected_code, receipt
        if module is candidate:
            assert receipt['timed_out'] is bool(delay)
        assert raised == (expected_code or None)
        if delay:
            assert receipt['reason'] == 'stage timeout'
        if inject_fsync:
            assert 'injected export fsync failure' in receipt['reason']
        if required is not None and expected_code == 125:
            assert receipt['reason'] == 'required exact success line missing'
        if expected_code == 0:
            assert receipt['reason'] is None
        if binary:
            actual = export.read_bytes()
            assert actual == payload
            assert raw == stderr, 'binary stdout and stderr must remain separate'
            assert receipt['export']['sha256'] == sha(payload)
            assert receipt['export']['size_bytes'] == len(payload)
            bound = math.ceil(len(payload) / CHUNK) + 1
            assert len(fsync_calls) <= bound
            if not inject_fsync:
                assert len(fsync_calls) == bound
        else:
            assert not stderr, 'parity fixture uses stdout only to avoid scheduling ambiguity'
            assert raw == payload and 'export' not in receipt
            assert not fsync_calls
        result = {
            'name': label, 'binary_export': binary, 'payload_bytes': len(payload),
            'payload_sha256': sha(payload), 'payload_newlines': payload.count(b'\n'),
            'stderr_bytes': len(stderr), 'stderr_sha256': sha(stderr),
            'expected_and_actual_exit': expected_code, 'raised_failure_code': raised,
            'export_fsync_calls': len(fsync_calls), 'export_fsync_sizes': fsync_calls,
            'expected_fsync_upper_bound': math.ceil(len(payload) / CHUNK) + 1 if binary else None,
            'receipt_path': str((folder / 'records' / label / 'finished.json').relative_to(ROOT)),
            'receipt_sha256': sha((folder / 'records' / label / 'finished.json').read_bytes()),
            'receipt': receipt, 'passed': True,
        }
        save(folder / 'result.json', result)
        results.append(result)
        return raw, display.getvalue(), receipt

    run_case('empty-export', candidate, b'')
    run_case('newline-heavy', candidate, b'{}\n' * 400000,
             stderr=b'separate-stderr\n')
    pattern = bytes(range(256))
    run_case('binary-two-boundaries', candidate,
             (pattern * ((2 * CHUNK + 257 + 255) // 256))[:2 * CHUNK + 257],
             stderr=b'\x00stderr-\xff\r\n')
    run_case('exact-chunk-boundary', candidate, b'\x00\xff' * (CHUNK // 2))
    run_case('nonzero-retains-bytes', candidate, b'failure-payload\x00\xff\n' * 2000,
             stderr=b'child-exits-seven\n', exit_code=7)
    run_case('timeout-retains-partial', candidate, b'partial-\x00\xff\n' * 1000,
             stderr=b'child-waits\n', delay=5, timeout=1.0)
    run_case('fsync-error-retained-failure', candidate, b'written-but-not-durable\n',
             stderr=b'fsync-fault-control\n', inject_fsync=True)
    text = b'##[warning]legacy\rpart\xff\n::error::prefixed\nOK\n'
    old = run_case('original-text-success', original, text, binary=False, required='OK')
    new = run_case('candidate-text-success', candidate, text, binary=False, required='OK')
    assert old[0] == new[0]
    for module in [original, candidate]:
        expected = ''.join(module.display_output(x) for x in text.splitlines(keepends=True))
        # Recorder readline splits only on LF, not CR. Check actual line grouping explicitly.
        expected = ''.join(module.display_output(x + b'\n') for x in text.split(b'\n')[:-1])
        assert expected in new[1] and expected in old[1]
    assert '| ##\\x5bwarning]' in new[1] and r'\r' in new[1]
    run_case('original-required-line-failure', original, b'OK suffix\n',
             binary=False, required='OK')
    run_case('candidate-required-line-failure', candidate, b'OK suffix\n',
             binary=False, required='OK')
    # Deterministic combined-failure API control: no process or service exists,
    # no real signal is sent, and join waits are simulated without sleeping.
    class FakeProcess:
        pid = 194939
        def __init__(self, *args, **kwargs):
            assert kwargs['start_new_session'] is True
            self.stdout = io.BytesIO()
            self.stderr = io.BytesIO()
            self.waits = 0
        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired('controlled-only', timeout)
            return 0
    joins = []
    class FakeThread:
        def __init__(self, *args, **kwargs):
            pass
        def start(self):
            pass
        def join(self, timeout=None):
            joins.append(timeout)
        def is_alive(self):
            return True
    signals = []
    folder = output / 'controlled-timeout-plus-two-drains'
    folder.mkdir()
    controlled = candidate.Recorder(folder / 'records')
    with mock.patch.object(candidate.subprocess, 'Popen', FakeProcess), \
         mock.patch.object(candidate.threading, 'Thread', FakeThread), \
         mock.patch.object(candidate.os, 'killpg', lambda pid, sig: signals.append([pid, int(sig)])), \
         contextlib.redirect_stdout(io.StringIO()):
        try:
            controlled.run('controlled-only', ['never-executed'], folder, env,
                           timeout=0.01, stdout_file=folder / 'empty-export.bin')
        except subprocess.CalledProcessError as error:
            assert error.returncode == 125
        else:
            raise AssertionError('combined failure was accepted')
    receipt = controlled.receipts[-1]
    assert receipt['exit_code'] == 125 and receipt['timed_out'] is True
    assert receipt['reason'] == ('stage timeout; output pipe remained open after child exit; '
                                 'output pipe remained open after child exit')
    assert joins == [10, 5, 10, 5] and len(signals) == 3
    assert all(pid == FakeProcess.pid for pid, _ in signals)
    assert receipt['export']['size_bytes'] == 0
    results.append({'name': 'controlled-timeout-plus-two-open-pipes', 'passed': True,
                    'mocked_process_and_threads': True, 'real_process_or_group_signal': False,
                    'join_calls_without_waiting': joins, 'mock_signal_calls': signals,
                    'receipt': receipt})
    assert sha(ORIGINAL.read_bytes()) == ORIGINAL_SHA
    children1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    report = {
        'schema': 'eth-r7-staging-recorder-controls/1',
        'status': 'STAGING_UNAPPLIED_CONTROLS_PASS', 'passed': True,
        'scope': 'Small local byte-transport controls only; no Lean, exporter, Nanoda, ETH proof or Linux Landrun execution. No Linux runtime or end-to-end speed verdict.',
        'started_utc': started,
        'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'original': {'path': str(ORIGINAL.relative_to(ROOT)), 'sha256': ORIGINAL_SHA,
                     'unchanged_after_controls': True},
        'candidate': {'path': str(CANDIDATE.relative_to(ROOT)), 'sha256': CANDIDATE_SHA},
        'control_script': {'path': str(Path(__file__).relative_to(ROOT)),
                           'sha256': sha(Path(__file__).read_bytes())},
        'chunk_bytes': CHUNK,
        'fsync_scope': 'Counted only actual candidate export-file fsync calls via device/inode, delegating to real os.fsync except one explicit failure injection. Text/json fsync operations continue unchanged and are not counted as export calls.',
        'results': results,
        'own_cpu_seconds': time.process_time() - cpu,
        'child_cpu_seconds': children1.ru_utime + children1.ru_stime - children0.ru_utime - children0.ru_stime,
        'wall_seconds': time.perf_counter() - wall,
        'paid_compute_usd': 0,
        'limits': 'No baseline fsync timing benchmark; newline count motivates a potential IO reduction only. Per-chunk/final fsync cannot guarantee host crash or physical-storage durability. Production CI and frozen r6 inputs remain unchanged.',
    }
    save(HERE / 'record-r7-control-result-r1.json', report)
    print(json.dumps({'status': report['status'], 'cases': len(results),
                      'own_cpu_seconds': report['own_cpu_seconds'],
                      'child_cpu_seconds': report['child_cpu_seconds'],
                      'wall_seconds': report['wall_seconds']}))


if __name__ == '__main__':
    main()
