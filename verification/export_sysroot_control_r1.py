#!/usr/bin/env python3
"""Trusted Init export controls; no external proof or Linux isolation check."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'verification/export-sysroot-control-r1'
SPECS = [
    ('4.33.1', 'anthropic', '433', '15f6055e299ad5b89345e533cc2192f4cc00f659'),
    ('4.34.1', 'openai', '434', '076e8e57707e813375e8f9da8bf989799ace9680'),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(BASE)), 'sha256': digest(data), 'size_bytes': len(data)}


def main():
    OUT.mkdir(exist_ok=False)
    (OUT / 'empty-path').mkdir()
    (OUT / 'home').mkdir()
    begun = time.monotonic()
    cpu_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    rows = []
    report = {'schema': 'eth-export-sysroot-control/1', 'scope': 'Trusted Init export only; not ETH, kernel replay, or Linux Landrun execution.',
              'script': identity(Path(__file__).resolve()), 'versions': rows, 'passed': False}
    try:
        for version, proof, short, commit in SPECS:
            prefix = BASE / proof / ('elan/toolchains/leanprover--lean4---v' + version)
            exporter_source = BASE / ('verification-tools/lean4export-' + short + '-source')
            exporter = exporter_source / '.lake/build/bin/lean4export'
            actual = subprocess.check_output(['git', '-C', str(exporter_source), 'rev-parse', 'HEAD'], text=True).strip()
            if actual != commit:
                raise RuntimeError('exporter source commit drift')
            source = prefix / 'src/lean/Lean/Util/Path.lean'
            row = {'lean_version': version, 'exporter_commit': actual,
                   'inputs': [identity(exporter), identity(exporter_source / 'Main.lean'), identity(prefix / 'bin/lean'), identity(source)], 'trials': []}
            rows.append(row)
            baseline = None
            for mode in ['baseline', 'empty-path-no-sysroot', 'empty-path-exact-sysroot']:
                env = {'PATH': str(prefix / 'bin') if mode == 'baseline' else str(OUT / 'empty-path'),
                       'HOME': str(OUT / 'home'), 'LANG': 'C', 'LC_ALL': 'C'}
                if mode == 'empty-path-exact-sysroot':
                    env['LEAN_SYSROOT'] = str(prefix)
                before = resource.getrusage(resource.RUSAGE_CHILDREN)
                started = time.monotonic()
                command = [str(exporter), 'Init', '--', 'Nat.add_zero']
                result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
                elapsed = time.monotonic() - started
                after = resource.getrusage(resource.RUSAGE_CHILDREN)
                for suffix, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
                    with (OUT / (short + '-' + mode + '.' + suffix)).open('xb') as handle:
                        handle.write(data)
                        handle.flush()
                        os.fsync(handle.fileno())
                trial = {'mode': mode, 'argv': ['lean4export', 'Init', '--', 'Nat.add_zero'], 'exit_code': result.returncode,
                         'wall_seconds': elapsed, 'child_cpu_seconds': after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                         'stdout_sha256': digest(result.stdout), 'stdout_bytes': len(result.stdout),
                         'stderr_sha256': digest(result.stderr), 'stderr_bytes': len(result.stderr)}
                row['trials'].append(trial)
                if mode == 'baseline':
                    if result.returncode != 0 or not result.stdout:
                        raise RuntimeError('baseline export failed')
                    baseline = result.stdout
                elif mode == 'empty-path-no-sysroot':
                    if result.returncode == 0 or b"could not execute external process 'lean'" not in result.stderr:
                        raise RuntimeError('missing-sysroot negative control did not fail as expected')
                else:
                    if result.returncode != 0 or result.stdout != baseline:
                        raise RuntimeError('exact-sysroot export differs from baseline')
                    trial['byte_identical_to_baseline'] = True
                current = resource.getrusage(resource.RUSAGE_CHILDREN)
                if current.ru_utime + current.ru_stime - cpu_start.ru_utime - cpu_start.ru_stime > 20 or time.monotonic() - begun > 55:
                    raise RuntimeError('control resource cap exceeded')
        report['passed'] = True
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        report['wall_seconds'] = time.monotonic() - begun
        report['child_cpu_seconds'] = after.ru_utime + after.ru_stime - cpu_start.ru_utime - cpu_start.ru_stime
        report['outputs'] = [identity(p) for p in sorted(OUT.iterdir()) if p.is_file()]
        target = BASE / 'verification/export-sysroot-control-result-r1.json'
        with target.open('x') as handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
