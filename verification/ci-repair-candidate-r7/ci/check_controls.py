#!/usr/bin/env python3
"""Small harness controls only. Does not build/check either external ETH proof."""
import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from unittest import mock
from record import Recorder, sha
import owned_cache
from replicate import public_runner_guard, clean_environment

HERE = Path(__file__).resolve().parent

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--result', type=Path, required=True)
    p.add_argument('--real-prefix', type=Path, action='append', default=[])
    p.add_argument('--source-checkout', type=Path)
    a = p.parse_args()
    start = time.monotonic()
    checks = []
    for source in HERE.glob('*.py'):
        ast.parse(source.read_text(), filename=source.name)
    checks.append('python syntax')
    good_event = {'repository': {'private': False, 'visibility': 'public', 'full_name': 'example/repro'}}
    good_env = {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
                'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REPOSITORY': 'example/repro'}
    with mock.patch('platform.system', return_value='Linux'), mock.patch('platform.machine', return_value='x86_64'), mock.patch('os.getuid', return_value=1001):
        public_runner_guard(good_event, good_env)
        for event, env in [({'repository': {'private': True, 'visibility': 'private'}}, good_env),
                           (good_event, dict(good_env, RUNNER_ENVIRONMENT='self-hosted')),
                           (good_event, dict(good_env, GITHUB_EVENT_NAME='push'))]:
            try:
                public_runner_guard(event, env)
            except RuntimeError:
                pass
            else:
                raise AssertionError('unsafe runner/event accepted')
    checks.append('public/manual/hosted guards')
    with tempfile.TemporaryDirectory(prefix='eth-ci-controls-') as tmp:
        tmp = Path(tmp)
        home = tmp / 'home'
        (home / 'tmp').mkdir(parents=True)
        with mock.patch.dict(os.environ, {'GITHUB_TOKEN': 'control-only', 'AWS_SECRET_ACCESS_KEY': 'control-only'}):
            env = clean_environment(home)
        assert 'GITHUB_TOKEN' not in env and 'AWS_SECRET_ACCESS_KEY' not in env
        checks.append('proof environment drops credentials')
        rec = Recorder(tmp / 'records')
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            rec.run('success', [sys.executable, '-c', 'print("::notice::untrusted"); print("EXACT")'], tmp, env, required_text='EXACT')
            assert '| ::notice::untrusted' in stream.getvalue()
            for name, command, options, expected in [
                ('controlled-failure', [sys.executable, '-c', 'raise SystemExit(7)'], {}, 7),
                ('controlled-timeout', [sys.executable, '-c', 'import time; time.sleep(30)'], {'timeout':0.1}, 124),
                ('missing-line', [sys.executable, '-c', 'print("other")'], {'required_text':'EXACT'}, 125)]:
                try:
                    rec.run(name, command, tmp, env, **options)
                except subprocess.CalledProcessError as error:
                    assert error.returncode == expected
                else:
                    raise AssertionError('failure accepted')
            export = tmp / 'separate-export'
            receipt = rec.run('export', [sys.executable, '-c', 'import sys; sys.stdout.buffer.write(b"export\\x00bytes"); print("diagnostic",file=sys.stderr)'],
                              tmp, env, stdout_file=export)
            assert export.read_bytes() == b'export\x00bytes' and receipt['export']['sha256'] == sha(export)
        assert len(list((tmp / 'records').glob('*/finished.json'))) == 5
        checks.append('streamed/fsynced exit, timeout, exact-line and export receipts')
        project = tmp / 'project'
        module = project / 'OAI/Tiny.lean'
        module.parent.mkdir(parents=True)
        module.write_text('def count : Nat := 3\n')
        build = project / '.lake/build/lib/lean/OAI'
        build.mkdir(parents=True)
        (build / 'Tiny.olean').write_bytes(b'control output only')
        (build / 'Tiny.trace').write_text(json.dumps({'synthetic':False, 'outputs':{}, 'depHash':'control'}))
        foreign = project / '.lake/packages/mathlib/foreign'
        foreign.parent.mkdir(parents=True)
        foreign.write_text('not cached')
        cache = tmp / 'cache'
        with contextlib.redirect_stdout(io.StringIO()):
            receipt = owned_cache.snapshot(project, 'openai', cache, HERE, {'compiler':'control'})
            assert receipt['status'] == 'ready' and receipt['completed_modules'] == 1
            assert len(receipt['files']) == 2 and not any('packages' in x['path'] for x in receipt['files'])
            restored = tmp / 'restored'
            (restored / 'OAI').mkdir(parents=True)
            (restored / 'OAI/Tiny.lean').write_bytes(module.read_bytes())
            owned_cache.restore(restored, 'openai', cache, HERE, {'compiler':'control'})
            assert (restored / '.lake/build/lib/lean/OAI/Tiny.olean').read_bytes() == b'control output only'
            (tmp / 'bad-restore/OAI').mkdir(parents=True)
            (tmp / 'bad-restore/OAI/Tiny.lean').write_bytes(module.read_bytes())
            for context, corruption in [({'compiler':'changed'}, False), ({'compiler':'control'}, True)]:
                if corruption:
                    (cache / 'files/lib/lean/OAI/Tiny.olean').write_bytes(b'corruption')
                try:
                    owned_cache.restore(tmp / 'bad-restore', 'openai', cache, HERE, context)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('invalid cache accepted')
            with mock.patch.object(owned_cache, 'payload_limit', return_value=1):
                over = owned_cache.snapshot(project, 'openai', tmp / 'oversize', HERE)
                assert over['status'] == 'skipped-empty-or-oversize' and not (tmp / 'oversize').exists()
        checks.append('owned-only bounded cache, SHA/context rejection, oversize skip')
        if a.source_checkout:
            base = tmp / 'prepared'
            base.mkdir()
            (base / 'source').symlink_to(a.source_checkout.resolve(), target_is_directory=True)
            prepared = subprocess.run([sys.executable, str(HERE / 'prepare_openai.py'), '--base', str(base)], capture_output=True, text=True)
            assert prepared.returncode == 0, prepared.stdout + prepared.stderr
            manifest = json.loads((base / 'source-manifest.json').read_text())
            rows = sorted((x['path'], x['sha256'], x['size_bytes']) for x in manifest['files'])
            pin = json.loads((HERE / 'pins.json').read_text())['openai']
            assert len(rows) == pin['closure_files']
            assert hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest() == pin['closure_sha256']
            for row in manifest['files']:
                dest = base / 'workspace' / (row['module'].replace('.', '/') + '.lean')
                assert sha(dest) == row['sha256']
            checks.append('public preparer3092-module exact closure and byte identity')
        for number, supplied_prefix in enumerate(a.real_prefix):
            prefix = supplied_prefix.resolve()
            # Local Darwin control branch, not a Linux systemd/Landrun control.
            gate = tmp / ('gate-' + str(number))
            result = subprocess.run([sys.executable, str(HERE / 'create_gate.py'), '--real-prefix', str(prefix), '--output', str(gate)],
                                    capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
            plain = subprocess.check_output([prefix / 'bin/lean', '--version'])
            gated = subprocess.check_output([gate / 'prefix/bin/lean', '--version'])
            assert plain == gated
            checks.append('local gate C compile and compiler metadata: ' + prefix.name)
            case = tmp / ('real-lake-' + str(number))
            (case / 'OAI').mkdir(parents=True)
            (case / 'OAI/Dep.lean').write_text('module\n@[expose] public def fixtureValue : Nat := 3\n')
            (case / 'OAI/Main.lean').write_text('module\npublic import OAI.Dep\npublic theorem fixtureValue_eq : fixtureValue = 3 := rfl\n')
            (case / 'lakefile.toml').write_text('name = "ethcontrol"\nversion = "0.1.0"\ndefaultTargets = ["OAI"]\n[[lean_lib]]\nname = "OAI"\nglobs = ["OAI.+"]\n')
            version = prefix.name.removeprefix('leanprover--lean4---v')
            (case / 'lean-toolchain').write_text('leanprover/lean4:v' + version + '\n')
            realenv = dict(env, PATH=str(prefix / 'bin') + ':' + env['PATH'], LEAN_SYSROOT=str(prefix))
            def lake(*arguments):
                return subprocess.run([prefix / 'bin/lake', *arguments], cwd=case, env=realenv, capture_output=True, text=True)
            built = lake('build', '+OAI.Main')
            assert built.returncode == 0, built.stdout + built.stderr
            signatures = list((case / '.lake/build').rglob('*.ir.sig'))
            assert len(signatures) >= 2, 'fixture did not exercise module IR signatures'
            realcache = tmp / ('real-cache-' + str(number))
            with contextlib.redirect_stdout(io.StringIO()):
                snap = owned_cache.snapshot(case, 'openai', realcache, HERE, {'compiler':version})
                assert snap['status'] == 'ready'
                assert any(x['path'].endswith('.ir.sig') for x in snap['files'])
                shutil.rmtree(case / '.lake/build')
                owned_cache.restore(case, 'openai', realcache, HERE, {'compiler':version})
            trace = lake('--no-build', 'build', '+OAI.Main')
            assert trace.returncode == 0, trace.stdout + trace.stderr
            # Demonstrate that the exact omitted artifact matters to ordinary Lake reuse.
            removed = next((case / '.lake/build').rglob('*.ir.sig'))
            prior = removed.read_bytes()
            removed.unlink()
            negative = lake('--no-build', 'build', '+OAI.Main')
            assert negative.returncode != 0, 'missing IR signature was not detected'
            removed.write_bytes(prior)
            final = lake('--no-build', 'build', '+OAI.Main')
            assert final.returncode == 0, final.stdout + final.stderr
            checks.append('real module-mode Lake cache roundtrip, IR-signature rejection and final no-build pass: ' + version)
    result = {'scope':'Local harness controls only; no Linux/Landrun or external proof replication',
              'checks':checks, 'passed':True, 'wall_seconds':time.monotonic()-start}
    a.result.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    main()
