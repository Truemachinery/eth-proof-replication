#!/usr/bin/env python3
"""Recheck the previously pinned public source, dependency heads, and Lean runtime."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def main():
    manifest_path = ROOT / "source-manifest.json"
    provenance_path = ROOT / "dependency-provenance.json"
    manifest = json.loads(manifest_path.read_text())
    provenance = json.loads(provenance_path.read_text())
    source = ROOT / "source"
    prefix = ROOT / "elan/toolchains/leanprover--lean4---v4.33.1"
    failures = []
    head = git(source, "rev-parse", "HEAD")
    source_dirty = git(source, "diff", "HEAD", "--name-only")
    if head != manifest["commit"] or source_dirty:
        failures.append({"source_head": head, "tracked_changes": source_dirty})
    for item in manifest["files"]:
        path = source / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            failures.append({"source_file_mismatch": item["path"]})
    packages = []
    for item in provenance["packages"]:
        path = source / "eth/.lake/packages" / item["name"]
        actual = git(path, "rev-parse", "HEAD")
        dirty = git(path, "diff", "HEAD", "--name-only")
        matched = actual == item["declared"]["rev"] and not dirty
        packages.append({"name": item["name"], "actual_commit": actual,
                         "matches_pinned_commit_and_clean_tracked_worktree": matched,
                         "tracked_changes": dirty})
        if not matched:
            failures.append({"dependency_mismatch": item["name"]})
    for item in provenance["installed_tool_files"]:
        path = prefix / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            failures.append({"installed_lean_runtime_mismatch": item["path"]})
    record = {
        "format": "anthropic-eth-pinned-input-identity-v1",
        "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "verifier_script_sha256": digest(Path(__file__).resolve()),
        "source_manifest_sha256": digest(manifest_path),
        "dependency_provenance_sha256": digest(provenance_path),
        "source_commit": head,
        "source_files_checked": len(manifest["files"]),
        "packages": packages,
        "installed_lean_files_checked": len(provenance["installed_tool_files"]),
        "all_pinned_inputs_match": not failures,
        "failures": failures,
        "limitations": "Rechecks pinned tracked public inputs and selected installed Lean runtime files; "
                       "does not independently rederive dependency build caches or toolchain archive hashes.",
    }
    print(json.dumps(record, indent=2), flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
