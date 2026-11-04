#!/usr/bin/env python3
"""Execute actual workflow retention guards against harmless local fixtures."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    out = BASE / 'verification/cache-policy-control-r2'
    out.mkdir(exist_ok=False)
    started = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    workflow_path = BASE / 'ci/workflow-template.yml'
    ledger_path = BASE / 'ci/ancestor-cache-compatibility.json'
    text = workflow_path.read_text()
    report = {'schema': 'eth-cache-policy-control/2', 'scope': 'Actual YAML outcome predicate and inline receipt guard executed on synthetic fixtures with a harmless maintenance stub; no GitHub cache API, real restore or proof execution.',
              'script_sha256': sha(Path(__file__).read_bytes()), 'workflow_sha256': sha(workflow_path.read_bytes()),
              'ledger_sha256': sha(ledger_path.read_bytes()), 'checks': [], 'passed': False}
    try:
        ledger = json.loads(ledger_path.read_text())
        if ledger['reviewed_workflow_sha256'] != report['workflow_sha256']:
            raise RuntimeError('ledger does not pin current workflow')
        for row in ledger['reviewed_current_harness_rows']:
            if sha((BASE / 'ci' / row['path']).read_bytes()) != row['sha256']:
                raise RuntimeError('reviewed current harness drift')
        parts = text.split('      - name: Bound retention and prune previous own-proof snapshots\n')[1:]
        if len(parts) != 2:
            raise RuntimeError('expected two actual cache policy steps')
        cases = ['skipped-key-guard', 'cancelled', 'early-failure-no-context', 'absent-finished',
                 'absent-owned-cache', 'missing-manifest', 'true-partial-ready', 'true-completed-ready',
                 'manifest-sha-mismatch', 'finished-proof-mismatch', 'snapshot-proof-mismatch',
                 'schema-mismatch', 'snapshot-status-mismatch', 'malformed-finished']
        for proof, section in zip(['openai', 'anthropic'], parts):
            section = section.split('      - name: Save at most2GiB')[0]
            predicate = next(line.strip()[4:] for line in section.splitlines() if line.strip().startswith('if: '))
            expression = predicate.replace('always()', 'True').replace('&&', 'and').replace('||', 'or')
            guard = section.split("          python3 - <<'PY'\n", 1)[1].split('          PY\n', 1)[0]
            guard = '\n'.join(line[10:] for line in guard.splitlines())
            if "proof = '" + proof + "'" not in guard:
                raise RuntimeError('guard uses wrong proof')
            for case in cases:
                root = out / (proof + '-' + case)
                repo, runner = root / 'repo', root / 'runner'
                (repo / 'ci').mkdir(parents=True)
                (repo / 'ci/cache_maintenance.py').write_text('from pathlib import Path\nPath("maintenance-called").write_text("called")\nPath("backend-sentinel").write_text("maintenance invoked")\n')
                backend = repo / 'backend-sentinel'
                backend.write_bytes(b'original good predecessor')
                directory = repo / '.ci-cache' / proof
                directory.mkdir(parents=True)
                manifest = directory / 'manifest.json'
                manifest.write_text('{"status":"ready","synthetic":true}\n')
                snapshot = {'proof': proof, 'status': 'ready', 'manifest_sha256': sha(manifest.read_bytes())}
                receipt = {'schema': 'eth-ci-run/1', 'proof': proof, 'status': 'incomplete', 'owned_cache': snapshot}
                outcome = 'failure'
                if case == 'skipped-key-guard':
                    outcome = 'skipped'
                elif case == 'cancelled':
                    outcome = 'cancelled'
                elif case == 'early-failure-no-context':
                    del receipt['owned_cache']
                elif case == 'absent-owned-cache':
                    receipt['owned_cache'] = None
                elif case == 'missing-manifest':
                    manifest.unlink()
                elif case == 'true-completed-ready':
                    outcome, receipt['status'] = 'success', 'all-required-stages-passed'
                elif case == 'manifest-sha-mismatch':
                    snapshot['manifest_sha256'] = '0' * 64
                elif case == 'finished-proof-mismatch':
                    receipt['proof'] = 'different-proof'
                elif case == 'snapshot-proof-mismatch':
                    snapshot['proof'] = 'different-proof'
                elif case == 'schema-mismatch':
                    receipt['schema'] = 'different-schema'
                elif case == 'snapshot-status-mismatch':
                    snapshot['status'] = 'skipped-empty-or-oversize'
                finished = runner / ('eth-replication-' + proof) / 'finished.json'
                finished.parent.mkdir(parents=True)
                if case != 'absent-finished':
                    finished.write_text('not json' if case == 'malformed-finished' else json.dumps(receipt))
                admitted = bool(eval(expression, {'__builtins__': {}}, {'steps': SimpleNamespace(replication=SimpleNamespace(outcome=outcome))}))
                expected_call = case in ['true-partial-ready', 'true-completed-ready']
                code, stdout, stderr = None, b'', b''
                if admitted:
                    result = subprocess.run([sys.executable, '-c', guard], cwd=repo,
                                            env={'GITHUB_WORKSPACE': str(repo), 'RUNNER_TEMP': str(runner)},
                                            capture_output=True, timeout=4)
                    code, stdout, stderr = result.returncode, result.stdout, result.stderr
                    if code != 0:
                        raise RuntimeError('inline guard error: ' + stderr.decode('utf-8', 'replace'))
                called = (repo / 'maintenance-called').exists()
                preserved = backend.read_bytes() == b'original good predecessor'
                if called != expected_call or preserved == expected_call:
                    raise RuntimeError('wrong maintenance/backend outcome: ' + proof + '/' + case)
                for suffix, data in [('stdout', stdout), ('stderr', stderr)]:
                    with (root / ('guard.' + suffix)).open('xb') as handle:
                        handle.write(data)
                        handle.flush()
                        os.fsync(handle.fileno())
                report['checks'].append({'proof': proof, 'case': case, 'passed': True, 'replication_outcome': outcome,
                                         'policy_step_admitted': admitted, 'maintenance_stub_called': called,
                                         'backend_sentinel_preserved': preserved, 'exit_code': code,
                                         'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr),
                                         'actual_predicate': predicate, 'actual_guard_sha256': sha(guard.encode())})
        report['passed'] = True
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        report['wall_seconds'] = time.monotonic() - started
        report['child_cpu_seconds'] = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
        with (BASE / 'verification/cache-policy-control-result-r2.json').open('x') as handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
        print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
