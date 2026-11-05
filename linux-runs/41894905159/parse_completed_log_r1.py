#!/usr/bin/env python3
"""Parse the completed OpenAI GitHub response without running proof tools."""
import hashlib
import json
import os
from pathlib import Path
import re
import time

base = Path(__file__).resolve().parent
raw = base / 'openai-job-126801717400.raw.log'
started = time.monotonic()
cpu = time.process_time()
payload = raw.read_bytes()
lines = payload.decode('utf-8-sig').splitlines()
rows, built = [], []
for number, line in enumerate(lines, 1):
    match = re.fullmatch(r'(\d{4}-\d\d-\d\dT\S+) ([A-Z][A-Z_]*) (\{.*\})', line)
    if match:
        rows.append({'line': number, 'timestamp': match[1], 'marker': match[2],
                     'data': json.loads(match[3])})
    module = re.search(r'\| .*?\[\d+/\d+\] Built ((?:OAI\.|ComparatorChallenges\.)\S+) \(', line)
    if module:
        built.append({'line': number, 'module': module[1]})
stages = [x for x in rows if x['marker'] == 'STAGE_RECEIPT']
starts = [x for x in rows if x['marker'] == 'STAGE_START']
run_rows = [x for x in rows if x['marker'] == 'RUN_RECEIPT']
assert len(run_rows) == 1 and len(stages) == len(starts) == 38
assert len({x['data']['name'] for x in stages}) == len(stages)
for start, stage in zip(starts, stages):
    assert all(stage['data'][k] == v for k, v in start['data'].items())
run = run_rows[0]['data']
assert len(run['stages']) == len(stages)
for stage, aggregate in zip(stages, run['stages']):
    assert all(stage['data'][k] == v for k, v in aggregate.items())
assert run['proof'] == 'openai' and run['mode'] == 'all'
assert run['status'] == 'incomplete'
assert all(x['data']['exit_code'] == 0 for x in stages[:-1])
assert stages[-1]['data']['name'] == 'source-build' and stages[-1]['data']['exit_code'] == 1
assert len(built) == len({x['module'] for x in built}) == 2880
assert run['owned_cache']['completed_modules'] == len(built)
assert run['owned_cache']['status'] == 'skipped-empty-or-oversize'
oom = [{'line': n, 'text': line} for n, line in enumerate(lines, 1)
       if re.fullmatch(r'\d{4}-\d\d-\d\dT\S+ \| Finished with result: oom-kill', line)]
assert len(oom) == 1
summary = {
    'schema': 'eth-completed-github-log-summary/1', 'run_id': 41894905159,
    'job_id': 126801717400,
    'raw_response': {'path': raw.name, 'bytes': len(payload), 'lines': len(lines),
                     'sha256': hashlib.sha256(payload).hexdigest()},
    'stage_count': len(stages), 'successful_stage_count': len(stages) - 1,
    'first_failed_stage': stages[-1], 'receipts': rows, 'oom_result_lines': oom,
    'successful_owned_module_build_events': built,
    'owned_module_counts': {'OAI': sum(x['module'].startswith('OAI.') for x in built),
                            'ComparatorChallenges': sum(x['module'].startswith('ComparatorChallenges.') for x in built)},
    'sum_stage_wall_seconds': sum(x['data']['wall_seconds'] for x in stages),
    'sum_reaped_child_cpu_seconds': sum(x['data']['child_cpu_seconds'] for x in stages),
    'source_build_systemd_tail': [{'line': n, 'text': line} for n, line in enumerate(lines, 1)
                                if oom[0]['line'] <= n < stages[-1]['line']],
    'scope': 'Actual displayed successful module-build events match snapshot count; no full target closure or '
             'theorem-check stage completed. OOM is a logged systemd result. Oversize snapshot was skipped, '
             'so there is no saved OpenAI cache identity or payload to continue. Emitted subprocess hashes '
             'are distinct from recovered raw files. Reaped-child CPU excludes systemd service CPU.',
    'parser': {'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'own_cpu_seconds': time.process_time() - cpu,
               'wall_seconds': time.monotonic() - started, 'paid_compute_usd': 0},
}
target = base / 'openai-job-summary-r1.json'
with target.open('x') as output:
    json.dump(summary, output, indent=2, sort_keys=True)
    output.write('\n')
    output.flush()
    os.fsync(output.fileno())
print(json.dumps({'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                  'bytes': target.stat().st_size, 'stage_count': len(stages),
                  'built_modules': len(built), 'parser_resources': summary['parser']}))
