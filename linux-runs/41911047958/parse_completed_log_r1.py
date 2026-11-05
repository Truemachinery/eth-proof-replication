#!/usr/bin/env python3
"""Derive receipts from the exact completed GitHub job response, without executing proof code."""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import time

base = Path(__file__).resolve().parent
raw = base / 'anthropic-job-126858374463.raw.log'
started = time.monotonic()
cpu = time.process_time()
payload = raw.read_bytes()
lines = payload.decode('utf-8-sig').splitlines()
rows = []
for number, line in enumerate(lines, 1):
    match = re.fullmatch(r'(\d{4}-\d\d-\d\dT\S+) ([A-Z][A-Z_]*) (\{.*\})', line)
    if match:
        rows.append({'line': number, 'timestamp': match[1], 'marker': match[2],
                     'data': json.loads(match[3])})
stages = [x for x in rows if x['marker'] == 'STAGE_RECEIPT']
starts = [x for x in rows if x['marker'] == 'STAGE_START']
run_rows = [x for x in rows if x['marker'] == 'RUN_RECEIPT']
assert len(run_rows) == 1 and len(stages) == len(starts) == 39
assert len({x['data']['name'] for x in stages}) == len(stages)
for start, stage in zip(starts, stages):
    assert all(stage['data'][k] == v for k, v in start['data'].items())
run = run_rows[0]['data']
for stage, aggregate in zip(stages, run['stages']):
    assert all(stage['data'][k] == v for k, v in aggregate.items())
assert len(run['stages']) == len(stages)
assert run['proof'] == 'anthropic' and run['mode'] == 'verify'
assert run['status'] == 'incomplete'
assert all(x['data']['exit_code'] == 0 for x in stages[:-1])
assert stages[-1]['data']['name'] == 'retained-target-export'
assert stages[-1]['data']['exit_code'] == 125
sentinels = ['nanoda kernel accepts the solution', 'Lean default kernel accepts the solution',
             'Your solution is okay!']
sentinel_rows = {s: [{'line': n, 'text': x} for n, x in enumerate(lines, 1)
                      if re.fullmatch(r'\d{4}-\d\d-\d\dT\S+ \| ' + re.escape(s), x)]
                 for s in sentinels}
assert all(len(x) == 1 for x in sentinel_rows.values())
summary = {
    'schema': 'eth-completed-github-log-summary/1',
    'run_id': 41911047958, 'job_id': 126858374463,
    'raw_response': {'path': raw.name, 'bytes': len(payload),
                     'sha256': hashlib.sha256(payload).hexdigest(), 'lines': len(lines)},
    'stage_count': len(stages), 'successful_stage_count': len(stages) - 1,
    'first_failed_stage': stages[-1], 'receipts': rows,
    'comparator_sentinel_lines': sentinel_rows,
    'sum_stage_wall_seconds': sum(x['data']['wall_seconds'] for x in stages),
    'sum_reaped_child_cpu_seconds': sum(x['data']['child_cpu_seconds'] for x in stages),
    'systemd_accounting_lines': [{'line': n, 'text': x} for n, x in enumerate(lines, 1)
                                 if '| CPU time consumed:' in x or '| Service runtime:' in x],
    'scope': 'GitHub response and emitted receipts only. No proof execution or subprocess raw-file recovery. '
             'Independent systemd service CPU is excluded from reaped-child totals. Partial export identity '
             'is the failed receipt observation, not a checked full export; final input seal was not reached.',
    'parser': {'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'own_cpu_seconds': time.process_time() - cpu,
               'wall_seconds': time.monotonic() - started,
               'paid_compute_usd': 0},
}
target = base / 'anthropic-job-summary-r1.json'
with target.open('x') as output:
    json.dump(summary, output, indent=2, sort_keys=True)
    output.write('\n')
    output.flush()
    os.fsync(output.fileno())
print(json.dumps({'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                  'bytes': target.stat().st_size, 'stage_count': len(stages),
                  'first_failure': stages[-1]['data']['name'], 'parser_resources': summary['parser']}))
