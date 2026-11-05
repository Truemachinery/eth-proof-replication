#!/usr/bin/env python3
"""Evaluate the staged driver's resource environment and service-budget builder, without children."""
import ast
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]
STAGE = BASE / 'verification/ci-repair-candidate-r7'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    start, cpu = time.monotonic(), time.process_time()
    driver = STAGE / 'ci/replicate.py'
    workflow = STAGE / '.github/workflows/replicate.yml'
    tree = ast.parse(driver.read_text())
    main_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    isolated = next(n for n in main_node.body if isinstance(n, ast.FunctionDef) and n.name == 'isolated')
    rec = SimpleNamespace(deadline=10000)
    env = {'os': os, 'time': SimpleNamespace(monotonic=lambda: 1000), 'rec': rec}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(driver), 'exec'), env)
    checks = []
    for seconds, deadline, expected in [(1800, 10000, 1795), (None, 10000, 7195), (1800, 1010, 1)]:
        rec.deadline = deadline
        command = env['isolated'](['exporter', 'Solution'], Path('/fixture'), {'LEAN_SYSROOT': '/real-prefix'}, seconds)
        runtime = next(x for x in command if x.startswith('--property=RuntimeMaxSec='))
        assert runtime == '--property=RuntimeMaxSec=' + str(expected)
        assert '--property=TimeoutStopSec=5s' in command
        assert '--property=KillMode=control-group' in command
        assert '--property=MemoryMax=14G' in command
        assert '--property=RestrictAddressFamilies=~AF_UNIX' in command
        assert command[-2:] == ['exporter', 'Solution']
        checks.append({'name': 'actual-isolated-builder-budget', 'seconds': seconds,
                       'deadline': deadline, 'effective_runtime_max': expected, 'passed': True})
    calls = [n for n in ast.walk(main_node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == 'run' and n.args and isinstance(n.args[0], ast.Constant)
             and n.args[0].value == 'retained-target-export']
    assert len(calls) == 1
    inner = calls[0].args[1]
    assert isinstance(inner, ast.Call) and inner.func.id == 'isolated'
    assert len(inner.args) == 4 and ast.literal_eval(inner.args[3]) == 1800
    assert next(ast.literal_eval(x.value) for x in calls[0].keywords if x.arg == 'timeout') == 1800
    checks.append({'name': 'actual-export-call-explicit-service-and-recorder-budget-1800', 'passed': True})
    genv = next(n for n in ast.walk(main_node) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'genv' for t in n.targets))
    for proof, slots in [('openai', '1'), ('anthropic', '2')]:
        scope = {'args': SimpleNamespace(proof=proof), 'penv': {'LEAN_NUM_THREADS': '2'},
                 'work': Path('/fixture'), 'env': {'PATH': '/original-bin'}}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[genv], type_ignores=[])), str(driver), 'exec'), scope)
        result = scope['genv']
        assert result['ETH_LEAN_SLOTS'] == slots and result['LEAN_NUM_THREADS'] == '2'
        assert result['LEAN_SYSROOT'] == '/fixture/compiler-gate/prefix'
        assert result['LAKE_OVERRIDE_LEAN'] == 'true'
        assert result['PATH'] == '/fixture/compiler-gate/prefix/bin:/original-bin'
        checks.append({'name': 'actual-source-compiler-environment', 'proof': proof,
                       'frontends': int(slots), 'runtime_threads': 2, 'passed': True})
    text = workflow.read_text()
    assert 'Save at most 6GiB of OpenAI completed outputs' in text
    assert 'Save at most 2GiB of Anthropic completed outputs' in text
    legacy = text.split('      - name: Restore the one reviewed predecessor cache\n')[1].split('      - name: Require exact predecessor cache selection\n')[0]
    expected_key = 'eth-owned-anthropic-9fbd29ee32ef2ea4fe15afa713145c3cfcc69aad02da8ac94dad8500bd76f92a-41911047958-1'
    assert expected_key in legacy and 'restore-keys:' not in legacy
    assert '41894905159-1' not in text
    assert 'ancestor_cache_restore' not in text.split('  anthropic:\n', 1)[0]
    checks.append({'name': 'actual-workflow-limits-and-only-r6-anthropic-predecessor', 'passed': True})
    report = {'schema': 'eth-r7-driver-resource-controls/1', 'passed': True, 'checks': checks,
              'scope': 'Actual AST expressions and service-command builder evaluated with harmless values; no service, compiler, proof tool, API or Linux runner executed. Single compiler memory fit remains unmeasured.',
              'inputs': {str(p.relative_to(BASE)): digest(p) for p in [Path(__file__), driver, workflow]},
              'own_cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.monotonic() - start,
              'paid_compute_usd': 0}
    target = BASE / 'verification/r7-driver-resource-control-result-r1.json'
    with target.open('x') as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    print(json.dumps({'path': str(target), 'sha256': digest(target), 'checks': len(checks),
                      'own_cpu_seconds': report['own_cpu_seconds'], 'wall_seconds': report['wall_seconds']}))


if __name__ == '__main__':
    main()
