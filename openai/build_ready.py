#!/usr/bin/env python3
"""Build at most two ready, unchanged project modules; persist each completion.

Lake itself has no assumed process-job limit. Project imports finish before a
module is scheduled. External dependencies must already be present and cached.
The ledger records command wall time, not per-module CPU under concurrency;
the surrounding stage recorder measures aggregate child CPU.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE / "workspace"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    parser.add_argument("--timeout", type=float, default=28800)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--configuration", help="explicit immutable package-configuration revision JSON")
    args = parser.parse_args()
    manifest = json.loads((BASE / "source-manifest.json").read_text())
    if args.configuration:
        revision = json.loads((BASE / args.configuration).read_text())
        if revision["original_source_manifest_sha256"] != digest(BASE / "source-manifest.json"):
            raise SystemExit("configuration revision references another source manifest")
        manifest["workspace_config"] = revision["workspace_config"]
    records = {r["module"]: r for r in manifest["files"]}
    for name, record in records.items():
        path = WORKSPACE / (name.replace(".", "/") + ".lean")
        if digest(path) != record["sha256"]:
            raise SystemExit("source changed: " + name)
    for record in manifest["workspace_config"]:
        if digest(WORKSPACE / record["path"]) != record["sha256"]:
            raise SystemExit("workspace configuration changed")
    cache_ready = json.loads((BASE / "external-dependencies-ready.json").read_text())
    if cache_ready["exit_code"] != 0 or cache_ready["mathlib_commit"] != manifest["mathlib_commit"]:
        raise SystemExit("external dependency preflight has not passed")
    if digest(WORKSPACE / "lake-manifest.json") != cache_ready["workspace_manifest_sha256"]:
        raise SystemExit("dependency manifest changed since external preflight")
    ledger = BASE / "logs/build-ready-r1.jsonl"
    modules_dir = BASE / "logs/modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    completed, attempts = set(), {}
    # A crash may leave a partial raw log before its completion record is written.
    for path in modules_dir.glob("*.attempt*.txt"):
        name, suffix = path.name.rsplit(".attempt", 1)
        attempt = int(suffix.removesuffix(".txt"))
        attempts[name] = max(attempts.get(name, 0), attempt)
    if ledger.exists():
        if not args.resume:
            raise SystemExit("ledger already exists; use explicit --resume")
        for line in ledger.read_text().splitlines():
            item = json.loads(line)
            name = item["module"]
            if name not in records:
                raise SystemExit("ledger names an unknown module: " + name)
            if item.get("source_sha256") != records[name]["sha256"]:
                raise SystemExit("ledger source hash differs from current manifest: " + name)
            attempts[name] = max(attempts.get(name, 0), item["attempt"])
            if item["exit_code"] == 0:
                # Lake will still inspect traces when a dependent is built.
                expected = WORKSPACE / ".lake/build/lib/lean" / (name.replace(".", "/") + ".olean")
                if not expected.is_file():
                    raise SystemExit("recorded module artifact missing: " + name)
                completed.add(name)
    dependencies = {name: set(record["imports"]) & records.keys()
                    for name, record in records.items()}
    active = {}
    stop = {"signal": None}

    def request_stop(signum, _frame):
        stop["signal"] = signum

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, request_stop)
    env = dict(os.environ)
    env["LEAN_NUM_THREADS"] = "2"
    lake = BASE / "elan/toolchains/leanprover--lean4---v4.34.1/bin/lake"
    started = time.monotonic()
    failure = None
    with ledger.open("a" if args.resume else "x") as journal:
        try:
            while len(completed) < len(records):
                if stop["signal"] is not None or time.monotonic() - started > args.timeout:
                    failure = 128 + stop["signal"] if stop["signal"] else 124
                    break
                ready = [name for name in manifest["topological_order"]
                         if name not in completed and name not in active
                         and dependencies[name] <= completed]
                for name in ready[:max(0, args.workers - len(active))]:
                    attempt = attempts.get(name, 0) + 1
                    attempts[name] = attempt
                    log_path = modules_dir / (name + ".attempt" + str(attempt) + ".txt")
                    log = log_path.open("xb", buffering=0)
                    command = [str(lake), "build", "+" + name]
                    proc = subprocess.Popen(command, cwd=WORKSPACE, env=env,
                                            stdout=log, stderr=subprocess.STDOUT,
                                            start_new_session=True)
                    active[name] = {"process": proc, "log": log, "log_path": log_path,
                                    "started": time.monotonic(), "argv": command, "attempt": attempt}
                    print("MODULE_START " + json.dumps({"module": name, "pid": proc.pid,
                          "completed": len(completed), "total": len(records), "argv": command}), flush=True)
                if not active:
                    raise RuntimeError("no ready module; missing dependency or graph cycle")
                time.sleep(0.5)
                for name, item in list(active.items()):
                    os.fsync(item["log"].fileno())
                    code = item["process"].poll()
                    if code is None:
                        continue
                    item["log"].close()
                    record = {"module": name, "attempt": item["attempt"], "argv": item["argv"],
                              "exit_code": code, "wall_seconds": time.monotonic() - item["started"],
                              "elapsed_wall_seconds": time.monotonic() - started,
                              "source_sha256": records[name]["sha256"],
                              "log_path": str(item["log_path"].relative_to(BASE)),
                              "log_sha256": digest(item["log_path"]),
                              "log_size_bytes": item["log_path"].stat().st_size,
                              "per_module_cpu_seconds": None,
                              "cpu_note": "Not attributed under concurrent scheduling; outer recorder measures aggregate."}
                    journal.write(json.dumps(record) + "\n")
                    journal.flush()
                    os.fsync(journal.fileno())
                    print("MODULE_END " + json.dumps(record), flush=True)
                    del active[name]
                    if code:
                        failure = code if code > 0 else 128 - code
                        break
                    completed.add(name)
                if failure is not None:
                    break
        finally:
            for item in active.values():
                try:
                    os.killpg(item["process"].pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            deadline = time.monotonic() + 10
            for item in active.values():
                try:
                    item["process"].wait(timeout=max(0.1, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    pass
                # Lake may exit before its compiler children. Drain its whole group.
                while time.monotonic() < deadline:
                    try:
                        os.killpg(item["process"].pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(0.1)
                try:
                    os.killpg(item["process"].pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                item["process"].wait()
                os.fsync(item["log"].fileno())
                item["log"].close()
            for name, item in active.items():
                drained = False
                for _ in range(30):
                    try:
                        os.killpg(item["process"].pid, 0)
                    except ProcessLookupError:
                        drained = True
                        break
                    time.sleep(0.1)
                if not drained:
                    failure = 125
                record = {"module": name, "attempt": item["attempt"], "argv": item["argv"],
                          "exit_code": item["process"].returncode or 125,
                          "cancelled": True, "process_group_drained": drained,
                          "wall_seconds": time.monotonic() - item["started"],
                          "source_sha256": records[name]["sha256"],
                          "log_path": str(item["log_path"].relative_to(BASE)),
                          "log_sha256": digest(item["log_path"]),
                          "log_size_bytes": item["log_path"].stat().st_size}
                journal.write(json.dumps(record) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
    for name, record in records.items():
        if digest(WORKSPACE / (name.replace(".", "/") + ".lean")) != record["sha256"]:
            raise SystemExit("source changed during build: " + name)
    for record in manifest["workspace_config"]:
        if digest(WORKSPACE / record["path"]) != record["sha256"]:
            raise SystemExit("workspace configuration changed during build")
    print(json.dumps({"completed_project_modules": len(completed), "total_project_modules": len(records),
                      "wall_seconds": time.monotonic() - started, "failure_exit_code": failure,
                      "lean_threads_per_invocation": 2, "max_ready_lake_targets": args.workers,
                      "ledger": str(ledger)}, indent=2), flush=True)
    raise SystemExit(failure or 0)


if __name__ == "__main__":
    main()
