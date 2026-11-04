#!/usr/bin/env python3
"""Make a minimal Lake workspace from byte-identical pinned ETH source files.

This changes package configuration, not proof sources. See source-manifest.json.
Run only after checking out the explicitly pinned public upstream commit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

BASE = None
SOURCE = None
COMMIT = "4eaee87548250b2682affda7d05d947c05554bae"
MATHLIB = "d13f23b723b8a846827a245b89c10fc7d3f11612"
TARGETS = ["OAI.Algorithms.SubexponentialSAT.Main", "ComparatorChallenges.SubexponentialSAT"]


def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()


def without_comments(text):
    # Nested block comments are legal in Lean. Preserve line boundaries for imports.
    out, i, depth = [], 0, 0
    while i < len(text):
        if text.startswith("/-", i):
            depth += 1
            i += 2
        elif depth and text.startswith("-/", i):
            depth -= 1
            i += 2
        elif depth:
            if text[i] == "\n":
                out.append("\n")
            i += 1
        elif text.startswith("--", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
        else:
            out.append(text[i])
            i += 1
    if depth:
        raise ValueError("unterminated comment")
    return "".join(out)


def main():
    global BASE, SOURCE
    p = argparse.ArgumentParser()
    p.add_argument("--base", type=Path, required=True)
    a = p.parse_args()
    BASE = a.base.resolve()
    SOURCE = BASE / "source"
    if Path(git("rev-parse", "--show-toplevel")).resolve() != SOURCE.resolve():
        raise SystemExit("checkout path resolves to another repository")
    if git("rev-parse", "HEAD") != COMMIT:
        raise SystemExit("unexpected upstream commit")
    if git("remote", "get-url", "origin") != "https://github.com/openai/math.git":
        raise SystemExit("unexpected upstream remote")
    if git("status", "--porcelain", "--", "lean"):
        raise SystemExit("upstream Lean sources have modifications")
    manifest = json.loads((SOURCE / "lean/lake-manifest.json").read_text())
    mathlib = next(p for p in manifest["packages"] if p["name"] == "mathlib")
    if mathlib["rev"] != MATHLIB:
        raise SystemExit("unexpected mathlib pin")
    workspace = BASE / "workspace"
    if workspace.exists():
        raise SystemExit("refusing to overwrite a workspace")
    visited, active, ordered, records, external = set(), set(), [], [], set()

    def visit(module):
        if module in visited:
            return
        if module in active:
            raise ValueError("import cycle: " + module)
        path = SOURCE / "lean" / (module.replace(".", "/") + ".lean")
        if not path.is_file():
            if module.split(".")[0] not in {"Mathlib", "Lean", "Std", "Init", "Batteries", "Qq", "Aesop"}:
                raise ValueError("unexpected external import: " + module)
            external.add(module)
            return
        active.add(module)
        text = path.read_text()
        imports = []
        for match in re.finditer(r"^\s*(?:(?:public|private)\s+)?import\s+([^\n]+)", without_comments(text), re.M):
            imports.extend(match.group(1).split())
        for dependency in imports:
            visit(dependency)
        data = path.read_bytes()
        records.append({"module": module, "path": str(path.relative_to(SOURCE)),
                        "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                        "imports": imports})
        ordered.append(module)
        active.remove(module)
        visited.add(module)

    for target in TARGETS:
        visit(target)
    workspace.mkdir()
    for record in records:
        destination = workspace / (record["module"].replace(".", "/") + ".lean")
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = (SOURCE / record["path"]).read_bytes()
        destination.write_bytes(data)
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == record["sha256"]
    (workspace / "lean-toolchain").write_bytes((SOURCE / "lean/lean-toolchain").read_bytes())
    (workspace / "lakefile.lean").write_text('''import Lake
open Lake DSL
package OAI where
  version := v!"0.1.0"
  fixedToolchain := true
  leanOptions := #[⟨`autoImplicit, false⟩]
require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "''' + MATHLIB + '''"
@[default_target] lean_lib OAI where
  roots := #[`OAI.Algorithms.SubexponentialSAT.Main]
  globs := #[`OAI.Algorithms.SubexponentialSAT.+]
lean_lib ComparatorChallenges where
  roots := #[`ComparatorChallenges.SubexponentialSAT]
  globs := #[`ComparatorChallenges.+]
''')
    result = {"upstream_url": git("remote", "get-url", "origin"), "commit": COMMIT,
              "mathlib_commit": MATHLIB, "targets": TARGETS, "project_module_count": len(records),
              "external_imports": sorted(external), "topological_order": ordered, "files": records,
              "configuration_deviation": "Minimal Lake package: exact upstream toolchain, autoImplicit=false, "
              "exact mathlib pin; byte-identical source import closure; unrelated packages omitted. "
              "This source workspace is used by a separate real Linux Landrun Comparator stage."}
    for filename in ["lean-toolchain", "lakefile.lean"]:
        data = (workspace / filename).read_bytes()
        result.setdefault("workspace_config", []).append({"path": filename, "sha256": hashlib.sha256(data).hexdigest()})
    (BASE / "source-manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"files", "topological_order"}}, indent=2))


if __name__ == "__main__":
    main()
