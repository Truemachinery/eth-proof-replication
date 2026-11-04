#!/usr/bin/env python3
"""Create a task-local symlinked Lean prefix with a C admission wrapper."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def identity(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": path.stat().st_size}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-prefix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    real = args.real_prefix.resolve()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit("refusing to overwrite gate prefix")
    output.mkdir(parents=True)
    prefix = output / "prefix"
    prefix.mkdir()
    (prefix / "bin").mkdir()
    for path in real.iterdir():
        if path.name == "bin":
            for binary in path.iterdir():
                if binary.name != "lean":
                    (prefix / "bin" / binary.name).symlink_to(binary, target_is_directory=binary.is_dir())
        else:
            (prefix / path.name).symlink_to(path, target_is_directory=path.is_dir())
    compiler = real / "bin/lean"
    compiler_id = identity(compiler)
    definitions = {"REAL_COMPILER": str(compiler), "EXPECTED_COMPILER_SHA": compiler_id["sha256"],
                   "LOCK_PATH": str(output / "slots.lock"), "LOG_PATH": str(output / "admissions.jsonl")}
    header = output / "gate_config.h"
    header.write_text("\n".join("#define " + key + " " + json.dumps(value)
                                for key, value in definitions.items()) + "\n")
    source = Path(__file__).resolve().with_name("lean_gate.c")
    commands = []
    for destination, flags in [(prefix / "bin/lean", []), (output / "gate-status", ["-DGATE_STATUS_EXEC"])]:
        argv = ["/usr/bin/clang", "-std=c11", "-O2", "-Wall", "-Wextra",
                "-Werror", "-Wno-deprecated-declarations", "-Wno-unused-function",
                "-I", str(output), *flags, str(source), "-o", str(destination)]
        proc = subprocess.run(argv, capture_output=True, text=True)
        commands.append({"argv": argv, "exit_code": proc.returncode,
                         "stdout": proc.stdout, "stderr": proc.stderr})
        if proc.returncode:
            print(json.dumps(commands, indent=2))
            raise SystemExit(proc.returncode)
    manifest = {"schema": "lean-compiler-gate/1", "real_compiler": compiler_id,
                "source": identity(source), "configuration": identity(header),
                "gate": identity(prefix / "bin/lean"), "status": identity(output / "gate-status"),
                "prefix": str(prefix), "build_commands": commands,
                "environment": {"LAKE_OVERRIDE_LEAN": "true", "LEAN_SYSROOT": str(prefix),
                                "MINING_LAB_LEAN_SLOTS": "2"},
                "scope": "Compiler admission only; same argv, sources, compiler and normal Lake traces.",
                "limitations": ["No throughput prediction or proof verdict.",
                                "Change slot count only at a recorded boundary; existing holders retain their slots.",
                                "Kernel/runtime library identities are supplied by the parent toolchain manifest."]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
