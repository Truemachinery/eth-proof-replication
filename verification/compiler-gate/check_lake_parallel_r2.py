#!/usr/bin/env python3
"""Corrected one-Lake control: four Lake workers, two actual compiler slots."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def main():
    base = Path(__file__).resolve().parent
    gate = base / "control-gate"
    old = base / "controls"
    out = base / "lake-parallel-r2"
    if out.exists():
        raise SystemExit("refusing to overwrite corrected control")
    out.mkdir()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    original_report = json.loads((old / "result.json").read_text())
    snapshot = old / "admissions-r1-snapshot.jsonl"
    with snapshot.open("xb") as f:
        f.write((gate / "admissions.jsonl").read_bytes()); f.flush(); os.fsync(f.fileno())
    if sha(snapshot) != original_report["admissions_sha256"]:
        raise SystemExit("first control admission journal drifted before snapshot")
    workspace = out / "lake-project"
    shutil.copytree(old / "lake-project", workspace, ignore=shutil.ignore_patterns(".lake"))
    source_hashes = {str(p.relative_to(workspace)): sha(p) for p in workspace.rglob("*.lean")}
    manifest = json.loads((gate / "manifest.json").read_text())
    real = Path(manifest["real_compiler"]["path"]).parent.parent
    prefix = Path(manifest["prefix"])
    env = dict(os.environ)
    env.update({"PATH": str(prefix / "bin") + os.pathsep + env.get("PATH", ""),
                "LEAN_SYSROOT": str(prefix), "LAKE_OVERRIDE_LEAN": "true",
                "MINING_LAB_LEAN_SLOTS": "2", "LEAN_NUM_THREADS": "4"})
    for key in ("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_PLUGIN_PATH"):
        env.pop(key, None)
    command = [str(real / "bin/lake"), "build", "+GateFixture.Main"]
    started = time.monotonic()
    proc = subprocess.Popen(command, cwd=workspace, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    samples = []
    while proc.poll() is None:
        query = subprocess.run([str(gate / "gate-status")], text=True, capture_output=True, check=True)
        row = json.loads(query.stdout); row["monotonic_seconds"] = time.monotonic(); samples.append(row)
        if time.monotonic() - started > 35:
            proc.terminate()
            raise RuntimeError("corrected ordinary Lake control exceeded35wall seconds")
        time.sleep(0.04)
    stdout, stderr = proc.communicate()
    (out / "lake.stdout.txt").write_text(stdout); (out / "lake.stderr.txt").write_text(stderr)
    maximum = max(sum(s["pid"] != 0 for s in row["slots"]) for row in samples)
    real_env = dict(env); real_env["LEAN_SYSROOT"] = str(real)
    real_env["PATH"] = str(real / "bin") + os.pathsep + os.environ.get("PATH", "")
    real_env.pop("LAKE_OVERRIDE_LEAN", None)
    check_command = [str(real / "bin/lake"), "--no-build", "build", "+GateFixture.Main"]
    check = subprocess.run(check_command, cwd=workspace, env=real_env, text=True,
                           capture_output=True, timeout=15)
    (out / "original-prefix.stdout.txt").write_text(check.stdout)
    (out / "original-prefix.stderr.txt").write_text(check.stderr)
    final = json.loads(subprocess.check_output([str(gate / "gate-status")], text=True))
    checks = {"lake_build_passed": proc.returncode == 0,
              "two_actual_compiler_locks_with_four_lake_workers": maximum == 2,
              "normal_traces_reused_by_original_prefix": check.returncode == 0,
              "source_bytes_unchanged": source_hashes == {
                  str(p.relative_to(workspace)): sha(p) for p in workspace.rglob("*.lean")},
              "all_slots_released": all(s["pid"] == 0 for s in final["slots"])}
    report = {"schema": "lean-gate-parallel-control-r2/1", "command": command,
              "source_hashes": source_hashes, "lake_exit_code": proc.returncode,
              "original_prefix_command": check_command, "original_prefix_exit_code": check.returncode,
              "maximum_active_compiler_locks": maximum, "samples": samples,
              "checks": checks, "all_checks_passed": all(checks.values()),
              "wall_seconds": time.monotonic() - started,
              "r1_admission_snapshot_sha256": sha(snapshot),
              "admissions_through_r2_sha256": sha(gate / "admissions.jsonl")}
    with (out / "result.json").open("x") as f:
        json.dump(report, f, indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
    print(json.dumps({k: report[k] for k in report if k != "samples"}), flush=True)
    raise SystemExit(0 if report["all_checks_passed"] else 1)


if __name__ == "__main__":
    main()
