#!/usr/bin/env python3
"""Build unchanged upstream modules one at a time to bound child-process concurrency."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "source" / "eth"


def strip_comments(text):
    # Lean permits nested /- ... -/. Preserve line boundaries for anchored imports.
    output = []
    depth = 0
    pos = 0
    while pos < len(text):
        if text.startswith("/-", pos):
            depth += 1
            output.append("  ")
            pos += 2
        elif depth and text.startswith("-/", pos):
            depth -= 1
            output.append("  ")
            pos += 2
        elif depth:
            output.append("\n" if text[pos] == "\n" else " ")
            pos += 1
        elif text.startswith("--", pos):
            end = text.find("\n", pos)
            if end == -1:
                break
            output.append("\n")
            pos = end + 1
        else:
            output.append(text[pos])
            pos += 1
    return "".join(output)


def make_graph():
    mapping = {}
    for path in sorted((PROJECT / "proof").rglob("*.lean")):
        relative = path.relative_to(PROJECT / "proof")
        parts = relative.with_suffix("").parts
        module = ".".join(parts if len(parts) == 1 else parts[1:])
        if module in mapping:
            raise RuntimeError("duplicate module " + module)
        mapping[module] = path
    for module in ("MainResults", "Challenge", "Solution"):
        mapping[module] = PROJECT / (module + ".lean")
    graph = {}
    for module, path in mapping.items():
        imports = []
        source = path.read_text()
        for line in strip_comments(source).splitlines():
            found = re.match(r"\s*(?:(?:public|private)\s+)?import\s+(.+)$", line)
            if found:
                imports.extend(found.group(1).split())
        graph[module] = {
            "path": str(path.relative_to(PROJECT)),
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "project_imports": sorted(set(imports) & mapping.keys()),
            "external_imports": sorted(set(imports) - mapping.keys()),
        }
    ordered = []
    active = set()
    visited = set()

    def visit(module):
        if module in active:
            raise RuntimeError("import cycle at " + module)
        if module in visited:
            return
        active.add(module)
        for dep in graph[module]["project_imports"]:
            visit(dep)
        active.remove(module)
        visited.add(module)
        ordered.append(module)

    for module in sorted(graph):
        visit(module)
    return {"format": "unchanged-source-topological-build-v1", "modules": graph,
            "module_count": len(graph), "order": ordered,
            "concurrency": "One lake build target at a time; project imports built first. "
                           "LEAN_NUM_THREADS=2 bounds threads per Lean process, not Lake's job count."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    graph_path = ROOT / "build-graph.json"
    if args.prepare:
        graph = make_graph()
        with graph_path.open("x") as stream:
            json.dump(graph, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"module_count": graph["module_count"], "path": str(graph_path)}))
        return
    graph = json.loads(graph_path.read_text())
    if graph != make_graph():
        raise SystemExit("source or graph changed since preparation")
    ledger = ROOT / "logs" / "build-topological-r1.jsonl"
    env = dict(os.environ)
    env["LEAN_NUM_THREADS"] = "2"
    start = time.monotonic()
    with ledger.open("x") as journal:
        for index, module in enumerate(graph["order"], 1):
            command = ["lake", "build", "+" + module]
            print("MODULE_START " + json.dumps({"index": index, "total": graph["module_count"],
                                              "module": module, "argv": command}), flush=True)
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            tick = time.monotonic()
            result = subprocess.run(command, cwd=PROJECT, env=env)
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            record = {"index": index, "module": module, "source": graph["modules"][module],
                      "argv": command, "exit_code": result.returncode,
                      "wall_seconds": time.monotonic() - tick,
                      "child_cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                      "elapsed_wall_seconds": time.monotonic() - start,
                      "peak_child_rss_bytes_macos_cumulative": after.ru_maxrss}
            journal.write(json.dumps(record) + "\n")
            journal.flush()
            os.fsync(journal.fileno())
            print("MODULE_END " + json.dumps(record), flush=True)
            if result.returncode:
                raise SystemExit(result.returncode if result.returncode > 0 else 128 - result.returncode)
    print("ALL_TOPOLOGICAL_MODULES_BUILT " + str(graph["module_count"]), flush=True)


if __name__ == "__main__":
    main()
