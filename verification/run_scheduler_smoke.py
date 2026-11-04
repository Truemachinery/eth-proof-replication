#!/usr/bin/env python3
"""Bounded real-Lean integration controls for a copied ready-module scheduler."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("scheduler-smoke")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open("w") as out:
        json.dump(value, out, indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())


def main():
    if BASE.exists():
        raise SystemExit("refusing to overwrite smoke fixture")
    BASE.mkdir()
    workspace = BASE / "workspace"
    workspace.mkdir()
    (BASE / "logs").mkdir()
    toolchain = ROOT / "openai/elan/toolchains/leanprover--lean4---v4.34.1"
    link = BASE / "elan/toolchains/leanprover--lean4---v4.34.1"
    link.parent.mkdir(parents=True)
    link.symlink_to(toolchain, target_is_directory=True)
    shutil.copyfile(ROOT / "openai/build_ready.py", BASE / "build_ready.py")
    (workspace / "lean-toolchain").write_text("leanprover/lean4:v4.34.1\n")
    (workspace / "lakefile.lean").write_text(
        'import Lake\nopen Lake DSL\npackage schedulerSmoke\n'
        'lean_lib Fixture where\n  roots := #[`A, `B, `C, `External]\n')
    # A sleeps during trusted fixture compilation to exercise cleanup of a live sibling when B fails.
    sources = {
        "A": "import Init\n#eval IO.sleep 2000\ntheorem fixture_a : 1 + 1 = 2 := rfl\n",
        "B": "import External\ntheorem fixture_b : 3 + 1 = 4 := rfl\n",
        "C": "import A\nimport B\ntheorem fixture_c : 5 + 1 = 6 := rfl\n",
    }
    imports = {"A": ["Init"], "B": ["External"], "C": ["A", "B"]}
    records = []
    for name, source in sources.items():
        path = workspace / (name + ".lean")
        path.write_text(source)
        records.append({"module": name, "sha256": sha(path), "imports": imports[name]})
    manifest = {"mathlib_commit": "fixture-no-mathlib", "files": records,
                "topological_order": ["A", "B", "C"], "workspace_config": [
                    {"path": name, "sha256": sha(workspace / name)}
                    for name in ("lean-toolchain", "lakefile.lean")]}
    write_json(BASE / "source-manifest.json", manifest)
    # Deliberately simulate an incomplete external-dependency preflight in the failure control only.
    write_json(BASE / "external-dependencies-ready.json",
               {"exit_code": 0, "mathlib_commit": "fixture-no-mathlib",
                "scope": "trusted test fixture; missing External is deliberate"})
    env = dict(os.environ)
    env["PATH"] = str(toolchain / "bin") + os.pathsep + env.get("PATH", "")
    env["LEAN_SYSROOT"] = str(toolchain)
    env["LEAN_NUM_THREADS"] = "1"
    env["ELAN_HOME"] = str(ROOT / "openai/elan")
    for key in ("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_PLUGIN_PATH"):
        env.pop(key, None)
    report = {"schema": "eth-scheduler-smoke/1", "scheduler_sha256": sha(BASE / "build_ready.py"),
              "toolchain": str(toolchain), "runs": [], "checks": {}}

    def run(label, argv, expected):
        started = time.monotonic()
        proc = subprocess.Popen(argv, cwd=workspace, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            output, _ = proc.communicate(timeout=40)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                output, _ = proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                output, _ = proc.communicate()
            raise RuntimeError("smoke stage timed out: " + label)
        log = BASE / "logs" / (label + ".txt")
        with log.open("x") as out:
            out.write(output)
            out.flush()
            os.fsync(out.fileno())
        row = {"label": label, "argv": argv, "exit_code": proc.returncode,
               "expected": expected, "wall_seconds": time.monotonic() - started,
               "log": str(log.relative_to(BASE)), "log_sha256": sha(log)}
        row["passed"] = proc.returncode == 0 if expected == "success" else proc.returncode != 0
        report["runs"].append(row)
        write_json(BASE / "progress.json", report)
        print(json.dumps(row), flush=True)
        if not row["passed"]:
            raise RuntimeError("unexpected stage outcome: " + label)
        return output

    command = [sys.executable, str(BASE / "build_ready.py"), "--workers", "2", "--timeout", "25"]
    first = run("missing-external-failure", command, "failure")
    (workspace / "External.lean").write_text(
        "import Init\ntheorem fixture_external : 7 + 1 = 8 := rfl\n")
    run("supply-external", [str(toolchain / "bin/lake"), "build", "+External"], "success")
    second = run("resume-success", command + ["--resume"], "success")
    run("final-lake-check", [str(toolchain / "bin/lake"), "build", "+C"], "success")

    # Source guard, then a different-manifest/old-ledger guard; both are intentionally rejected.
    a_path = workspace / "A.lean"
    original = a_path.read_bytes()
    a_path.write_bytes(original + b"\n-- intentional source-drift control\n")
    drift = run("source-drift-rejected", command + ["--resume"], "failure")
    changed_manifest = json.loads(json.dumps(manifest))
    next(r for r in changed_manifest["files"] if r["module"] == "A")["sha256"] = sha(a_path)
    write_json(BASE / "source-manifest.json", changed_manifest)
    ledger_drift = run("ledger-drift-rejected", command + ["--resume"], "failure")
    a_path.write_bytes(original)
    write_json(BASE / "source-manifest.json", manifest)
    run("final-resume-no-work", command + ["--resume"], "success")

    rows = [json.loads(line) for line in (BASE / "logs/build-ready-r1.jsonl").read_text().splitlines()]
    starts = [json.loads(line.removeprefix("MODULE_START ")) for output in (first, second)
              for line in output.splitlines() if line.startswith("MODULE_START ")]
    group_checks = []
    for row in starts:
        try:
            os.killpg(row["pid"], 0)
            absent = False
        except ProcessLookupError:
            absent = True
        group_checks.append({"pid": row["pid"], "process_group_absent": absent})
    completed = {row["module"] for row in rows if row["exit_code"] == 0}
    log_paths = [row["log_path"] for row in rows]
    report["checks"] = {
        "all_three_modules_completed": completed == {"A", "B", "C"},
        "two_ready_starts_before_completion": first.find('"module": "B"') < first.find("MODULE_END "),
        "c_scheduled_only_after_a_b": second.rfind('"module": "C"') > 0,
        "cancelled_sibling_recorded": any(row.get("cancelled") for row in rows),
        "cancelled_groups_drained": all(row.get("process_group_drained", True) for row in rows),
        "no_process_groups_remaining": all(row["process_group_absent"] for row in group_checks),
        "unique_recorded_log_paths": len(log_paths) == len(set(log_paths)),
        "ledger_source_hashes_match_manifest": all(
            row["source_sha256"] == next(r for r in records if r["module"] == row["module"])["sha256"]
            for row in rows),
        "source_drift_guard_message": "source changed: A" in drift,
        "ledger_drift_guard_message": "ledger source hash differs from current manifest: A" in ledger_drift,
    }
    report["process_groups"] = group_checks
    report["all_checks_passed"] = all(report["checks"].values())
    write_json(BASE / "result.json", report)
    print(json.dumps({"all_checks_passed": report["all_checks_passed"], "checks": report["checks"]}), flush=True)
    raise SystemExit(0 if report["all_checks_passed"] else 1)


if __name__ == "__main__":
    main()
