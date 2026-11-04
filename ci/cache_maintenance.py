#!/usr/bin/env python3
"""Trusted Actions-only cache pruning. The API token never reaches proof processes."""
import argparse
import json
import os
from pathlib import Path
import urllib.request
from record import sha
from replicate import public_runner_guard
from owned_cache import MAX_BYTES

p = argparse.ArgumentParser()
p.add_argument('proof', choices=['openai', 'anthropic'])
p.add_argument('--directory', type=Path, required=True)
p.add_argument('--audit-only', action='store_true')
a = p.parse_args()
public_runner_guard(json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text()), os.environ)
manifest = a.directory / 'manifest.json'
if not manifest.is_file():
    print('CACHE_SAVE skipped: no completed bounded snapshot')
    raise SystemExit(0)
data = json.loads(manifest.read_text())
files = list(a.directory.rglob('*'))
if any(x.is_symlink() for x in files) or sum(x.stat().st_size for x in files if x.is_file()) > MAX_BYTES:
    raise RuntimeError('cache staging exceeds2GiB or contains symlinks')
if data.get('proof') != a.proof or data.get('status') != 'ready':
    raise RuntimeError('cache staging identity/status mismatch')
repo = os.environ['GITHUB_REPOSITORY']
token = os.environ['GH_TOKEN']
def api(path, method='GET'):
    req = urllib.request.Request('https://api.github.com/repos/' + repo + path, method=method,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read()
    return json.loads(body) if body else None
actual_repo = api('')
if actual_repo.get('private') is not False or actual_repo.get('visibility') != 'public':
    raise RuntimeError('live repository visibility is not public')
# Dedicated new repo; do not delete unrelated caches. Refuse a policy we cannot bound.
items = []
page = 1
while True:
    batch = api('/actions/caches?per_page=100&page=' + str(page))['actions_caches']
    items.extend(batch)
    if len(batch) < 100:
        break
    page += 1
    if page > 10:
        raise RuntimeError('unexpected cache population')
prefix = 'eth-owned-' + a.proof + '-'
if a.audit_only:
    # Use actual backend archive sizes after save; staging reserve alone is not a proof of this bound.
    legal = ['eth-owned-openai-', 'eth-owned-anthropic-']
    if any(not any(x['key'].startswith(prefix_) for prefix_ in legal) for x in items):
        raise RuntimeError('unexpected cache namespace during post-save audit')
    invalid = [x for x in items if x['size_in_bytes'] > MAX_BYTES]
    for item in invalid:
        if item['key'].startswith(prefix):
            api('/actions/caches/' + str(item['id']), 'DELETE')
            print('OVERSIZE_CACHE_DELETED ' + json.dumps({'id': item['id'], 'key': item['key'], 'bytes': item['size_in_bytes']}))
    if invalid:
        raise RuntimeError('actual backend cache entry exceeded2GiB; own oversized entry deleted')
    if any(sum(x['key'].startswith(prefix_) for x in items) > 1 for prefix_ in legal) or sum(x['size_in_bytes'] for x in items) > 2 * MAX_BYTES:
        for item in items:
            if item['key'].startswith(prefix):
                api('/actions/caches/' + str(item['id']), 'DELETE')
        raise RuntimeError('actual backend cache retention exceeded4GiB/two entries; own entries removed')
    print('CACHE_BACKEND_AUDIT ' + json.dumps({'entries': [{k: x[k] for k in ['id', 'key', 'size_in_bytes']} for x in items],
          'total_bytes': sum(x['size_in_bytes'] for x in items), 'max_each_bytes': MAX_BYTES, 'max_total_bytes': 2 * MAX_BYTES}))
    raise SystemExit(0)
for item in items:
    if item['key'].startswith(prefix):
        api('/actions/caches/' + str(item['id']), 'DELETE')
        print('CACHE_DELETED ' + json.dumps({'id': item['id'], 'key': item['key'], 'bytes': item['size_in_bytes']}))
remaining = [x for x in items if not x['key'].startswith(prefix)]
other = 'anthropic' if a.proof == 'openai' else 'openai'
if any(not x['key'].startswith('eth-owned-' + other + '-') for x in remaining):
    raise RuntimeError('unexpected cache namespace; refusing upload')
if len(remaining) > 1 or sum(x['size_in_bytes'] for x in remaining) > MAX_BYTES:
    raise RuntimeError('other proof retained cache exceeds2GiB or has multiple snapshots')
print('CACHE_SAVE_ALLOWED ' + json.dumps({'proof': a.proof, 'manifest_sha256': sha(manifest),
      'payload_bytes': data['payload_bytes'], 'max_each_bytes': MAX_BYTES, 'max_total_bytes': 2 * MAX_BYTES}))
with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
    out.write('ready=true\n')
