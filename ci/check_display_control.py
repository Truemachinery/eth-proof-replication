#!/usr/bin/env python3
"""Local display-only regression; no GitHub runner or proof verification."""
import argparse
import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from record import Recorder, display_output, sha, write_json

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--result', type=Path, required=True)
    args = p.parse_args()
    payload = (b'::warning::modern\nleading ##[warning]legacy\nprogress\r::error::after-cr\n'
               b'##[add-mask]CONTROL_VALUE\ninvalid-utf8-\xff\nYour solution is okay!\r\n')
    displayed = ''.join(display_output(line) for line in payload.splitlines(keepends=True))
    assert '##[' not in displayed and '\r' not in displayed
    assert not any(line.lstrip().startswith('::') for line in displayed.splitlines())
    assert r'##\x5b' in displayed and r'\r' in displayed
    # The old prefix alone left a legacy marker recognized by the pinned runner parser.
    assert '##[' in '| ' + payload.decode(errors='replace')
    encoded = base64.b64encode(payload).decode('ascii')
    # Keep literal command markers out of the trusted prepared-argv diagnostic itself.
    code = 'import base64,sys;sys.stdout.buffer.write(base64.b64decode(' + repr(encoded) + '))'
    with tempfile.TemporaryDirectory(prefix='eth-display-control-') as temporary:
        root = Path(temporary)
        recorder = Recorder(root / 'records')
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(root), 'LANG': 'C'}
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            receipt = recorder.run('display-success', [sys.executable, '-c', code], root, env,
                                   required_text='Your solution is okay!')
        child_lines = [line for line in captured.getvalue().splitlines() if line.startswith('| ')]
        assert child_lines and all('##[' not in line and '\r' not in line for line in child_lines)
        raw = root / 'records/display-success/raw.log'
        assert raw.read_bytes() == payload
        assert receipt['raw_log_sha256'] == hashlib.sha256(payload).hexdigest()
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                recorder.run('display-failure', [sys.executable, '-c', code + ';raise SystemExit(7)'], root, env)
            except subprocess.CalledProcessError as error:
                assert error.returncode == 7
            else:
                raise AssertionError('nonzero child exit was changed')
            export = root / 'export.raw'
            exported = recorder.run('display-export', [sys.executable, '-c', code], root, env, stdout_file=export)
        assert export.read_bytes() == payload
        assert exported['export']['sha256'] == hashlib.sha256(payload).hexdigest()
    result = {'scope': 'Local recorder display/raw-byte regression only; no GitHub runner, Lean, Linux or proof checks',
              'passed': True, 'checks': ['modern prefix and legacy marker/CR display neutralization',
                'invalid UTF8 affects display only; raw bytes and SHA remain exact',
                'required success line checked against unchanged raw stream',
                'nonzero child exit preserved', 'export stdout bytes and SHA unchanged'],
              'record_py_sha256': sha(HERE / 'record.py'),
              'primary_sources': ['https://github.com/actions/runner/blob/v2.338.2/src/Runner.Common/ActionCommand.cs#L119',
                'https://github.com/actions/runner/blob/v2.338.2/src/Runner.Worker/ActionCommandManager.cs#L62']}
    write_json(args.result, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
