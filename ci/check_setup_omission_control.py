#!/usr/bin/env python3
"""Test omitting generated setup inventories from normal Lake artifact continuation."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
from unittest import mock
import owned_cache
from record import Recorder, sha, write_json

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--real-prefix', type=Path, action='append', required=True)
    p.add_argument('--records', type=Path, required=True)
    p.add_argument('--result', type=Path, required=True)
    args = p.parse_args()
    recorder = Recorder(args.records)
    results = []
    with tempfile.TemporaryDirectory(prefix='eth-setup-omission-') as temporary:
        base = Path(temporary)
        for i, supplied in enumerate(args.real_prefix):
            prefix = supplied.resolve()
            project = base / ('case-' + str(i))
            (project / 'OAI').mkdir(parents=True)
            (project / 'OAI/Dep.lean').write_text('module\n@[expose] public def fixtureValue : Nat := 3\n')
            (project / 'OAI/Main.lean').write_text('module\npublic import OAI.Dep\npublic theorem fixtureValue_eq : fixtureValue = 3 := rfl\n')
            # This source is present before snapshot; its target will be built only after restore.
            (project / 'OAI/Tail.lean').write_text('module\npublic import OAI.Main\npublic theorem fixtureTail : fixtureValue = 3 := fixtureValue_eq\n')
            (project / 'lakefile.toml').write_text('name = "ethsetupcontrol"\nversion = "0.1.0"\n[[lean_lib]]\nname = "OAI"\nglobs = ["OAI.+"]\n')
            version = prefix.name.removeprefix('leanprover--lean4---v')
            (project / 'lean-toolchain').write_text('leanprover/lean4:v' + version + '\n')
            env = {'PATH': str(prefix / 'bin') + ':' + os.environ.get('PATH', '/usr/bin:/bin'),
                   'HOME': str(base), 'LEAN_SYSROOT': str(prefix), 'LEAN_NUM_THREADS': '2', 'LANG': 'C'}
            def run(label, *arguments):
                return recorder.run(version + '-' + label, [prefix / 'bin/lake', *arguments], project, env, timeout=30)
            run('baseline', 'build', '+OAI.Main')
            build = project / '.lake/build'
            setups = list(build.rglob('*.setup.json'))
            assert len(setups) == 2, 'expected two generated inventories'
            setup_bytes = sum(x.stat().st_size for x in setups)
            for trace in (build / 'lib/lean').rglob('*.trace'):
                assert '.setup.json' not in json.dumps(json.loads(trace.read_text()).get('outputs'))
            cache = base / ('cache-' + str(i))
            # Exercise the exact candidate omission before requiring a production policy change.
            with mock.patch.object(owned_cache, 'SUFFIXES', owned_cache.SUFFIXES - {'.setup.json'}):
                snap = owned_cache.snapshot(project, 'openai', cache, HERE, {'compiler': version})
                assert snap['status'] == 'ready'
                assert not any(x['path'].endswith('.setup.json') for x in snap['files'])
                shutil.rmtree(build)  # This test's own disposable build tree only.
                assert owned_cache.restore(project, 'openai', cache, HERE, {'compiler': version})
            assert not list(build.rglob('*.setup.json'))
            original_artifacts = {str(x.relative_to(build)): (sha(x), x.stat().st_mtime_ns)
                                  for x in build.rglob('*') if x.is_file() and x.suffix in {'.olean', '.trace', '.c'}}
            def unchanged():
                for name, identity in original_artifacts.items():
                    f = build / name
                    assert (sha(f), f.stat().st_mtime_ns) == identity, 'restored module rebuilt: ' + name
            run('no-build-after-restore', '--no-build', 'build', '+OAI.Main')
            unchanged()
            after_no_build = len(list(build.rglob('*.setup.json')))
            run('ordinary-resume', 'build', '+OAI.Main')
            unchanged()
            after_resume = len(list(build.rglob('*.setup.json')))
            run('new-dependent', 'build', '+OAI.Tail')
            unchanged()
            assert (build / 'lib/lean/OAI/Tail.olean').is_file()
            run('final-no-build', '--no-build', 'build', '+OAI.Tail')
            unchanged()
            results.append({'lean_version': version, 'passed': True, 'generated_setups_before': len(setups),
                            'generated_setup_bytes_before': setup_bytes, 'cached_payload_bytes_without_setups': snap['payload_bytes'],
                            'setups_after_no_build': after_no_build, 'setups_after_ordinary_resume': after_resume,
                            'setups_after_new_dependent': len(list(build.rglob('*.setup.json'))),
                            'restored_artifact_bytes_and_mtimes_unchanged': True, 'new_dependent_built': True})
    result = {'scope': 'Tiny real native Lean module-mode cache continuation controls only; no Mathlib or external ETH proof build and no Linux execution',
              'passed': True, 'candidate_policy': 'Exclude generated .setup.json inventories; preserve all normal outputs/traces',
              'versions': results, 'control_source_sha256': sha(HERE / 'check_setup_omission_control.py')}
    write_json(args.result, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
