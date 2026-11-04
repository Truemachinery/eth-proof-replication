"""Codex-owned provenance and CLI smoke audit, not an upstream checker.

This records official tool sources/binaries and runs no external proof checks.
It never edits an upstream source tree or relaxes a theorem/axiom policy.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[2]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return {"sha256": h.hexdigest(), "size_bytes": path.stat().st_size}


def output(args, cwd=None, env=None):
    return subprocess.check_output(args, cwd=cwd, env=env, text=True).strip()


def source_record(folder):
    path = BASE / folder
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=path).decode().split("\0")
    return {
        "path": folder,
        "commit": output(["git", "rev-parse", "HEAD"], path),
        "origin": output(["git", "remote", "get-url", "origin"], path),
        "tracked_changes": output(["git", "status", "--porcelain", "--untracked-files=no"], path),
        "tracked_files": [{"path": name, **digest(path / name)} for name in files if name],
    }


def smoke(name, command, expected_exit, env=None, expected_text=None):
    started = time.monotonic()
    p = subprocess.run(command, capture_output=True, text=True, timeout=60, env=env)
    if p.returncode != expected_exit:
        raise RuntimeError((name, p.returncode, p.stdout, p.stderr))
    if expected_text and expected_text not in p.stdout + p.stderr:
        raise RuntimeError((name, "expected diagnostic missing", p.stdout, p.stderr))
    return {"name": name, "command": command, "exit_code": p.returncode,
            "expected_exit_code": expected_exit, "stdout": p.stdout, "stderr": p.stderr,
            "wall_seconds": time.monotonic() - started}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    destination = Path(args.output)
    if destination.exists():
        raise SystemExit("refusing to overwrite an existing manifest")
    sources = ["comparator-source", "lean4export-434-source", "lean4export-433-source", "nanoda-source"]
    relative_binaries = {
        "comparator435": "comparator-source/.lake/build/bin/comparator",
        "lean4export4341": "lean4export-434-source/.lake/build/bin/lean4export",
        "lean4export4331": "lean4export-433-source/.lake/build/bin/lean4export",
        "nanoda": "nanoda-source/target/release/nanoda_bin",
    }
    for relative in relative_binaries.values():
        if not (BASE / relative).is_file():
            raise SystemExit("missing built binary: " + relative)
    records = [smoke("comparator_missing_config", [str(BASE / relative_binaries["comparator435"])],
                     1, expected_text="Expected config file path as first argument")]
    for version, sibling, label in [("4.34.1", "openai", "4341"), ("4.33.1", "anthropic", "4331")]:
        prefix = BASE.parent / sibling / "elan/toolchains" / ("leanprover--lean4---v" + version)
        executable = BASE / relative_binaries["lean4export" + label]
        env = dict(os.environ, LEAN_SYSROOT=str(prefix), LEAN_NUM_THREADS="2")
        command = [str(prefix / "bin/lake"), "--dir", str(BASE / ("lean4export-" + label[:3] + "-source")),
                   "env", str(executable)]
        record = smoke("exporter" + label + "_empty_environment", command, 0, env)
        lines = [json.loads(line) for line in record["stdout"].splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("exporter produced no metadata")
        record["metadata"] = lines[0]
        if lines[0]["meta"]["lean"]["version"] != version:
            raise RuntimeError(("exporter compiler version mismatch", version, lines[0]))
        if lines[0]["meta"]["format"]["version"] != "3.1.0":
            raise RuntimeError(("unexpected exporter format", lines[0]))
        records.append(record)
    # The pinned checker without a config must fail before reading any export.
    # Its exact no-argument diagnostic/exit code is retained, not inferred as a
    # successful proof check.
    nano = subprocess.run([str(BASE / relative_binaries["nanoda"])], capture_output=True,
                          text=True, timeout=20)
    if nano.returncode == 0:
        raise RuntimeError("nanoda unexpectedly accepted missing configuration")
    if "This program expects a path to a configuration file" not in nano.stdout + nano.stderr:
        raise RuntimeError(("nanoda failed without its expected diagnostic", nano.stdout, nano.stderr))
    records.append({"name": "nanoda_missing_config", "command": [relative_binaries["nanoda"]],
                    "exit_code": nano.returncode, "expected": "nonzero: missing config",
                    "stdout": nano.stdout, "stderr": nano.stderr})
    records.append(smoke("nanoda_help", [str(BASE / relative_binaries["nanoda"]), "--help"],
                         0, expected_text="nanoda_bin 0.4.6-beta"))
    history = json.loads(output([sys.executable, "-m", "mining_lab.checkpoint", "history",
                                 "--agent", "codex-eth-tools", "--task", "eth-native-comparator-tools-20261104"],
                                PROJECT))
    runs = history["revisions"][-1]["runs"]
    result = {
        "scope": "Tool source/build provenance and trivial CLI smoke only; no ETH proof verification",
        "platform": platform.platform(), "python": sys.version,
        "sources": [source_record(folder) for folder in sources],
        "binaries": {key: {"path": name, **digest(BASE / name)} for key, name in relative_binaries.items()},
        "official_development_shim": {"path": "comparator-source/scripts/fake-landrun.sh",
                                      **digest(BASE / "comparator-source/scripts/fake-landrun.sh"),
                                      "isolation": "none; upstream development shim runs child commands unsandboxed"},
        "reviewed_inputs": {name: digest(BASE / name) for name in
                            ["rustup-init.sh", "rustup-init", "rustup-init.sha256", "rust-stable-channel.toml", "tool_audit.py"]},
        "build_and_acquisition_runs": runs, "cli_smoke": records,
        "limitations": ["No external proof was executed by this audit.",
                        "CLI acceptance/rejection is not a checker correctness proof.",
                        "Mac native mode has no Landrun operating-system sandbox.",
                        "Compiler toolchain provenance is supplied separately by the proof owners.",
                        "Source/binary hashes attest file identity, not semantic correctness."],
    }
    with destination.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"output": str(destination), "smoke_cases": len(records),
                      "sources_clean": all(not r["tracked_changes"] for r in result["sources"]),
                      "binary_hashes": {k: v["sha256"] for k, v in result["binaries"].items()}}))


if __name__ == "__main__":
    main()
