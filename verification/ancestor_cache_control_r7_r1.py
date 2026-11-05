#!/usr/bin/env python3
"""Protocol controls on synthetic owned outputs, not a restored Linux proof cache."""
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parents[1]
CI = BASE / 'verification/ci-repair-candidate-r7/ci'
WORKFLOW = CI.parent / '.github/workflows/replicate.yml'
sys.path.insert(0, str(CI))
import owned_cache as cache
import replicate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def context(project):
    return {'project_identity': [{'path': name, 'sha256': sha(project / name)}
                                 for name in ['A.lean', 'lakefile.toml']],
            'proof_runtime': {'version_prefix': 'lean-4.33.1-linux', 'files': [{'path': 'bin/lean', 'sha256': '0' * 64}]}}


def main():
    out = BASE / 'verification/ancestor-cache-control-r7-r1'
    out.mkdir(exist_ok=False)
    started = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    report = {'schema': 'eth-ancestor-cache-control/1', 'scope': 'Synthetic owned-output identity/ownership and actual workflow-guard controls; no real Actions cache restore, Lean trace check or ETH verification.',
              'script_sha256': sha(Path(__file__).resolve()), 'inputs': dict({name: sha(CI / name) for name in ['owned_cache.py', 'replicate.py', cache.ANCESTOR_LEDGER]}, workflow=sha(WORKFLOW)), 'checks': [], 'passed': False}
    try:
        original_ledger = json.loads((CI / cache.ANCESTOR_LEDGER).read_text())
        job = json.loads((BASE / 'linux-runs/41911047958/anthropic-job-summary-r1.json').read_text())
        run = next(row['data'] for row in job['receipts'] if row['marker'] == 'RUN_RECEIPT')
        if original_ledger['producer_harness_rows'] != sorted(run['harness'], key=lambda x: x['path']):
            raise RuntimeError('production predecessor rows differ from actual RUN receipt')
        real_entry = original_ledger['proofs']['anthropic']
        for key in ['manifest_sha256', 'fingerprint', 'context_sha256']:
            if real_entry[key] != run['owned_cache'][key]:
                raise RuntimeError('production predecessor metadata mismatch: ' + key)
        if real_entry['exact_cache_key'] != next(row['data'] for row in job['receipts'] if row['marker'] == 'CACHE_BACKEND_AUDIT')['entries'][0]['key']:
            raise RuntimeError('production predecessor key mismatch')
        report['checks'].append({'name': 'closed-production-receipt-binding', 'passed': True, 'actual_cache_bytes_validated': False})
        template = out / 'template'
        project = template / 'project'
        project.mkdir(parents=True)
        (project / 'A.lean').write_text('def fixtureValue : Nat := 3\n')
        (project / 'lakefile.toml').write_text('name = "fixture"\n[[lean_lib]]\nname = "A"\n')
        build = project / '.lake/build/lib/lean'
        build.mkdir(parents=True)
        (build / 'A.olean').write_bytes(b'synthetic artifact for path/hash controls only\n')
        write(build / 'A.trace', {'synthetic': False, 'outputs': {}, 'depHash': 'fixture'})
        old_harness = out / 'old-harness'
        old_harness.mkdir()
        rows = original_ledger['producer_harness_rows']
        if len(rows) != 24 or len({r['path'] for r in rows}) != 24 or cache.ANCESTOR_LEDGER not in {r['path'] for r in rows}:
            raise RuntimeError('R6 producer must be exactly24 including oldledger')
        current_rows = original_ledger['reviewed_current_harness_rows']
        if len(current_rows) != 23 or cache.ANCESTOR_LEDGER in {r['path'] for r in current_rows}:
            raise RuntimeError('current reviewed rows must be exactly23 nonledger')
        for row in rows:
            source = BASE / 'ci' / row['path']
            if Path(row['path']).name != row['path'] or sha(source) != row['sha256']:
                raise RuntimeError('actual R6 public producer row mismatch: ' + row['path'])
            shutil.copyfile(source, old_harness / row['path'])
        report['checks'].append({'name':'exact-R6-old24-current23-row-shapes-and-baseline-hashes','passed':True})
        with contextlib.redirect_stdout(io.StringIO()):
            snap = cache.snapshot(project, 'anthropic', template / 'cache', old_harness, context(project))
        shutil.rmtree(project / '.lake')
        harness = template / 'repo/ci'
        harness.mkdir(parents=True)
        for row in original_ledger['reviewed_current_harness_rows']:
            shutil.copyfile(CI / row['path'], harness / row['path'])
        workflow = harness.parent / '.github/workflows/replicate.yml'
        workflow.parent.mkdir(parents=True)
        shutil.copyfile(WORKFLOW, workflow)
        fixture_ledger = copy.deepcopy(original_ledger)
        fixture_ledger['scope'] = 'SYNTHETIC CONTROL ONLY: context and manifest differ from real cache.'
        for key in ['manifest_sha256', 'fingerprint', 'context_sha256']:
            fixture_ledger['proofs']['anthropic'][key] = snap[key]
        write(harness / cache.ANCESTOR_LEDGER, fixture_ledger)
        key = real_entry['exact_cache_key']
        cases = ['accept-and-preserve', 'source-drift', 'config-drift', 'runtime-drift', 'wrong-proof',
                 'missing-key', 'prefix-only-key', 'manifest-drift', 'payload-hash-drift', 'unowned-path',
                 'duplicate-path', 'producer-driver-drift', 'producer-row-drift', 'workflow-drift', 'no-overwrite', 'old-ledger-omission', 'current-ledger-row-inclusion']
        for name in cases:
            root = out / name
            shutil.copytree(template, root)
            p, source, h = root / 'project', root / 'cache', root / 'repo/ci'
            ledger_path = h / cache.ANCESTOR_LEDGER
            ledger = json.loads(ledger_path.read_text())
            proof, actual_key = 'anthropic', key
            if name == 'source-drift':
                (p / 'A.lean').write_text('def fixtureValue : Nat := 4\n')
            if name == 'config-drift':
                with (p / 'lakefile.toml').open('a') as handle:
                    handle.write('# changed build config\n')
            ctx = context(p)
            if name == 'runtime-drift':
                ctx['proof_runtime']['files'][0]['sha256'] = '1' * 64
            if name == 'wrong-proof':
                proof = 'openai'
            if name == 'missing-key':
                actual_key = ''
            if name == 'prefix-only-key':
                actual_key += '-unapproved-suffix'
            if name == 'manifest-drift':
                with (source / 'manifest.json').open('ab') as handle:
                    handle.write(b' ')
            if name == 'payload-hash-drift':
                with (source / 'files/lib/lean/A.olean').open('ab') as handle:
                    handle.write(b'changed')
            if name in ['unowned-path', 'duplicate-path']:
                manifest = json.loads((source / 'manifest.json').read_text())
                if name == 'unowned-path':
                    old_path = manifest['files'][0]['path']
                    new_path = 'lib/lean/Unowned.olean'
                    (source / 'files' / old_path).rename(source / 'files' / new_path)
                    manifest['files'][0]['path'] = new_path
                else:
                    manifest['files'].append(copy.deepcopy(manifest['files'][0]))
                write(source / 'manifest.json', manifest)
                # Deliberately reapprove this synthetic manifest to exercise deeper path guards.
                ledger['proofs']['anthropic']['manifest_sha256'] = sha(source / 'manifest.json')
                write(ledger_path, ledger)
            if name == 'producer-driver-drift':
                with (h / 'replicate.py').open('a') as handle:
                    handle.write('\n# unreviewed producer change\n')
            if name == 'producer-row-drift':
                ledger['producer_harness_rows'][0]['sha256'] = '2' * 64
                write(ledger_path, ledger)
            if name == 'old-ledger-omission':
                ledger['producer_harness_rows'] = [r for r in ledger['producer_harness_rows'] if r['path'] != cache.ANCESTOR_LEDGER]
                write(ledger_path, ledger)
            if name == 'current-ledger-row-inclusion':
                ledger['reviewed_current_harness_rows'].append({'path':cache.ANCESTOR_LEDGER,'sha256':sha(ledger_path)})
                write(ledger_path, ledger)
            if name == 'workflow-drift':
                with (h.parent / '.github/workflows/replicate.yml').open('a') as handle:
                    handle.write('\n# unreviewed workflow\n')
            if name == 'no-overwrite':
                target = p / '.lake/build/lib/lean/A.olean'
                target.parent.mkdir(parents=True)
                target.write_bytes(b'pre-existing output')
            old_manifest = (source / 'manifest.json').read_bytes()
            os.environ['ETH_RESTORED_CACHE_KEY'] = actual_key
            os.environ['RUNNER_TEMP'] = str(root / 'runner-temp')
            captured = io.StringIO()
            error = None
            try:
                with contextlib.redirect_stdout(captured):
                    restored = cache.restore(p, proof, source, h, ctx)
            except RuntimeError as exc:
                error = str(exc)
            accepted = name == 'accept-and-preserve'
            if accepted:
                if error or not restored or (source / 'manifest.json').read_bytes() != old_manifest:
                    raise RuntimeError('valid synthetic predecessor rejected or relabeled')
                records = root / 'runner-temp/eth-replication-anthropic/records'
                original = records / ('ancestor-cache-original-' + snap['manifest_sha256'] + '.json')
                if original.read_bytes() != old_manifest:
                    raise RuntimeError('original manifest not preserved exactly')
                with contextlib.redirect_stdout(captured):
                    new = cache.snapshot(p, proof, source, h, ctx)
                if new['fingerprint'] == snap['fingerprint'] or original.read_bytes() != old_manifest:
                    raise RuntimeError('new snapshot failed identity separation or erased original')
                if not (records / 'ancestor-cache-restore-receipt.json').is_file():
                    raise RuntimeError('missing acceptance receipt')
                new_manifest = (source / 'manifest.json').read_bytes()
                shutil.rmtree(p / '.lake')
                os.environ['ETH_RESTORED_CACHE_KEY'] = 'current-harness-fixture-key'
                with contextlib.redirect_stdout(captured):
                    if not cache.restore(p, proof, source, h, ctx):
                        raise RuntimeError('current fingerprint restore failed')
                if (source / 'manifest.json').read_bytes() != new_manifest:
                    raise RuntimeError('normal current manifest changed')
                report['checks'].append({'name': 'normal-current-fingerprint-acceptance', 'passed': True})
            elif error is None:
                raise RuntimeError('drift was accepted: ' + name)
            if name == 'no-overwrite' and target.read_bytes() != b'pre-existing output':
                raise RuntimeError('existing output was overwritten')
            report['checks'].append({'name': name, 'passed': True, 'expected_acceptance': accepted, 'rejection': error})
        os.environ['ETH_RESTORED_CACHE_KEY'] = key
        if 'ETH_RESTORED_CACHE_KEY' in replicate.clean_environment(out / 'proof-home'):
            raise RuntimeError('cache metadata entered proof environment')
        report['checks'].append({'name': 'metadata-excluded-from-proof-env', 'passed': True})
        text = WORKFLOW.read_text()
        section = text.split('      - name: Require exact predecessor cache selection\n')[1].split('      - name: Build and check pinned public proof\n')[0]
        guard = section.split("          python3 - <<'PY'\n", 1)[1].split('          PY\n', 1)[0]
        guard = '\n'.join(line[10:] for line in guard.splitlines())
        legacy = text.split('      - name: Restore the one reviewed predecessor cache\n')[1].split('      - name: Require exact predecessor cache selection\n')[0]
        if 'restore-keys:' in legacy or key not in legacy:
            raise RuntimeError('legacy action is not exact-key only')
        for value, expected in [(key, 0), (key + '-suffix', 1)]:
            trial = subprocess.run([sys.executable, '-c', guard], env={'MATCHED_ANCESTOR_CACHE_KEY': value}, capture_output=True, timeout=3)
            if (trial.returncode == 0) != (expected == 0):
                raise RuntimeError('actual workflow exact-key guard failed')
        report['checks'].append({'name': 'actual-workflow-guard-exact-vs-prefix', 'passed': True, 'guard_sha256': hashlib.sha256(guard.encode()).hexdigest()})
        report['passed'] = True
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        report['wall_seconds'] = time.monotonic() - started
        report['child_cpu_seconds'] = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
        target = BASE / 'verification/ancestor-cache-control-result-r7-r1.json'
        with target.open('x') as handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
        print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
