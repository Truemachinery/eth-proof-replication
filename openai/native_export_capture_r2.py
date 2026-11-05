#!/usr/bin/env python3
"""Capture a direct export child; inherit the Recorder's process group."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stop_owned_child(process):
    """Reap only this Popen child; never signal the caller's process group."""
    if process.poll() is None:
        try:
            process.terminate()
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("supply the direct export command after --")
    started = time.monotonic()
    record = {"schema": "native-direct-fd-export/2", "argv": command,
              "cwd": os.getcwd(), "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "stdout_path": str(args.output), "mode": "exclusive direct file descriptor; inherited stderr",
              "process_group": "No new session/group: caller Recorder owns timeout and group termination.",
              "exception_cleanup": "Terminate/wait direct Popen child; kill/wait after five seconds. No group signals."}
    # Lake env is outside this wrapper; its Popen child is the actual exporter.
    # No pipe or per-line fsync for large NDJSON. Recorder captures stderr/receipt.
    process = None
    try:
        with args.output.open("xb", buffering=0) as output:
            process = subprocess.Popen(command, stdout=output, stderr=None, stdin=subprocess.DEVNULL)
            while True:
                try:
                    code = process.wait(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    os.fsync(output.fileno())
            os.fsync(output.fileno())
    except BaseException:
        if process is not None:
            stop_owned_child(process)
        raise
    record.update({"child_exit_code": code, "complete": code == 0,
                   "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "wall_seconds": time.monotonic() - started,
                   "export": {"path": str(args.output), "sha256": sha(args.output),
                              "size_bytes": args.output.stat().st_size}})
    with args.receipt.open("x") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(record, sort_keys=True), flush=True)
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    sys.exit(main())
