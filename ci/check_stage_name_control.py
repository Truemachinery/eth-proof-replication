#!/usr/bin/env python3
"""Bounded regression for actual version-derived CI stage labels; no proof work."""
import argparse
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from record import Recorder, sha, validate_stage_name, write_json

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    pins = json.loads((HERE / 'pins.json').read_text())
    versions = sorted({pins[proof][field] for proof in ['openai', 'anthropic']
                       for field in ['lean', 'comparator_lean']})
    labels = {'lean-' + version + '-' + suffix for version in versions for suffix in ['download', 'extract']}
    # All remaining dynamic labels are checkout names plus these literal suffixes.
    for name in ['source', 'comparator', 'exporter', 'nanoda']:
        labels.update(name + '-' + suffix for suffix in ['init', 'remote', 'sparse-init', 'sparse-set', 'fetch', 'checkout'])
    tree = ast.parse((HERE / 'replicate.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'run':
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                labels.add(node.args[0].value)
    for label in labels:
        validate_stage_name(label)
    rejected = ['', '.', '..', '../escape', '/absolute', 'a/b', 'a\\b', 'a\nb', 'a b', 'a:b', 'μ', 'a' * 121]
    for label in rejected:
        try:
            validate_stage_name(label)
        except ValueError:
            pass
        else:
            raise AssertionError('unsafe path component accepted: ' + repr(label))
    with tempfile.TemporaryDirectory(prefix='eth-stage-label-control-') as directory:
        base = Path(directory)
        recorder = Recorder(base / 'records')
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(base), 'LANG': 'C'}
        with contextlib.redirect_stdout(io.StringIO()):
            for version in versions:
                for suffix in ['download', 'extract']:
                    label = 'lean-' + version + '-' + suffix
                    receipt = recorder.run(label, [sys.executable, '-c', 'print("CONTROL_OK")'], base, env,
                                           timeout=5, required_text='CONTROL_OK')
                    assert receipt['exit_code'] == 0
            try:
                recorder.run('../escape', [sys.executable, '-c', 'raise SystemExit(99)'], base, env)
            except ValueError:
                pass
            else:
                raise AssertionError('recorder accepted traversal')
        assert not (base / 'escape').exists()
        assert len(list((base / 'records').glob('*/finished.json'))) == 2 * len(versions)
    result = {'scope': 'Stage-name validation and tiny recorder subprocess regression only; no downloads, Lean, Linux or proof checks',
              'passed': True, 'versions': versions, 'validated_stage_labels': sorted(labels),
              'rejected_path_components': len(rejected), 'versioned_recorder_stages_passed': 2 * len(versions),
              'record_py_sha256': sha(HERE / 'record.py'), 'replicate_py_sha256': sha(HERE / 'replicate.py')}
    write_json(args.result, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
