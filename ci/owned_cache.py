#!/usr/bin/env python3
"""Bounded cache of completed project artifacts; excludes dependencies, tools and exports."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tomllib
from record import sha, write_json

MAX_BYTES = 2 * 1024**3
# Leave room for the small manifest and Actions' container/archive metadata.
PAYLOAD_LIMIT = MAX_BYTES - 32 * 1024**2
SUFFIXES = {'.olean', '.olean.private', '.olean.server', '.ilean', '.ir', '.trace',
            '.ir.sig', '.ir.sig.hash', '.olean.hash', '.olean.private.hash', '.olean.server.hash', '.ilean.hash', '.ir.hash',
            '.c', '.c.hash', '.c.o', '.c.o.hash', '.c.o.export', '.c.o.export.hash'}


def fingerprint(harness, proof, context=None):
    rows = [(p.name, sha(p)) for p in sorted(Path(harness).iterdir()) if p.is_file()]
    return hashlib.sha256(json.dumps([proof, rows, context], separators=(',', ':')).encode()).hexdigest()


def modules(project, proof):
    if proof == 'openai':
        return {str(p.relative_to(project)).removesuffix('.lean')
                for root in ['OAI', 'ComparatorChallenges'] for p in (project / root).rglob('*.lean')}
    config = tomllib.loads((project / 'lakefile.toml').read_text())
    result = set()
    for lib in config['lean_lib']:
        directory = project / lib.get('srcDir', '.')
        if 'srcDir' in lib:
            result.update(str(p.relative_to(directory)).removesuffix('.lean') for p in directory.rglob('*.lean'))
        else:
            for name in lib.get('roots', [lib['name']]):
                source = directory / (name.replace('.', '/') + '.lean')
                if source.is_file():
                    result.add(name.replace('.', '/'))
    return result


def allowed(name, module_set):
    for prefix in ['lib/lean/', 'ir/']:
        if name.startswith(prefix):
            rest = name[len(prefix):]
            # Pinned Lake puts conditional LLVM bitcode and its hash in irDir only.
            suffixes = SUFFIXES | {'.bc', '.bc.hash'} if prefix == 'ir/' else SUFFIXES
            for suffix in sorted(suffixes, key=len, reverse=True):
                if rest.endswith(suffix) and rest[:-len(suffix)] in module_set:
                    return True
    return False


def snapshot(project, proof, destination, harness, context=None):
    destination = Path(destination).resolve()
    if destination.exists():
        shutil.rmtree(destination)  # Only this fixed task-owned cache staging folder.
    build = project / '.lake/build'
    module_set = modules(project, proof)
    complete = set()
    for module in module_set:
        trace, olean = build / ('lib/lean/' + module + '.trace'), build / ('lib/lean/' + module + '.olean')
        if trace.is_file() and olean.is_file() and not trace.is_symlink() and not olean.is_symlink():
            data = json.loads(trace.read_text())
            if data.get('synthetic') is False and 'outputs' in data and 'depHash' in data:
                complete.add(module)
    rows = []
    if build.exists():
        for p in sorted(build.rglob('*')):
            if p.is_symlink():
                raise RuntimeError('symlink in project build output')
            if not p.is_file():
                continue
            name = str(p.relative_to(build))
            if allowed(name, complete):
                if p.stat().st_nlink != 1:
                    raise RuntimeError('hardlinked project build output')
                rows.append({'path': name, 'size_bytes': p.stat().st_size, 'sha256': sha(p)})
    size = sum(x['size_bytes'] for x in rows)
    receipt = {'schema': 'eth-owned-cache/1', 'proof': proof, 'fingerprint': fingerprint(harness, proof, context),
               'context_sha256': hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest(), 'payload_bytes': size, 'cap_bytes': MAX_BYTES, 'completed_modules': len(complete),
               'files': rows, 'status': 'ready' if rows and size <= PAYLOAD_LIMIT else 'skipped-empty-or-oversize'}
    if receipt['status'] == 'ready':
        destination.mkdir(parents=True)
        for row in rows:
            target = destination / 'files' / row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(build / row['path'], target)
            if sha(target) != row['sha256']:
                raise RuntimeError('snapshot changed while copying')
        write_json(destination / 'manifest.json', receipt)
        total = sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())
        if total > MAX_BYTES:
            shutil.rmtree(destination)
            receipt['status'] = 'skipped-total-oversize'
        else:
            receipt['total_bytes'] = total
            receipt['manifest_sha256'] = sha(destination / 'manifest.json')
    print('OWNED_CACHE_SNAPSHOT ' + json.dumps({k: v for k, v in receipt.items() if k != 'files'}, sort_keys=True), flush=True)
    return receipt


def restore(project, proof, source, harness, context=None):
    source = Path(source).resolve()
    if not source.exists():
        print('OWNED_CACHE_RESTORE missing', flush=True)
        return False
    data = json.loads((source / 'manifest.json').read_text())
    if data.get('schema') != 'eth-owned-cache/1' or data.get('proof') != proof or data.get('fingerprint') != fingerprint(harness, proof, context):
        raise RuntimeError('cache identity does not match exact harness/source/toolchain/config pins')
    if data['status'] != 'ready' or data['payload_bytes'] > PAYLOAD_LIMIT:
        raise RuntimeError('invalid cache payload limit/status')
    names, size = set(), 0
    module_set = modules(project, proof)
    for row in data['files']:
        name = row['path']
        if name in names or not allowed(name, module_set):
            raise RuntimeError('unexpected/duplicate cached path')
        names.add(name)
        p = source / 'files' / name
        if p.is_symlink() or not p.is_file() or p.stat().st_nlink != 1 or p.resolve().is_relative_to(source.resolve()) is False:
            raise RuntimeError('invalid cached regular file')
        if any(parent.is_symlink() for parent in p.parents if parent != source.parent):
            raise RuntimeError('symlinked cached parent')
        if p.stat().st_size != row['size_bytes'] or sha(p) != row['sha256']:
            raise RuntimeError('cached file size/hash mismatch')
        size += row['size_bytes']
    if size != data['payload_bytes'] or size > PAYLOAD_LIMIT:
        raise RuntimeError('cached total mismatch')
    actual = {str(p.relative_to(source / 'files')) for p in (source / 'files').rglob('*') if p.is_file()}
    if actual != names:
        raise RuntimeError('unmanifested cache files')
    for row in data['files']:
        target = project / '.lake/build' / row['path']
        if target.exists():
            raise RuntimeError('restore would overwrite an existing project output')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / 'files' / row['path'], target)
    print('OWNED_CACHE_RESTORE ' + json.dumps({'manifest_sha256': sha(source / 'manifest.json'), 'fingerprint': data['fingerprint'],
          'files': len(names), 'bytes': size, 'completed_modules': data['completed_modules']}), flush=True)
    return True
