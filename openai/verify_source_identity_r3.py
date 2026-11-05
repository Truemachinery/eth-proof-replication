#!/usr/bin/env python3
"""Read-only native OpenAI input identity check; never invoke Lean or Lake."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
REPLICATION = BASE.parent
EXPECTATIONS_SHA256 = "e39147fee63287baea89a046c85c462090f1c443f15b53d809e613631f0cce47"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pinned_json(path, expected):
    if path.is_symlink() or sha(path) != expected:
        raise RuntimeError("pinned metadata mismatch: " + str(path.relative_to(REPLICATION)))
    return json.loads(path.read_text())


def git(path, *args):
    env = dict(os.environ)
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1")
    command = ["/usr/bin/git", "--no-optional-locks", "-c", "core.fsmonitor=false",
               "-c", "core.untrackedCache=false", "-c", "core.pager=cat", "-C", str(path), *args]
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30)
    if result.returncode:
        raise RuntimeError("Git metadata command failed: " + args[0] + " exit="
                           + str(result.returncode) + " stderr_sha256="
                           + hashlib.sha256(result.stderr).hexdigest())
    return result.stdout


def inventory(root):
    found, links = set(), []
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(x for x in dirs if x not in {".lake", ".git"})
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                links.append(str(path.relative_to(root)))
        for name in files:
            if name.endswith(".lean"):
                path = Path(directory) / name
                found.add(str(path.relative_to(root)))
    return found, links


def main():
    started = time.monotonic()
    own_cpu = time.process_time()
    child_cpu = resource.getrusage(resource.RUSAGE_CHILDREN)
    failures = []
    record = {"schema": "openai-native-input-identity/1",
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "Read-only identity metadata during or after source build; no Lean/Lake/proof/checker execution.",
              "helper_sha256": sha(Path(__file__).resolve()), "failures": failures,
              "proof_build_or_kernel_verdict": "Not assessed by this identity checker.",
              "gate_environment_keys_ignored_for_runtime_selection":
                  [x for x in ["LAKE_OVERRIDE_LEAN", "LEAN_SYSROOT", "LEAN_PATH", "LEAN_PLUGIN_PATH"] if x in os.environ]}
    try:
        expected = pinned_json(BASE / "identity_expectations_r1.json", EXPECTATIONS_SHA256)
        record["expectations_sha256"] = EXPECTATIONS_SHA256
        manifest = pinned_json(BASE / "source-manifest.json", expected["source_manifest_sha256"])
        configuration = pinned_json(BASE / "workspace-config-r2.json", expected["workspace_config_r2_sha256"])
        if manifest["commit"] != expected["source_commit"] or configuration["original_source_manifest_sha256"] != expected["source_manifest_sha256"]:
            raise RuntimeError("source/config provenance binding differs")
        workspace, source = BASE / "workspace", BASE / "source"

        def check_file(path, size, wanted, label):
            if path.is_symlink() or not path.is_file():
                failures.append({"kind": "missing-or-symlink-file", "path": label})
                return False
            before = path.stat()
            actual = sha(path)
            after = path.stat()
            stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            passed = actual == wanted and (size is None or after.st_size == size) and stable
            if not passed:
                failures.append({"kind": "file-identity-mismatch", "path": label,
                                 "actual_sha256": actual, "expected_sha256": wanted,
                                 "size_bytes": after.st_size, "stable_during_read": stable})
            return passed

        def check_repository(path, commit, remote, label):
            top = Path(git(path, "rev-parse", "--show-toplevel").decode().strip())
            if top.resolve() != path.resolve():
                raise RuntimeError("Git top-level differs for " + label)
            head = git(path, "rev-parse", "HEAD").decode().strip()
            dirty = git(path, "diff", "--no-ext-diff", "--name-only", commit, "--").decode().splitlines()
            index_dirty = git(path, "diff", "--cached", "--no-ext-diff", "--name-only", commit, "--").decode().splitlines()
            origin = git(path, "remote", "get-url", "origin").decode().strip()
            remote_matches = origin.removesuffix(".git") == remote.removesuffix(".git")
            passed = head == commit and not dirty and not index_dirty and remote_matches
            item = {"name": label, "expected_commit": commit, "actual_commit": head,
                    "tracked_changes_against_expected": dirty,
                    "tracked_index_changes_against_expected": index_dirty,
                    "remote_matches_expected_https_repository": remote_matches,
                    "passed": passed}
            if not passed:
                failures.append({"kind": "repository-identity-mismatch", "name": label})
            return item

        record["upstream"] = check_repository(source, expected["source_commit"], expected["source_remote"], "upstream-openai")
        expected_names = set()
        for row in manifest["files"]:
            name = row["module"].replace(".", "/") + ".lean"
            if name in expected_names or row["path"] != "lean/" + name:
                raise RuntimeError("invalid source-manifest module mapping")
            expected_names.add(name)
            check_file(source / row["path"], row["size_bytes"], row["sha256"], "upstream/" + row["path"])
            check_file(workspace / name, row["size_bytes"], row["sha256"], "workspace/" + name)
        actual_names, linked_dirs = inventory(workspace)
        expected_inventory = expected_names | {r["path"] for r in configuration["workspace_config"] if r["path"].endswith(".lean")}
        if actual_names != expected_inventory or linked_dirs or len(expected_names) != expected["module_count"]:
            failures.append({"kind": "workspace-lean-inventory-mismatch",
                             "unexpected": sorted(actual_names - expected_inventory),
                             "missing": sorted(expected_inventory - actual_names), "symlink_directories": linked_dirs})
        record["closure_source_files_checked_per_copy"] = len(expected_names)
        record["workspace_lean_inventory_count"] = len(actual_names)
        record["expected_workspace_lean_inventory_count"] = len(expected_inventory)
        record["workspace_config_files_checked"] = len(configuration["workspace_config"])
        record["workspace_lean_config_files_checked"] = sum(r["path"].endswith(".lean") for r in configuration["workspace_config"])
        record["workspace_inventory_excludes"] = [".lake", ".git"]
        for row in configuration["workspace_config"]:
            check_file(workspace / row["path"], None, row["sha256"], "workspace/" + row["path"])
        if (workspace / "lean-toolchain").read_text().strip() != expected["lean_toolchain"]:
            failures.append({"kind": "unexpected-lean-toolchain"})
        lakefile = (workspace / "lakefile.lean").read_text()
        required_globs = ["globs := #[`OAI.Algorithms.SubexponentialSAT.+]", "globs := #[`ComparatorChallenges.+]"]
        record["recorded_r2_library_globs_present"] = all(x in lakefile for x in required_globs)
        if not record["recorded_r2_library_globs_present"]:
            failures.append({"kind": "missing-recorded-r2-library-globs"})
        check_file(source / "lean/ComparatorChallenges/SubexponentialSAT.json", None,
                   expected["original_comparator_config_sha256"], "upstream/original-comparator-config")
        check_file(workspace / "lake-manifest.json", None, expected["workspace_lock_sha256"], "workspace/prebuild-dependency-lock")
        ready = pinned_json(BASE / "external-dependencies-ready.json", expected["prebuild_lock_provenance"]["receipt_sha256_newly_observed"])
        if ready["exit_code"] != 0 or ready["workspace_manifest_sha256"] != expected["workspace_lock_sha256"]:
            failures.append({"kind": "prebuild-lock-receipt-mismatch"})
        locked = json.loads((workspace / "lake-manifest.json").read_text())
        locked_rows = {x["name"]: x for x in locked["packages"]}
        wanted_rows = {x["name"]: x for x in expected["expected_dependencies"]}
        if len(locked_rows) != len(locked["packages"]) or set(locked_rows) != set(wanted_rows):
            failures.append({"kind": "dependency-lock-name-set-mismatch"})
        mathlib = workspace / ".lake/packages/mathlib"
        provenance = expected["dependency_expectations_source"]
        blob = git(mathlib, "show", provenance["commit"] + ":lake-manifest.json")
        oid = git(mathlib, "rev-parse", provenance["commit"] + ":lake-manifest.json").decode().strip()
        if hashlib.sha256(blob).hexdigest() != provenance["blob_sha256"] or oid != provenance["git_blob_oid"]:
            raise RuntimeError("pinned Mathlib dependency declaration object changed")
        derived = {x["name"]: {k: x.get(k) for k in ["name", "rev", "url", "type", "subDir", "manifestFile", "configFile"]}
                   for x in json.loads(blob)["packages"]}
        if derived != {name: row for name, row in wanted_rows.items() if name != "mathlib"}:
            raise RuntimeError("dependency expectations do not derive from pinned Mathlib object")
        record["dependencies"] = []
        for name, row in wanted_rows.items():
            if name in locked_rows and any(locked_rows[name].get(k) != value for k, value in row.items()):
                failures.append({"kind": "dependency-lock-declaration-mismatch", "name": name})
            record["dependencies"].append(check_repository(workspace / ".lake/packages" / name, row["rev"], row["url"], name))

        runtime_source = expected["runtime_pin_source"]
        pinned_json(BASE / runtime_source["primary_manifest"], runtime_source["primary_manifest_sha256"])
        pinned_json(REPLICATION / "verification-tools/runtime-identities.json", runtime_source["shared_runtime_inventory_sha256"])
        pinned_json(REPLICATION / "verification-tools/compiler-identities.json", runtime_source["shared_compiler_inventory_sha256"])
        prefix = BASE / "elan/toolchains/leanprover--lean4---v4.34.1"
        if prefix.is_symlink() or prefix.resolve() != prefix.absolute():
            raise RuntimeError("real original toolchain prefix resolves through an override")
        record["selected_real_runtime_prefix"] = str(prefix)
        record["runtime_files"] = []
        for row in expected["expected_runtime_files"]:
            passed = check_file(prefix / row["path"], row["size_bytes"], row["sha256"], "real4341/" + row["path"])
            record["runtime_files"].append({"path": row["path"], "expected_sha256": row["sha256"], "passed": passed})
        record["historical_vs_new_observation"] = "Expected source/config/lock/runtime facts come from the explicit expectation provenance. This run newly observes current identities only; no historical archive hash or completed proof verdict is asserted."
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        failures.append({"kind": "identity-check-error", "error": str(error)})
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record.update({"all_pinned_input_checks_passed": not failures,
                   "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "wall_seconds": time.monotonic() - started,
                   "own_cpu_seconds": time.process_time() - own_cpu,
                   "reaped_git_child_cpu_seconds": after.ru_utime + after.ru_stime - child_cpu.ru_utime - child_cpu.ru_stime,
                   "limitations": "No dependency object-cache rederivation, build-output validation, kernel/axiom audit, archive-download hash or system-library verification. Tracked cleanliness uses Git; closure bytes and selected runtime files are hashed directly."})
    print(json.dumps(record, indent=2), flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
