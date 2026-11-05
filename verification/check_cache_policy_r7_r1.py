#!/usr/bin/env python3
"""Small mocked cache-policy controls; no network, proof tools or large files."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import runpy
import sys
import tempfile
import time
import types
import urllib.request
from unittest import mock

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
CI = BASE / 'ci-repair-candidate-r7/ci'
sys.path.insert(0, str(CI))
import owned_cache as owned


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started, cpu = time.monotonic(), time.process_time()
    checks = []
    def check(name, value):
        assert value, name
        checks.append(name)
    def rejected(call, text):
        try:
            call()
        except RuntimeError as error:
            assert text in str(error), str(error)
            return True
        return False
    with tempfile.TemporaryDirectory(prefix='cache-r7-control-', dir=BASE) as tmp:
        root = Path(tmp)
        harness = root / 'harness'
        harness.mkdir()
        (harness / 'fixture').write_text('stable tiny fixture harness')
        for proof, cap in [('openai', 6 * 1024**3), ('anthropic', 2 * 1024**3)]:
            check(proof + ' exact cap/reserve', owned.max_bytes(proof) == cap and owned.payload_limit(proof) == cap - 32 * 1024**2)
            check(proof + ' payload boundary', cap - 32 * 1024**2 <= owned.payload_limit(proof) and not cap - 32 * 1024**2 + 1 <= owned.payload_limit(proof))
        check('8GiB total cap', owned.TOTAL_MAX_BYTES == 8 * 1024**3)
        check('observed OAI payload fits expanded limit', 3718194367 <= owned.payload_limit('openai') and 3718194367 > owned.payload_limit('anthropic'))
        try:
            owned.max_bytes('unknown')
        except KeyError:
            checks.append('unknown proof fails closed')
        else:
            raise AssertionError('unknown proof accepted')
        # Actual snapshot/restore on a few bytes retains existing ownership/hash guards.
        project = root / 'project'
        (project / 'OAI').mkdir(parents=True)
        (project / 'OAI/Tiny.lean').write_text('-- synthetic fixture only\n')
        build = project / '.lake/build/lib/lean/OAI'
        build.mkdir(parents=True)
        (build / 'Tiny.olean').write_bytes(b'fixture')
        (build / 'Tiny.trace').write_text(json.dumps({'synthetic': False, 'outputs': [], 'depHash': 'fixture'}))
        (build / 'Foreign.olean').write_bytes(b'exclude')
        cache = root / 'cache'
        with contextlib.redirect_stdout(io.StringIO()):
            ready = owned.snapshot(project, 'openai', cache, harness, {'fixture': True})
            check('tiny actual snapshot owns two files only', ready['status'] == 'ready' and len(ready['files']) == 2 and ready['cap_bytes'] == 6 * 1024**3)
            for proof in ['openai']:
                with mock.patch.object(owned, 'payload_limit', return_value=ready['payload_bytes']):
                    exact = owned.snapshot(project, proof, root / ('exact-' + proof), harness)
                    check(proof + ' scaled payload equality accepted', exact['status'] == 'ready')
                with mock.patch.object(owned, 'payload_limit', return_value=ready['payload_bytes'] - 1):
                    over = owned.snapshot(project, proof, root / ('over-' + proof), harness)
                    check(proof + ' scaled payload plus-one skipped', over['status'] == 'skipped-empty-or-oversize')
            restored = root / 'restored'
            (restored / 'OAI').mkdir(parents=True)
            (restored / 'OAI/Tiny.lean').write_bytes((project / 'OAI/Tiny.lean').read_bytes())
            check('tiny restore passes full existing validation', owned.restore(restored, 'openai', cache, harness, {'fixture': True}))
            check('restore refuses overwrite', rejected(lambda: owned.restore(restored, 'openai', cache, harness, {'fixture': True}), 'overwrite'))
            (cache / 'files/lib/lean/OAI/Tiny.olean').write_bytes(b'changed')
            check('restore still rejects changed hash', rejected(lambda: owned.restore(restored, 'openai', cache, harness, {'fixture': True}), 'hash mismatch'))

        # Execute maintenance with mocked public API and tiny staging files only.
        directory = root / 'stage'
        directory.mkdir()
        manifest = directory / 'manifest.json'
        event, output = root / 'event.json', root / 'output.txt'
        event.write_text('{}')
        class Response:
            def __init__(self, value): self.value = value
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(self.value).encode()
        def maintenance(proof, items, audit=True, small_limit=None):
            manifest.write_text(json.dumps({'proof': proof, 'status': 'ready', 'payload_bytes': 0}))
            output.write_text('')
            deletes, calls = [], []
            def opener(request, timeout=60):
                calls.append((request.get_method(), request.full_url))
                prefix = 'https://api.github.com/repos/fixture/public'
                assert request.full_url.startswith(prefix)
                path = request.full_url[len(prefix):]
                if request.get_method() == 'DELETE':
                    deletes.append(int(path.rsplit('/', 1)[-1]))
                    return Response(None)
                if path == '': return Response({'private': False, 'visibility': 'public'})
                assert path == '/actions/caches?per_page=100&page=1'
                return Response({'actions_caches': items})
            environment = {'GITHUB_EVENT_PATH': str(event), 'GITHUB_REPOSITORY': 'fixture/public', 'GH_TOKEN': 'fixture-only', 'GITHUB_OUTPUT': str(output)}
            arguments = ['cache_maintenance.py', proof, '--directory', str(directory)] + (['--audit-only'] if audit else [])
            error = None
            stub = types.SimpleNamespace(public_runner_guard=lambda event, env: None)
            with contextlib.redirect_stdout(io.StringIO()), mock.patch.dict(os.environ, environment, clear=True), mock.patch.dict(sys.modules, {'replicate': stub, 'owned_cache': owned}), mock.patch.object(sys, 'argv', arguments), mock.patch.object(urllib.request, 'urlopen', opener):
                with contextlib.ExitStack() as stack:
                    if small_limit is not None: stack.enter_context(mock.patch.object(owned, 'max_bytes', return_value=small_limit))
                    try:
                        runpy.run_path(str(CI / 'cache_maintenance.py'), run_name='__main__')
                    except SystemExit as exit:
                        if exit.code != 0: error = str(exit)
                    except RuntimeError as failure:
                        error = str(failure)
            return error, deletes, calls, output.read_text()
        def item(proof, size, identity):
            return {'key': 'eth-owned-' + proof + '-fixture-' + str(identity), 'size_in_bytes': size, 'id': identity}
        pair = [item('openai', 6 * 1024**3, 1), item('anthropic', 2 * 1024**3, 2)]
        for proof in ['openai', 'anthropic']:
            error, deletes, _, _ = maintenance(proof, pair)
            check(proof + ' backend equality6plus2 accepted', error is None and deletes == [])
        for current, oversized, expected_delete in [('openai', 'openai', [1]), ('anthropic', 'anthropic', [2]), ('openai', 'anthropic', []), ('anthropic', 'openai', [])]:
            values = [dict(x, size_in_bytes=x['size_in_bytes'] + (1 if x['key'].startswith('eth-owned-' + oversized + '-') else 0)) for x in pair]
            error, deletes, _, _ = maintenance(current, values)
            check(current + ' rejects oversized ' + oversized + ' without deleting other proof', error is not None and deletes == expected_delete)
        duplicate = [item('openai', 3 * 1024**3, 1), item('openai', 3 * 1024**3, 3), item('anthropic', 2 * 1024**3, 2)]
        error, deletes, _, _ = maintenance('openai', duplicate)
        check('duplicate own snapshots rejected/deleted at8GiB', error is not None and deletes == [1, 3])
        error, deletes, _, _ = maintenance('openai', [{'key': 'unrelated', 'id': 9, 'size_in_bytes': 1}])
        check('unrelated namespace rejected without deletion', error is not None and deletes == [])
        for current, other, cap in [('openai', 'anthropic', 2 * 1024**3), ('anthropic', 'openai', 6 * 1024**3)]:
            error, deletes, _, ready_output = maintenance(current, [item(other, cap, 2)], audit=False)
            check(current + ' pre-save accepts other-proof equality', error is None and ready_output == 'ready=true\n')
            error, _, _, ready_output = maintenance(current, [item(other, cap + 1, 2)], audit=False)
            check(current + ' pre-save rejects other-proof plus-one', error is not None and not ready_output)
        manifest.write_text(json.dumps({'proof': 'openai', 'status': 'ready', 'payload_bytes': 0}))
        small = manifest.stat().st_size
        error, _, _, _ = maintenance('openai', [], audit=False, small_limit=small)
        check('actual staging equality accepted scaled', error is None)
        error, deletes, calls, _ = maintenance('openai', [], audit=False, small_limit=small - 1)
        check('actual staging plus-one rejected before API', error is not None and not deletes and not calls)

    result = {'schema': 'eth-r7-cache-policy-control/1', 'passed': True, 'checks': checks,
              'scope': 'Production staged cache functions and fully mocked maintenance API; synthetic tiny files only. No network, proof tools, multiGiB allocation or live CI edits. Full actual-R6 ancestor protocol is a separate control after final ledger freeze.',
              'sources': {name: {'sha256': sha(CI / name), 'size_bytes': (CI / name).stat().st_size} for name in ['owned_cache.py', 'cache_maintenance.py', 'check_controls.py', 'check_bc_control.py']},
              'control_sha256': sha(Path(__file__)), 'own_cpu_seconds': time.process_time() - cpu,
              'wall_seconds': time.monotonic() - started, 'incremental_usd': 0}
    with (BASE / 'cache-policy-r7-control-result-r1.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__': main()
