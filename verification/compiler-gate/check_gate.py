#!/usr/bin/env python3
"""Real Lean/Lake controls for gate bounds, inherited locks, argv and traces."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = BASE / "controls"
    if out.exists():
        raise SystemExit("refusing to overwrite controls")
    out.mkdir()
    gate = BASE / "control-gate"
    manifest = json.loads((gate / "manifest.json").read_text())
    real = Path(manifest["real_compiler"]["path"]).parent.parent
    prefix = Path(manifest["prefix"])
    executable = prefix / "bin/lean"
    env = dict(os.environ)
    env["PATH"] = str(prefix / "bin") + os.pathsep + env.get("PATH", "")
    env["LEAN_SYSROOT"] = str(prefix)
    env["LAKE_OVERRIDE_LEAN"] = "true"
    env["LEAN_NUM_THREADS"] = "1"
    for key in ("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_PLUGIN_PATH"):
        env.pop(key, None)
    report = {"schema": "lean-gate-controls/1", "checks": {}, "runs": [], "samples": []}

    def run(label, argv, cwd=out, current_env=env, expected=0):
        started = time.monotonic()
        p = subprocess.run(argv, cwd=cwd, env=current_env, text=True,
                           capture_output=True, timeout=30)
        (out / (label + ".stdout.txt")).write_text(p.stdout)
        (out / (label + ".stderr.txt")).write_text(p.stderr)
        row = {"label": label, "argv": list(map(str, argv)), "exit_code": p.returncode,
               "expected_exit": expected, "wall_seconds": time.monotonic() - started}
        report["runs"].append(row)
        print(json.dumps(row), flush=True)
        if p.returncode != expected:
            raise RuntimeError(label + ": " + p.stderr)
        return p

    def rows():
        p = gate / "admissions.jsonl"
        return [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []

    def sample():
        p = subprocess.run([str(gate / "gate-status")], text=True, capture_output=True, check=True)
        d = json.loads(p.stdout)
        d["monotonic_seconds"] = time.monotonic()
        report["samples"].append(d)
        return [s["pid"] for s in d["slots"] if s["pid"]]

    before = len(rows())
    result = run("metadata", [str(executable), "--githash"])
    real_env = dict(env); real_env["LEAN_SYSROOT"] = str(real)
    comparison = run("real-metadata", [str(real / "bin/lean"), "--githash"], current_env=real_env)
    report["checks"]["metadata_identical_and_ungated"] = result.stdout == comparison.stdout and len(rows()) == before
    sleeper = out / "Sleep.lean"
    sleeper.write_text('import Init\ndef main (args : List String) : IO Unit := do\n'
                       '  IO.sleep 700\n  IO.println (String.intercalate "|" args)\n')
    for slots in (2, 4):
        phase_env = dict(env); phase_env["MINING_LAB_LEAN_SLOTS"] = str(slots)
        procs = []
        expected_argv = []
        for i in range(5):
            argv = [str(executable), "--run", str(sleeper), "with spaces", 'quote"value', str(i)]
            expected_argv.append(argv)
            procs.append(subprocess.Popen(argv, env=phase_env, cwd=out, text=True,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE))
        max_active = 0
        seen_holders = set()
        started = time.monotonic()
        while any(p.poll() is None for p in procs):
            holders = sample()
            max_active = max(max_active, len(holders)); seen_holders.update(holders)
            if time.monotonic() - started > 35:
                for p in procs: p.kill()
                raise RuntimeError("concurrency control timeout")
            time.sleep(0.035)
        for i, p in enumerate(procs):
            stdout, stderr = p.communicate()
            (out / f"slots{slots}-{i}.stdout.txt").write_text(stdout)
            (out / f"slots{slots}-{i}.stderr.txt").write_text(stderr)
            if p.returncode != 0 or stdout.strip() != f'with spaces|quote"value|{i}':
                raise RuntimeError("argument forwarding/compile failure: " + stderr)
        admissions = [r for r in rows() if r["event"] == "admitted" and r["pid"] in {p.pid for p in procs}]
        report["checks"][f"slots_{slots}_bounded_and_saturated"] = max_active == slots
        report["checks"][f"slots_{slots}_locks_survive_exec"] = seen_holders == {p.pid for p in procs}
        report["checks"][f"slots_{slots}_argv_unchanged"] = sorted(r["argv"] for r in admissions) == sorted(expected_argv)
        report["checks"][f"slots_{slots}_release_on_exit"] = not sample()
        print(json.dumps({"slots": slots, "maximum_active_locks": max_active, "seen_pids": sorted(seen_holders)}), flush=True)

    workspace = out / "lake-project"; workspace.mkdir()
    (workspace / "lean-toolchain").write_text("leanprover/lean4:v4.34.1\n")
    (workspace / "lakefile.lean").write_text('import Lake\nopen Lake DSL\npackage gateSmoke\n'
        'lean_lib GateFixture where\n  roots := #[`GateFixture.Main]\n  globs := #[`GateFixture.+]\n')
    source_dir = workspace / "GateFixture"; source_dir.mkdir()
    for i in range(4):
        (source_dir / f"Leaf{i}.lean").write_text(
            f'import Init\n#eval IO.sleep 500\ntheorem leaf_{i} : {i} + 1 = {i+1} := rfl\n')
    (source_dir / "Main.lean").write_text("".join(f"import GateFixture.Leaf{i}\n" for i in range(4)))
    sources_before = {str(p.relative_to(workspace)): sha(p) for p in workspace.rglob("*.lean")}
    phase_env = dict(env); phase_env["MINING_LAB_LEAN_SLOTS"] = "2"
    argv = [str(real / "bin/lake"), "build", "+GateFixture.Main"]
    proc = subprocess.Popen(argv, cwd=workspace, env=phase_env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    maximum = 0
    while proc.poll() is None:
        maximum = max(maximum, len(sample())); time.sleep(0.04)
    stdout, stderr = proc.communicate()
    (out / "lake-build.stdout.txt").write_text(stdout)
    (out / "lake-build.stderr.txt").write_text(stderr)
    if proc.returncode:
        raise RuntimeError("ordinary Lake gate build failed: " + stderr)
    report["checks"]["ordinary_lake_compilers_bounded_and_parallel"] = maximum == 2
    real_env = dict(phase_env); real_env["LEAN_SYSROOT"] = str(real)
    real_env["PATH"] = str(real / "bin") + os.pathsep + os.environ.get("PATH", "")
    real_env.pop("LAKE_OVERRIDE_LEAN", None)
    run("original-prefix-no-rebuild", [str(real / "bin/lake"), "--no-build", "build", "+GateFixture.Main"],
        cwd=workspace, current_env=real_env)
    report["checks"]["source_bytes_unchanged"] = sources_before == {str(p.relative_to(workspace)): sha(p)
        for p in workspace.rglob("*.lean")}
    invalid = dict(env); invalid["MINING_LAB_LEAN_SLOTS"] = "5"
    run("invalid-slot-count", [str(executable), "--run", str(sleeper)], current_env=invalid, expected=125)
    report["checks"]["final_slots_empty"] = not sample()
    report["all_checks_passed"] = all(report["checks"].values())
    report["admissions_sha256"] = sha(gate / "admissions.jsonl")
    report["gate_manifest_sha256"] = sha(gate / "manifest.json")
    with (out / "result.json").open("x") as f:
        json.dump(report, f, indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
    print(json.dumps({"all_checks_passed": report["all_checks_passed"], "checks": report["checks"]}), flush=True)
    raise SystemExit(0 if report["all_checks_passed"] else 1)


if __name__ == "__main__":
    main()
