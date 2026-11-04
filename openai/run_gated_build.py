#!/usr/bin/env python3
"""Use one ordinary Lake build with a reviewed task-local compiler admission gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slots", type=int, choices=(2, 3, 4), default=3)
    args = parser.parse_args()
    workspace = BASE / "workspace"
    manifest_path = BASE / "source-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    revision = json.loads((BASE / "workspace-config-r2.json").read_text())
    if revision["original_source_manifest_sha256"] != sha(manifest_path):
        raise SystemExit("source manifest differs from configuration revision")
    for row in manifest["files"]:
        path = workspace / (row["module"].replace(".", "/") + ".lean")
        if sha(path) != row["sha256"]:
            raise SystemExit("upstream source drift: " + row["module"])
    for row in revision["workspace_config"]:
        if sha(workspace / row["path"]) != row["sha256"]:
            raise SystemExit("workspace configuration drift")
    ready = json.loads((BASE / "external-dependencies-ready.json").read_text())
    if ready["exit_code"] or ready["mathlib_commit"] != manifest["mathlib_commit"]:
        raise SystemExit("external dependency preflight missing")
    if sha(workspace / "lake-manifest.json") != ready["workspace_manifest_sha256"]:
        raise SystemExit("dependency manifest drift")
    gate_dir = BASE / "compiler-gate-r1"
    gate = json.loads((gate_dir / "manifest.json").read_text())
    real_prefix = BASE / "elan/toolchains/leanprover--lean4---v4.34.1"
    if Path(gate["real_compiler"]["path"]) != real_prefix / "bin/lean":
        raise SystemExit("gate uses a different compiler")
    for key in ("real_compiler", "source", "configuration", "gate", "status"):
        row = gate[key]
        if sha(Path(row["path"])) != row["sha256"]:
            raise SystemExit("compiler gate drift: " + key)
    gated_prefix = gate_dir / "prefix"
    for path in real_prefix.iterdir():
        entries = path.iterdir() if path.name == "bin" else [path]
        for original in entries:
            if path.name == "bin" and original.name == "lean":
                continue
            linked = gated_prefix / original.relative_to(real_prefix)
            if not linked.is_symlink() or linked.resolve() != original.resolve():
                raise SystemExit("gated prefix differs from real toolchain: " + str(linked))
    env = dict(os.environ)
    for variable in ("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_PLUGIN_PATH"):
        env.pop(variable, None)
    env.update({"ELAN_HOME": str(BASE / "elan"), "XDG_CACHE_HOME": str(BASE / "cache"),
                "MATHLIB_CACHE_DIR": str(BASE / "cache/mathlib"), "LAKE_OVERRIDE_LEAN": "true",
                "LEAN_SYSROOT": str(gated_prefix), "MINING_LAB_LEAN_SLOTS": str(args.slots),
                "LEAN_NUM_THREADS": "4",
                "PATH": str(gated_prefix / "bin") + os.pathsep + str(real_prefix / "bin")
                        + os.pathsep + env.get("PATH", "")})
    command = [str(real_prefix / "bin/lake"), "build", "+OAI.Algorithms.SubexponentialSAT.Main",
               "+ComparatorChallenges.SubexponentialSAT"]
    print(json.dumps({"mode": "ordinary_lake_with_compiler_admission", "argv": command,
                      "cwd": str(workspace), "source_module_count": len(manifest["files"]),
                      "source_hashes_checked": True, "compiler_frontend_slots": args.slots,
                      "lean_runtime_threads": 4, "gate_manifest_sha256": sha(gate_dir / "manifest.json"),
                      "limitations": "Gate bounds Lean frontends, not C/link jobs; cached project objects "
                                      "come only from this run's earlier recorded source attempts."}, indent=2), flush=True)
    os.chdir(workspace)
    os.execve(command[0], command, env)


if __name__ == "__main__":
    main()
