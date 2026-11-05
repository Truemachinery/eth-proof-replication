#!/usr/bin/env python3
"""Codex-owned recorder for the reviewed native fake-landrun execution mode.

It forwards the original Nanoda argument vector unchanged, records the inputs,
and never changes the theorem, export, configuration or axiom policy.
"""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time

BASE = Path(__file__).resolve().parent
SHIM_SHA256 = "167507c89d8b3c7667ad78b50df7b19f89883751a01efd1457404fa34a994e8b"


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def identity(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    s = path.stat()
    return {"path": str(path), "sha256": h.hexdigest(), "size_bytes": s.st_size,
            "device": s.st_dev, "inode": s.st_ino, "mtime_ns": s.st_mtime_ns}


def save_bytes(path, data):
    with path.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def save_json(path, data):
    save_bytes(path, (json.dumps(data, indent=2) + "\n").encode())


def archive_export(source, destination):
    h = hashlib.sha256()
    count = 0
    with source.open("rb") as src, destination.open("xb") as dst:
        with gzip.GzipFile(filename="export.ndjson", mode="wb", fileobj=dst,
                           compresslevel=1, mtime=0) as compressed:
            for block in iter(lambda: src.read(1024 * 1024), b""):
                h.update(block)
                count += len(block)
                compressed.write(block)
        dst.flush()
        os.fsync(dst.fileno())
    return {"uncompressed_sha256": h.hexdigest(), "uncompressed_size_bytes": count,
            "gzip": identity(destination)}


def same_bytes(before, after):
    return before["sha256"] == after["sha256"] and before["size_bytes"] == after["size_bytes"]


def main():
    started = time.monotonic()
    own_cpu = time.process_time()
    record = None
    child = None
    checker_exit = None
    details = {"mode": "native_fake_landrun_unsandboxed", "started_at": utc(),
               "wrapper_argv": sys.argv, "wrapper_source": identity(Path(__file__))}
    try:
        shim = Path(os.environ["COMPARATOR_LANDRUN"]).resolve()
        if identity(shim)["sha256"] != SHIM_SHA256:
            raise ValueError("recorder is restricted to the reviewed upstream fake-landrun shim")
        root = Path(os.environ["REPLICATION_CHECKER_RECORD_DIR"]).resolve()
        try:
            root.relative_to(BASE.parent.resolve())
        except ValueError:
            raise ValueError("record directory must be inside this replication artifact tree")
        root.mkdir(parents=True, exist_ok=True)
        record = Path(tempfile.mkdtemp(prefix="nanoda-" + str(os.getpid()) + "-", dir=root))
        details["record_directory"] = str(record)
        details["shim"] = identity(shim)
        if len(sys.argv) != 2:
            raise ValueError("expected the original single Nanoda config-path argument")
        binary = Path(os.environ["NANODA_REAL_BINARY"]).resolve()
        expected = json.loads((BASE / "tool-manifest-r1.json").read_text())["binaries"]["nanoda"]["sha256"]
        binary_before = identity(binary)
        if binary_before["sha256"] != expected:
            raise ValueError("Nanoda binary differs from the audited tool manifest")
        config_path = Path(sys.argv[1]).resolve()
        config_bytes = config_path.read_bytes()
        config = json.loads(config_bytes)
        if config.get("use_stdin", False) or not config.get("export_file_path"):
            raise ValueError("recorder requires Comparator's file-backed export configuration")
        export_path = Path(config["export_file_path"])
        if not export_path.is_absolute():
            export_path = Path.cwd() / export_path
        export_path = export_path.resolve()
        config_before = identity(config_path)
        if hashlib.sha256(config_bytes).hexdigest() != config_before["sha256"]:
            raise ValueError("configuration changed while being archived")
        archive = archive_export(export_path, record / "export.ndjson.gz")
        save_bytes(record / "effective-config.json", config_bytes)
        export_before = identity(export_path)
        if (archive["uncompressed_sha256"] != export_before["sha256"] or
                archive["uncompressed_size_bytes"] != export_before["size_bytes"]):
            raise ValueError("export changed while being archived")
        details.update({"checker_argv": [str(binary)] + sys.argv[1:], "cwd": os.getcwd(),
                        "binary_before": binary_before, "config_before": config_before,
                        "config_archive": identity(record / "effective-config.json"),
                        "export_before": export_before, "export_archive": archive,
                        "effective_policy": config,
                        "policy_changes_by_recorder": False,
                        "inherited_recording_environment": {
                            k: os.environ[k] for k in ["COMPARATOR_LANDRUN", "NANODA_REAL_BINARY",
                                                       "REPLICATION_CHECKER_RECORD_DIR"]}})
        save_json(record / "00-prepared.json", details)
        child_cpu = resource.getrusage(resource.RUSAGE_CHILDREN)
        check_started = time.monotonic()
        child = subprocess.Popen([str(binary)] + sys.argv[1:])
        save_json(record / "01-started.json", {"pid": child.pid, "started_at": utc(),
                                               "checker_argv": [str(binary)] + sys.argv[1:]})
        checker_exit = child.wait()
        after_cpu = resource.getrusage(resource.RUSAGE_CHILDREN)
        details.update({"checker_exit_code": checker_exit,
                        "checker_wall_seconds": time.monotonic() - check_started,
                        "checker_cpu_seconds": after_cpu.ru_utime + after_cpu.ru_stime
                            - child_cpu.ru_utime - child_cpu.ru_stime,
                        "binary_after": identity(binary), "config_after": identity(config_path),
                        "export_after": identity(export_path)})
        unchanged = (same_bytes(binary_before, details["binary_after"])
                     and same_bytes(config_before, details["config_after"])
                     and same_bytes(export_before, details["export_after"]))
        details["inputs_unchanged"] = unchanged
        if not unchanged:
            raise ValueError("checker binary/config/export bytes changed during execution")
        details.update({"finished_at": utc(), "wrapper_wall_seconds": time.monotonic() - started,
                        "wrapper_cpu_seconds": time.process_time() - own_cpu,
                        "wrapper_exit_code": checker_exit, "recording_complete": True})
        save_json(record / "02-finished.json", details)
        if checker_exit < 0:
            signal.signal(-checker_exit, signal.SIG_DFL)
            os.kill(os.getpid(), -checker_exit)
        return checker_exit
    except BaseException as error:
        if child is not None and child.poll() is None:
            try:
                child.terminate()
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    child.kill()
                except ProcessLookupError:
                    pass
                child.wait(timeout=10)
        if child is not None and checker_exit is None:
            checker_exit = child.returncode
        details.update({"finished_at": utc(), "checker_exit_code": checker_exit,
                        "wrapper_exit_code": 125, "recording_complete": False,
                        "error": type(error).__name__ + ": " + str(error),
                        "wrapper_wall_seconds": time.monotonic() - started,
                        "wrapper_cpu_seconds": time.process_time() - own_cpu})
        if record is not None:
            try:
                save_json(record / "99-error.json", details)
            except Exception as save_error:
                print("record_nanoda: could not persist error receipt: " + str(save_error), file=sys.stderr)
        print("record_nanoda: " + details["error"], file=sys.stderr)
        return 125


if __name__ == "__main__":
    sys.exit(main())
