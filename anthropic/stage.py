#!/usr/bin/env python3
# Explicit portable derivative; original executed-source SHA is in PUBLIC_MANIFEST.json.
"""Record one exact external-proof verification command, without truncating output."""

def __eth_public_expand_path(value):
    p = __import__('pathlib').Path
    root = __import__('os').environ.get('ETH_REPLICATION_ROOT', str(p(__file__).resolve().parents[1]))
    project = __import__('os').environ.get('ETH_PROJECT_ROOT', '<PRIVATE_PROJECT_ROOT>')
    return value.replace('<REPLICATION_ROOT>', root).replace('<HOME>', str(p.home())).replace('<PRIVATE_PROJECT_ROOT>', project)
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('--cwd', default='source/eth')
    parser.add_argument('--timeout', type=float, default=28800)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        parser.error('an exact command after -- is required')
    output = ROOT / 'logs' / (args.name + '.txt')
    result = ROOT / 'logs' / (args.name + '.json')
    if output.exists() or result.exists():
        raise SystemExit('refusing to overwrite recorded stage')
    env = dict(os.environ)
    env['ELAN_HOME'] = str(ROOT / 'elan')
    env['XDG_CACHE_HOME'] = str(ROOT / 'cache')
    env['MATHLIB_CACHE_DIR'] = str(ROOT / 'cache' / 'mathlib')
    env['PATH'] = __eth_public_expand_path('<HOME>/.elan/bin:') + env['PATH']
    cwd = ROOT / args.cwd
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    timed_out = False
    pid = None
    with output.open('xb', buffering=0) as log:
        try:
            proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            pid = proc.pid
            try:
                while True:
                    remaining = args.timeout - (time.monotonic() - start)
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(command, args.timeout)
                    try:
                        exit_code = proc.wait(timeout=min(1.0, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        os.fsync(log.fileno())
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    exit_code = proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    exit_code = proc.wait()
        except BaseException as exc:
            log.write(('\nWRAPPER_EXCEPTION: ' + repr(exc) + '\n').encode())
            if pid is not None:
                try:
                    os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            exit_code = 125
        os.fsync(log.fileno())
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record = {'format': 'external-eth-command-v1', 'name': args.name, 'started_utc': started, 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'argv': command, 'cwd': str(cwd), 'environment_overrides': {k: env[k] for k in ['ELAN_HOME', 'XDG_CACHE_HOME', 'MATHLIB_CACHE_DIR', 'PATH']}, 'timeout_wall_seconds': args.timeout, 'timed_out': timed_out, 'exit_code': exit_code, 'wall_seconds': time.monotonic() - start, 'child_user_seconds': after.ru_utime - before.ru_utime, 'child_system_seconds': after.ru_stime - before.ru_stime, 'child_cpu_seconds': after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime, 'peak_child_rss_bytes_macos': after.ru_maxrss, 'output_path': str(output), 'output_size_bytes': output.stat().st_size, 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'limitations': 'Local command resource accounting excludes source authoring and model inference. Downloaded dependency objects are distinct from project-source re-elaboration.'}
    with result.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(record, indent=2), flush=True)
    sys.exit(124 if timed_out else exit_code if exit_code >= 0 else 128 - exit_code)
if __name__ == '__main__':
    main()
