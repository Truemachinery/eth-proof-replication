#!/usr/bin/env python3
"""Exercise the trusted probe against Init only; never loads an external proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite output")
    probe = Path(__file__).resolve().with_name("AuditTargets.lean")
    lean = args.toolchain.resolve() / "bin/lean"
    env = dict(os.environ)
    env["PATH"] = str(lean.parent) + os.pathsep + env.get("PATH", "")
    env["LEAN_SYSROOT"] = str(args.toolchain.resolve())
    env["LEAN_NUM_THREADS"] = "1"
    # These controls intentionally import only trusted toolchain Init.
    for key in ("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_PLUGIN_PATH"):
        env.pop(key, None)
    cases = [("trusted-theorem", "Nat.add_zero", 0),
             ("missing-theorem", "EthReplicationAudit.NoSuchTheorem", 2),
             ("definition-is-not-theorem", "Nat.add", 2)]
    report = {"schema": "eth-trusted-probe-controls/1", "cases": [],
              "probe_sha256": hashlib.sha256(probe.read_bytes()).hexdigest(),
              "toolchain": str(args.toolchain.resolve()),
              "environment": {"PATH_front": str(lean.parent),
                              "LEAN_SYSROOT": env["LEAN_SYSROOT"],
                              "LEAN_NUM_THREADS": env["LEAN_NUM_THREADS"],
                              "inherited_lean_paths_removed": True}}
    for case, target, expected in cases:
        argv = [str(lean), "--run", str(probe), "Init", target]
        started = time.monotonic()
        proc = subprocess.run(argv, env=env, text=True, capture_output=True, timeout=20)
        records = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        complete = [r for r in records if r.get("event") == "complete"]
        target_rows = [r for r in records if r.get("event") == "target"]
        errors = [r for r in records if r.get("event") == "error"]
        passed = proc.returncode == expected
        if expected == 0:
            passed = passed and len(complete) == 1 and complete[0]["passed"] is True
            passed = passed and len(target_rows) == 1 and target_rows[0]["axioms"] == []
        else:
            passed = passed and len(errors) == 1 and not complete
        row = {"case": case, "argv": argv, "expected_exit_code": expected,
               "exit_code": proc.returncode, "wall_seconds": time.monotonic() - started,
               "stdout": proc.stdout, "stderr": proc.stderr, "records": records,
               "control_passed": bool(passed)}
        report["cases"].append(row)
        print(json.dumps(row), flush=True)
    report["all_controls_passed"] = all(r["control_passed"] for r in report["cases"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as out:
        json.dump(report, out, indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    raise SystemExit(0 if report["all_controls_passed"] else 1)


if __name__ == "__main__":
    main()
