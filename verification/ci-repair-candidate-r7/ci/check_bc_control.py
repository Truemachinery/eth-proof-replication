#!/usr/bin/env python3
"""Narrow owned-cache path/bound controls; does not run Lean or LLVM."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
from unittest import mock
import owned_cache
from record import sha, write_json

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    checks = []
    owned = {'OAI/Tiny'}
    assert owned_cache.allowed('ir/OAI/Tiny.bc', owned)
    assert owned_cache.allowed('ir/OAI/Tiny.bc.hash', owned)
    for name in ['lib/lean/OAI/Tiny.bc', 'lib/lean/OAI/Tiny.bc.hash', 'ir/Foreign.bc',
                 'ir/OAI/Tiny.bc.o', '../ir/OAI/Tiny.bc', '.lake/packages/mathlib/ir/OAI/Tiny.bc']:
        assert not owned_cache.allowed(name, owned), name
    checks.append('conditional bitcode accepted only under existing ir directory and owned module')
    with tempfile.TemporaryDirectory(prefix='eth-bc-cache-control-') as directory:
        base = Path(directory)
        project = base / 'project'
        (project / 'OAI').mkdir(parents=True)
        (project / 'OAI/Tiny.lean').write_text('def fixtureValue : Nat := 3\n')
        artifacts = {
            'lib/lean/OAI/Tiny.olean': b'synthetic ownership control only',
            'lib/lean/OAI/Tiny.trace': json.dumps({'synthetic': False, 'outputs': {}, 'depHash': 'control'}).encode(),
            'ir/OAI/Tiny.bc': b'synthetic LLVM bitcode path control; not actual LLVM output',
            'ir/OAI/Tiny.bc.hash': b'control hash sidecar bytes',
            'ir/Foreign.bc': b'unowned: must be excluded',
            'lib/lean/OAI/Tiny.bc': b'wrong output directory: must be excluded',
        }
        for name, data in artifacts.items():
            file = project / '.lake/build' / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        foreign = project / '.lake/packages/mathlib/.lake/build/ir/Mathlib/Foreign.bc'
        foreign.parent.mkdir(parents=True)
        foreign.write_bytes(b'dependency: must be excluded')
        cache = base / 'cache'
        context = {'test': 'ownership-and-bounds-only'}
        with contextlib.redirect_stdout(io.StringIO()):
            snap = owned_cache.snapshot(project, 'openai', cache, HERE, context)
            expected = {'lib/lean/OAI/Tiny.olean', 'lib/lean/OAI/Tiny.trace', 'ir/OAI/Tiny.bc', 'ir/OAI/Tiny.bc.hash'}
            assert snap['status'] == 'ready' and {row['path'] for row in snap['files']} == expected
            restored = base / 'restored'
            (restored / 'OAI').mkdir(parents=True)
            (restored / 'OAI/Tiny.lean').write_bytes((project / 'OAI/Tiny.lean').read_bytes())
            assert owned_cache.restore(restored, 'openai', cache, HERE, context)
            for name in expected:
                assert (restored / '.lake/build' / name).read_bytes() == artifacts[name]
            checks.append('owned bitcode and sidecar roundtrip byte-identically; foreign paths and dependencies excluded')
            target = cache / 'files/ir/OAI/Tiny.bc'
            target.write_bytes(b'changed bytes')
            bad = base / 'bad'
            (bad / 'OAI').mkdir(parents=True)
            (bad / 'OAI/Tiny.lean').write_bytes((project / 'OAI/Tiny.lean').read_bytes())
            try:
                owned_cache.restore(bad, 'openai', cache, HERE, context)
            except RuntimeError as error:
                assert 'hash mismatch' in str(error)
            else:
                raise AssertionError('tampered bitcode cache accepted')
            checks.append('bitcode tamper rejected by existing per-file size/hash validation')
            assert owned_cache.max_bytes('openai') == 6 * 1024**3
            assert owned_cache.max_bytes('anthropic') == 2 * 1024**3
            with mock.patch.object(owned_cache, 'payload_limit', return_value=1):
                skipped = owned_cache.snapshot(project, 'openai', base / 'oversize', HERE, context)
                assert skipped['status'] == 'skipped-empty-or-oversize'
                assert not (base / 'oversize').exists()
            checks.append('proof-specific 6GiB/2GiB caps and existing oversize skip remain active')
    result = {'scope': 'Synthetic cache ownership/restore/bound controls only; no Lean, Linux or LLVM execution',
              'passed': True, 'checks': checks, 'owned_cache_sha256': sha(HERE / 'owned_cache.py')}
    write_json(args.result, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
