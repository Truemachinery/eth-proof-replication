#!/usr/bin/env python3
"""Aggregate seven closed R2 checks and explicit new worker-stack Nanoda resource-build retry; no verifier execution."""
import argparse
import ast
import datetime
import gzip
import importlib.util
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import sys
import time

BASE = Path(__file__).resolve().parent
TREE = BASE.parent
PROJECT = BASE.parents[2]
WORKSPACE = BASE / "workspace"
REAL = BASE / "elan/toolchains/leanprover--lean4---v4.34.1"
RECORD_ROOT = BASE / "native-phase-records"
OUTPUT_ROOT = BASE / "native-aggregate-records"
LAUNCHER = BASE / "verify_native_phase_r2.py"
LAUNCHER_SHA = "fe3b12c0b8312a6b0cdb5ec1c6d88933cbff796bc92e9403682735d25348c19c"
MODULE = "OAI.Algorithms.SubexponentialSAT.Main"
CHALLENGE = "ComparatorChallenges.SubexponentialSAT"
TARGET = "OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat"
AXIOMS = ["propext", "Quot.sound", "Classical.choice"]
PHASES = ("pre-identity", "trace", "audit", "comparator", "selected-export",
          "extra-nanoda", "original-fresh", "post-identity")
LIMITS = {
    "pre-identity": 300, "trace": 600, "audit": 1800, "comparator": 7200,
    "selected-export": 1800, "extra-nanoda": 7200, "original-fresh": 7200,
    "post-identity": 300,
}
TOOLS = TREE / "verification-tools"
COMPARATOR = TOOLS / "comparator-source/.lake/build/bin/comparator"
EXPORTER = TOOLS / "lean4export-434-source/.lake/build/bin/lean4export"
NANODA = TOOLS / "nanoda-source/target/release/nanoda_bin"
SHIM = TOOLS / "comparator-source/scripts/fake-landrun.sh"
NANODA_RECORDER = TOOLS / "record_nanoda.py"
CAPTURE = BASE / "native_export_capture_r2.py"
CONFIG = BASE / "source/lean/ComparatorChallenges/SubexponentialSAT.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            "invalid nonnegative finite resource/time value")
    return value


def utc(value):
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp lacks timezone")
    return parsed.timestamp()


def canonical(value):
    path = Path(os.path.abspath(value))
    require(path.resolve() == path, "symlink or noncanonical evidence path: " + str(path))
    return path


class Evidence:
    def __init__(self):
        self.rows = {}
        self.stats = {}
        self.public = set()

    def identity(self, value, public=False):
        path = canonical(value)
        require(path.is_file() and not path.is_symlink(), "missing regular evidence: " + str(path))
        if path not in self.rows:
            before = path.stat()
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            after = path.stat()
            key = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
            require(key(before) == key(after), "evidence changed while hashing")
            self.rows[path] = {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": after.st_size}
            self.stats[path] = key(after)
        if public:
            require(path.suffix not in {".ndjson", ".gz"}, "large export cannot enter small-artifact list")
            self.public.add(path)
        return self.rows[path]

    def bind(self, row, path, public=False):
        actual = self.identity(path, public)
        require(all(row.get(k) == actual[k] for k in actual), "artifact binding differs: " + str(path))
        return actual

    def json(self, path, public=False):
        self.identity(path, public)
        def unique(pairs):
            result = {}
            for key, value in pairs:
                require(key not in result, "duplicate JSON key")
                result[key] = value
            return result
        return json.loads(Path(path).read_text(), object_pairs_hook=unique)

    def stable(self):
        for path, before in self.stats.items():
            now = path.stat()
            require((now.st_dev, now.st_ino, now.st_size, now.st_mtime_ns) == before,
                    "evidence changed after hashing: " + str(path))


def assignments(path):
    result = {}
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                result[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return result


def pinned_inputs(evidence):
    require(evidence.identity(LAUNCHER)["sha256"] == LAUNCHER_SHA, "native R2 launcher changed")
    constants = assignments(LAUNCHER)
    require(constants["TIMEOUTS"] == LIMITS and constants["AXIOMS"] == AXIOMS,
            "pinned launcher constants differ")
    files = {}
    for name, wanted in constants["PINS"].items():
        row = evidence.identity(canonical(BASE / name))
        require(row["sha256"] == wanted, "selected pinned input differs: " + name)
        files[name] = row
    configuration = evidence.json(BASE / "workspace-config-r2.json")
    for row in configuration["workspace_config"]:
        actual = evidence.identity(WORKSPACE / row["path"])
        require(actual["sha256"] == row["sha256"], "workspace configuration drift")
        files["workspace/" + row["path"]] = actual
    expected = evidence.json(BASE / "identity_expectations_r1.json")
    for row in expected["expected_runtime_files"]:
        actual = evidence.identity(REAL / row["path"])
        require(actual["sha256"] == row["sha256"] and actual["size_bytes"] == row["size_bytes"],
                "original runtime drift")
        files["real4341/" + row["path"]] = actual
    config = evidence.json(CONFIG)
    require(config["challenge_module"] == CHALLENGE and config["solution_module"] == MODULE
            and config["theorem_names"] == [TARGET] and config["definition_names"] == []
            and config["permitted_axioms"] == AXIOMS and config["enable_nanoda"] is False
            and not config.get("external_kernels"), "original Comparator contract differs")
    content = {"files": files, "launcher": evidence.identity(LAUNCHER), "module": MODULE,
               "challenge": CHALLENGE, "theorems": [TARGET], "original_comparator_nanoda_enabled": False}
    fingerprint = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return content, fingerprint, expected


def phase_command(name, folder, python):
    prefix = [python, str(BASE / "in_workspace.py")]
    operations = {
        "pre-identity": [python, str(BASE / "verify_source_identity_r3.py")],
        "post-identity": [python, str(BASE / "verify_source_identity_r3.py")],
        "trace": ["lake", "--no-build", "build", "+" + MODULE, "+" + CHALLENGE],
        "audit": ["lake", "env", "lean", "--run", str(TREE / "verification/AuditTargets.lean"), MODULE, TARGET],
        "comparator": ["lake", "env", str(COMPARATOR), str(CONFIG)],
        "selected-export": ["lake", "env", python, str(CAPTURE), "--output", str(folder / "selected-solution.ndjson"),
                            "--receipt", str(folder / "export-capture.json"), "--", str(EXPORTER), MODULE, "--", TARGET],
        "extra-nanoda": [python, str(NANODA_RECORDER), str(folder / "additional-nanoda-config.json")],
        "original-fresh": ["lake", "env", str(REAL / "bin/leanchecker"), "--fresh", MODULE],
    }
    return prefix + operations[name]


def phase_environment(name, folder, python):
    paths = [str(REAL / "bin"), str(Path(python).resolve().parent), "/usr/bin", "/bin", "/usr/sbin", "/sbin", "/opt/homebrew/bin"]
    env = {"PATH": os.pathsep.join(dict.fromkeys(paths)), "HOME": str(folder / "home"),
           "TMPDIR": str(folder / "tmp"), "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "ELAN_HOME": str(BASE / "elan"),
           "XDG_CACHE_HOME": str(BASE / "cache"), "MATHLIB_CACHE_DIR": str(BASE / "cache/mathlib"),
           "LEAN_SYSROOT": str(REAL), "LEAN_NUM_THREADS": "2", "LEAN_ABORT_ON_PANIC": "1",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0",
           "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1"}
    if name == "comparator":
        env.update(COMPARATOR_LANDRUN=str(SHIM), COMPARATOR_LEAN4EXPORT=str(EXPORTER))
    if name == "extra-nanoda":
        env.update(COMPARATOR_LANDRUN=str(SHIM), NANODA_REAL_BINARY=str(NANODA),
                   REPLICATION_CHECKER_RECORD_DIR=str(folder / "nanoda-records"))
    return env


def closed_phase(evidence, name, folder, content, fingerprint):
    folder = canonical(folder)
    require(folder.is_relative_to(RECORD_ROOT) and folder != RECORD_ROOT, "phase outside owned record root")
    result = evidence.json(folder / "phase-result.json", True)
    require(result.get("schema") == "openai-native-phase/1" and result.get("phase") == name
            and result.get("status") == "passed" and result.get("interrupt_signal") is None
            and result.get("record_directory") == str(folder)
            and result.get("input_fingerprint") == fingerprint, "phase not closed successful: " + name)
    prepared = evidence.json(folder / "phase-prepared.json", True)
    require(prepared["phase"] == name and prepared["record_directory"] == str(folder)
            and prepared["started_utc"] == result["started_utc"], "phase preparation binding differs")
    evidence.bind(result["phase_inputs"], folder / "phase-inputs.json", True)
    inputs = evidence.json(folder / "phase-inputs.json")
    require(inputs["phase"] == name and inputs["selected_inputs"] == content
            and inputs["input_fingerprint"] == fingerprint, "phase selected input binding differs")
    require(name == "extra-nanoda" or inputs["export_input"] is None, "unexpected phase export input")
    python = inputs["argv"][0]
    require(Path(python).is_absolute(), "phase Python path must be explicit")
    require(inputs["argv"] == phase_command(name, folder, python)
            and inputs["environment"] == phase_environment(name, folder, python)
            and inputs["environment_keys"] == sorted(inputs["environment"])
            and inputs["cwd"] == str(WORKSPACE) and inputs["timeout_seconds"] == LIMITS[name],
            "phase exact argv/environment differs: " + name)
    stage = folder / "stages" / name
    evidence.bind(result["stage_finished"], stage / "finished.json", True)
    finished = evidence.json(stage / "finished.json")
    start = evidence.json(stage / "prepared.json", True)
    raw = evidence.identity(stage / "raw.log", True)
    require(finished["schema"] == "eth-ci-stage/1" and finished["name"] == name
            and type(finished["exit_code"]) is int and finished["exit_code"] == 0
            and finished["reason"] is None and not finished.get("timed_out", False)
            and all(finished.get(k) == v for k, v in start.items())
            and finished["argv"] == inputs["argv"] and finished["cwd"] == str(WORKSPACE)
            and finished["timeout_seconds"] == LIMITS[name] and finished["stdout_is_export"] is False
            and finished["raw_log_sha256"] == raw["sha256"] and finished["raw_log_bytes"] == raw["size_bytes"]
            and result["stage_receipts"] == [finished], "stage receipt/output acceptance differs: " + name)
    number(finished["wall_seconds"]); number(finished["child_cpu_seconds"])
    begun = number(finished["started_utc_epoch"])
    require(utc(result["started_utc"]) <= begun + 1 and utc(result["finished_utc"]) + 1 >= begun + finished["wall_seconds"],
            "phase timing does not enclose child stage")
    return {"name": name, "directory": str(folder), "result": result, "inputs": inputs,
            "stage": finished, "raw_path": stage / "raw.log", "python": python,
            "start": begun, "end": begun + finished["wall_seconds"]}


def identity_phase(phase, expected):
    raw = json.loads(phase["raw_path"].read_text())
    require(raw == phase["result"]["identity_metadata"] and raw["schema"] == "openai-native-input-identity/1"
            and raw["all_pinned_input_checks_passed"] is True and raw["failures"] == []
            and raw["helper_sha256"] == "52cb3de32ef89c5fbb460032601693a9d2e740cda296b8dd44f9ab6fd1fa9174"
            and raw["expectations_sha256"] == "e39147fee63287baea89a046c85c462090f1c443f15b53d809e613631f0cce47"
            and raw["closure_source_files_checked_per_copy"] == 3092 and raw["workspace_lean_inventory_count"] == 3093
            and raw["expected_workspace_lean_inventory_count"] == 3093 and raw["workspace_config_files_checked"] == 2
            and raw["recorded_r2_library_globs_present"] is True
            and raw["selected_real_runtime_prefix"] == str(REAL), "identity inspection not complete")
    for row in [raw["upstream"], *raw["dependencies"]]:
        require(row["passed"] is True and row["actual_commit"] == row["expected_commit"]
                and row["tracked_changes_against_expected"] == [] and row["tracked_index_changes_against_expected"] == []
                and row["remote_matches_expected_https_repository"] is True, "Git identity not clean/pinned")
    require(raw["upstream"]["actual_commit"] == expected["source_commit"], "upstream identity differs")
    require({r["name"]: r["actual_commit"] for r in raw["dependencies"]}
            == {r["name"]: r["rev"] for r in expected["expected_dependencies"]}, "dependency identity set differs")
    require({r["path"]: r["expected_sha256"] for r in raw["runtime_files"]}
            == {r["path"]: r["sha256"] for r in expected["expected_runtime_files"]}
            and all(r["passed"] is True for r in raw["runtime_files"]), "selected runtime identity differs")
    return raw


def audit_phase(phase):
    rows = [json.loads(line) for line in phase["raw_path"].read_text().splitlines() if line.strip()]
    require(len(rows) == 3 and rows == phase["result"]["audit_events"], "audit event lineage incomplete")
    environment, target, complete = rows
    require(all(r["schema"] == "eth-target-axiom-audit/1" and r["module"] == MODULE for r in rows)
            and environment["event"] == "environment" and environment["initializer_execution_enabled"] is False
            and environment["load_extensions"] is False and environment["load_level"] == "private"
            and set(environment["permitted_axioms"]) == set(AXIOMS)
            and environment["standard_axiom_signature_check"] is True
            and target["event"] == "target" and target["target"] == TARGET and target["passed"] is True
            and target["disallowed_axioms"] == [] and set(target["axioms"]) <= set(AXIOMS)
            and type(target["visited_constants"]) is int and target["visited_constants"] > 0
            and complete["event"] == "complete" and complete["passed"] is True and complete["targets_checked"] == 1,
            "named-target transitive axiom audit failed/incomplete")
    return rows


def export_phase(evidence, phase):
    folder = Path(phase["directory"])
    result = phase["result"]
    evidence.bind(result["capture_receipt"], folder / "export-capture.json", True)
    capture = evidence.json(folder / "export-capture.json")
    export = evidence.identity(folder / "selected-solution.ndjson")
    require(capture["schema"] == "native-direct-fd-export/2" and capture["complete"] is True
            and type(capture["child_exit_code"]) is int and capture["child_exit_code"] == 0
            and capture["argv"] == [str(EXPORTER), MODULE, "--", TARGET]
            and capture["cwd"] == str(WORKSPACE) and capture["stdout_path"] == export["path"]
            and capture["export"] == export and result["export"] == export and export["size_bytes"] > 0,
            "selected export not complete/exact/hash-bound")
    return export


def nano_phase(evidence, phase, export, threads=2, *, binary, recorder):
    folder = Path(phase["directory"])
    expected = {"use_stdin": False, "export_file_path": export["path"], "permitted_axioms": AXIOMS,
                "unpermitted_axiom_hard_error": True, "num_threads": threads, "nat_extension": True, "string_extension": True}
    config_path = folder / "additional-nanoda-config.json"
    require(evidence.json(config_path, True) == expected and phase["inputs"]["export_input"] == export,
            "additional Nanoda input/policy differs")
    directories = sorted((folder / "nanoda-records").glob("nanoda-*"))
    require(len(directories) == 1, "Nanoda invocation count is not exactly one")
    record = canonical(directories[0])
    require(not (record / "99-error.json").exists(), "Nanoda recorder has an error receipt")
    zero = evidence.json(record / "00-prepared.json", True)
    one = evidence.json(record / "01-started.json", True)
    two = evidence.json(record / "02-finished.json", True)
    config = evidence.identity(config_path)
    effective = evidence.identity(record / "effective-config.json", True)
    require(evidence.json(record / "effective-config.json") == expected, "archived actual Nano policy differs")
    argv = [str(binary), str(config_path)]
    require(all(two.get(k) == value for k, value in zero.items())
            and one["checker_argv"] == two["checker_argv"] == argv and type(one["pid"]) is int and one["pid"] > 0
            and two["mode"] == "native_fake_landrun_unsandboxed" and two["cwd"] == str(WORKSPACE)
            and two["wrapper_argv"] == [str(recorder), str(config_path)]
            and two["recording_complete"] is True and two["inputs_unchanged"] is True
            and type(two["checker_exit_code"]) is int and two["checker_exit_code"] == 0
            and type(two["wrapper_exit_code"]) is int and two["wrapper_exit_code"] == 0
            and two["policy_changes_by_recorder"] is False and two["effective_policy"] == expected,
            "actual Nanoda prepared/start/finish lineage incomplete/failed")
    for before, after, actual in [(two["binary_before"], two["binary_after"], evidence.identity(binary)),
                                  (two["config_before"], two["config_after"], config),
                                  (two["export_before"], two["export_after"], export)]:
        require(all(before[k] == after[k] == actual[k] for k in ("path", "sha256", "size_bytes")),
                "actual Nano checked input changed/differs")
    evidence.bind(two["config_archive"], record / "effective-config.json")
    evidence.bind(two["shim"], SHIM)
    evidence.bind(two["wrapper_source"], recorder)
    require(effective["sha256"] == config["sha256"], "Nanoda effective config is not actual forwarded config bytes")
    archive = evidence.bind(two["export_archive"]["gzip"], record / "export.ndjson.gz")
    digest, size = hashlib.sha256(), 0
    with gzip.open(record / "export.ndjson.gz", "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block); size += len(block)
    require(digest.hexdigest() == two["export_archive"]["uncompressed_sha256"] == export["sha256"]
            and size == two["export_archive"]["uncompressed_size_bytes"] == export["size_bytes"],
            "actual checked archive does not reproduce selected payload bytes")
    saved = phase["result"]["nanoda"]
    evidence.bind(saved["finished_receipt"], record / "02-finished.json")
    require(saved["gzip"] == archive, "phase Nanoda gzip binding differs")
    require(saved["small_records"] == [evidence.identity(record / name) for name in
            ["00-prepared.json", "01-started.json", "02-finished.json", "effective-config.json"]],
            "Nanoda small-record bindings differ")
    number(two["checker_cpu_seconds"]); number(two["checker_wall_seconds"])
    require(utc(two["started_at"]) <= utc(one["started_at"]) <= utc(two["finished_at"])
            and phase["start"] - 1 <= utc(two["started_at"])
            and utc(two["finished_at"]) <= phase["end"] + 1,
            "Nanoda recording is not inside its enclosing phase interval")
    return {"record_directory": str(record), "finished_receipt": evidence.identity(record / "02-finished.json"),
            "effective_policy": expected, "checker_cpu_seconds_included_in_phase": two["checker_cpu_seconds"],
            "checker_wall_seconds": two["checker_wall_seconds"], "actual_export": export, "retained_gzip": archive}


def checkpoint_wrapper(evidence, path, session=None):
    wrapper = evidence.json(path, True)
    require(type(wrapper.get("final_exec_exit_code")) is int and wrapper["final_exec_exit_code"] == 0
            and type(wrapper.get("exec_session_id")) is int
            and (session is None or wrapper["exec_session_id"] == session), "outer exec did not close normally")
    record = wrapper["checkpoint_run_result"]
    require(type(record["exit_code"]) is int and record["exit_code"] == 0 and record["timed_out"] is False
            and record["agent"] == "codex-eth-replication" and record["task"] == "external-eth-proof-replication-20261104"
            and type(record["revision_event_id"]) is int and record["revision_event_id"] > 0,
            "checkpoint build/outer receipt failed or unrecognized")
    raw_path = canonical(PROJECT / record["log_path"])
    raw = evidence.identity(raw_path, True)
    require(raw["sha256"] == record["log_sha256"] and raw["size_bytes"] == record["log_size"],
            "outer checkpoint raw log not bound")
    number(record["cpu_seconds"]); number(record["wall_seconds"])
    return wrapper, record, raw_path


def source_clock(wrapper, started_utc, checkpoint_wall):
    begin = utc(started_utc)
    captured = utc(wrapper["captured_utc"])
    require(captured >= begin, "actual source closure capture predates source start")
    return {"source_header_started_utc": started_utc, "actual_terminal_capture_utc": wrapper["captured_utc"],
            "utc_start_to_capture_observation_seconds": captured - begin,
            "reported_checkpoint_monotonic_wall_seconds": number(checkpoint_wall),
            "utc_span_minus_reported_monotonic_seconds": captured - begin - checkpoint_wall,
            "scope": "Captured UTC is root's observation after actual terminal session output, not an exact child finish timestamp; observation/transport delay is possible. The UTC span/difference is not CPU or compute time. Checkpoint wall is the separately reported monotonic command measurement.",
            "start": begin, "end": captured}


def source_build(evidence, path):
    wrapper, record, raw_path = checkpoint_wrapper(evidence, path, 11317)
    require(raw_path == BASE / "logs/source-build-gated-r4.txt", "different build attempt supplied")
    text = raw_path.read_text()
    command = next(line[len("# command: "):] for line in text.splitlines() if line.startswith("# command: "))
    parts = shlex.split(command)
    require(len(parts) == 4 and Path(parts[0]).name.startswith("python3")
            and canonical(PROJECT / parts[1]) == BASE / "run_gated_build.py" and parts[2:] == ["--slots", "3"],
            "source build command differs from actual approved attempt")
    clock = source_clock(wrapper, next(line[len("# started_at: "):] for line in text.splitlines() if line.startswith("# started_at: ")), record["wall_seconds"])
    header, _ = json.JSONDecoder().raw_decode(text[text.index("\n{") + 1:])
    require(header["mode"] == "ordinary_lake_with_compiler_admission"
            and header["argv"] == [str(REAL / "bin/lake"), "build", "+" + MODULE, "+" + CHALLENGE]
            and header["cwd"] == str(WORKSPACE) and header["source_module_count"] == 3092
            and header["source_hashes_checked"] is True and header["compiler_frontend_slots"] == 3
            and header["lean_runtime_threads"] == 4, "source build header/contract differs")
    require(evidence.identity(BASE / "compiler-gate-r1/manifest.json")["sha256"] == header["gate_manifest_sha256"],
            "source compiler gate manifest changed")
    successes = re.findall(r"^Build completed successfully \((\d+) jobs\)\.$", text, re.MULTILINE)
    require(successes and int(successes[-1]) > 0, "closed source build lacks actual final Lake success line")
    return {"receipt": evidence.identity(path), "checkpoint": record, "raw": evidence.identity(raw_path),
            "header": header, "reported_lake_jobs": int(successes[-1]), "clock_scopes": clock, "start": clock["start"], "end": clock["end"]}


def mappings(values, required, names=PHASES):
    result = {}
    for value in values:
        name, path = value.split("=", 1)
        require(name in names and name not in result, "unknown/duplicate phase mapping")
        result[name] = canonical(path)
    require(not required or set(result) == set(names), "exact required explicit phase mappings missing")
    require(len(set(result.values())) == len(result), "phase evidence directories must be distinct")
    return result


ORIGINAL_PHASES = tuple(name for name in PHASES if name != "extra-nanoda")
RETRY_SOURCE = BASE / "nanoda_worker_stack_retry_r3.py"
RETRY_SHA = "9f4fe4e87a568f8bd89d39df61ed03fc155e120e2194aa82dce038918c1f34f3"


def retry_metadata(evidence):
    require(evidence.identity(RETRY_SOURCE)["sha256"] == RETRY_SHA, "reviewed retry helper changed")
    spec = importlib.util.spec_from_file_location("aggregation_reviewed_retry_metadata", RETRY_SOURCE)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    require(module.PROTOCOL == "openai-native-r2-nanoda-worker-stack256-cfenv-r3"
            and module.CF_KEY == "__CF_USER_TEXT_ENCODING"
            and module.CF_VALUE_SHA256 == "bfea86ae0b123713ac5b1af20b2dd4ead4f0bb81822ed654e80347e6fa420f3b",
            "explicit reviewed macOS metadata revision differs")
    return module


def closed_retry(e, helper, folder, content, fp, export, fresh, failure):
    folder = canonical(folder)
    require(folder.is_relative_to(helper.ROOT) and folder != helper.ROOT, "retry directory outside explicit variant root")
    result = e.json(folder / "retry-result.json", True)
    prepared = e.json(folder / "retry-prepared.json", True)
    require(result["schema"] == "openai-native-resource-retry/1" and result["protocol_variant"] == helper.PROTOCOL
            and result["logical_check"] == "extra-nanoda" and result["status"] == "passed"
            and result["original_r2_attempt_passed"] is False and result["interrupt_signal"] is None
            and result["record_directory"] == str(folder) and result["base_r2_input_fingerprint"] == fp
            and result["resource_policy"] == helper.RESOURCE_POLICY
            and prepared["started_utc"] == result["started_utc"] and prepared["protocol_variant"] == helper.PROTOCOL,
            "resource retry not explicitly closed under reviewed variant")
    e.bind(result["retry_inputs"], folder / "retry-inputs.json", True)
    inputs = e.json(folder / "retry-inputs.json")
    require(inputs["schema"] == "openai-native-resource-retry-inputs/1"
            and inputs["protocol_variant"] == helper.PROTOCOL and inputs["base_r2_input_fingerprint"] == fp
            and inputs["selected_inputs"] == content and inputs["export_input"] == export
            and inputs["resource_policy"] == helper.RESOURCE_POLICY
            and inputs["config_delta"] == {}
            and inputs["resource_inputs"] == helper.resource_inputs(e)
            and result["failed_attempt"] == inputs["failed_attempt"] == failure
            and inputs["fresh_directory"] == fresh["directory"], "resource retry provenance/policy differs")
    require(e.identity(folder / "additional-nanoda-config.json", True)["sha256"]
            == e.identity(Path(failure["directory"]) / "additional-nanoda-config.json")["sha256"],
            "resource retry config bytes differ from the actual original failed config")
    e.bind(inputs["fresh_phase_result"], Path(fresh["directory"]) / "phase-result.json")
    e.bind(inputs["retry_source"], RETRY_SOURCE)
    python = inputs["argv"][0]
    require(inputs["argv"] == [python, str(RETRY_SOURCE), "--child", str(folder)]
            and inputs["environment"] == helper.retry_environment(folder, python)
            and inputs["environment_keys"] == sorted(inputs["environment"])
            and inputs["cwd"] == str(WORKSPACE) and inputs["timeout_seconds"] == 7200,
            "retry exact child argv/environment differs")
    stage = folder / "stages" / helper.STAGE
    e.bind(result["stage_finished"], stage / "finished.json", True)
    finished = e.json(stage / "finished.json"); start = e.json(stage / "prepared.json", True)
    raw = e.identity(stage / "raw.log", True)
    require(type(finished["exit_code"]) is int and finished["exit_code"] == 0 and finished["reason"] is None
            and finished["name"] == helper.STAGE and finished["schema"] == "eth-ci-stage/1"
            and all(finished.get(k) == v for k, v in start.items())
            and finished["argv"] == inputs["argv"] and finished["cwd"] == str(WORKSPACE)
            and finished["timeout_seconds"] == 7200 and finished["stdout_is_export"] is False
            and finished["raw_log_sha256"] == raw["sha256"] and finished["raw_log_bytes"] == raw["size_bytes"]
            and result["stage_receipts"] == [finished], "retry stage did not close normally/hash-bound")
    number(finished["child_cpu_seconds"]); number(finished["wall_seconds"])
    begun = number(finished["started_utc_epoch"]); ended = begun + finished["wall_seconds"]
    require(fresh["end"] <= begun and failure["end"] <= fresh["start"]
            and utc(result["started_utc"]) <= begun and utc(result["finished_utc"]) + 1 >= ended,
            "fresh/failure/retry ordering differs")
    e.bind(result["worker_resource"], folder / "worker-resource.json", True)
    worker = e.json(folder / "worker-resource.json")
    require(worker["schema"] == "native-nanoda-worker-resource/2" and worker["protocol_variant"] == helper.PROTOCOL
            and worker["retry_source"] == inputs["retry_source"] and worker["environment"] == inputs["environment"]
            and worker["environment_keys"] == inputs["environment_keys"] and worker["cwd"] == str(WORKSPACE)
            and worker["exec_argv"] == [python, str(helper.RESOURCE_RECORDER), str(folder / "additional-nanoda-config.json")]
            and worker["resource_inputs"] == inputs["resource_inputs"] and worker["resource_policy"] == helper.RESOURCE_POLICY
            and type(worker["main_stack_limits_before"]) is list and len(worker["main_stack_limits_before"]) == 2
            and all(type(v) is int for v in worker["main_stack_limits_before"])
            and worker["main_stack_limits_before"] == worker["main_stack_limits_after"]
            and worker["main_stack_limits_changed"] is False and worker["actual_nanoda_worker_extent_measured"] is False
            and type(worker["pid"]) is int and worker["pid"] == worker["pgid"]
            and begun - 1 <= utc(worker["observed_utc"]) <= ended + 1, "actual worker-resource exec event differs")
    events = [json.loads(line[len("WORKER_RESOURCE "):]) for line in (stage / "raw.log").read_text().splitlines()
              if line.startswith("WORKER_RESOURCE ")]
    require(events == [worker], "retry raw worker-resource event differs from saved record")
    summary = helper.nano_records(e, folder, export, 2, 0)
    require(result["nanoda"] == summary and Path(summary["record_directory"]).name.startswith("nanoda-" + str(worker["pid"]) + "-"),
            "actual checker does not follow recorded resource-exec process")
    return {"name": "extra-nanoda", "directory": str(folder), "result": dict(result, nanoda=summary),
            "inputs": inputs, "stage": finished, "raw_path": stage / "raw.log", "python": python,
            "start": begun, "end": ended, "worker_resource": worker}


def preexec_environment_failure(e, helper, content, fp, export, fresh):
    """Retain the actual closed resource-R2 guard failure; no Nano ran in it."""
    folder = BASE / "native-retry-records/worker-stack256-r2-01"
    result = e.json(folder / "retry-result.json", True)
    inputs = e.json(folder / "retry-inputs.json", True)
    prepared = e.json(folder / "retry-prepared.json", True)
    old_source = BASE / "nanoda_worker_stack_retry_r2.py"
    require(e.identity(old_source, True)["sha256"] == "59931d7b0d00ba5651322e6a3e1efb9524223334ce74ee767891dd95534557fc"
            and e.identity(folder / "retry-result.json")["sha256"] == "d6b716803c4d9d36b02052bcd04b7cc40d38195973939c59ec2b25f628db627d",
            "actual preserved resource-R2 source/result differs")
    e.bind(inputs["retry_source"], old_source)
    require(result["schema"] == "openai-native-resource-retry/1" and result["status"] == "failed"
            and result["protocol_variant"] == inputs["protocol_variant"] == "openai-native-r2-nanoda-worker-stack256-r2"
            and result["original_r2_attempt_passed"] is False and result["interrupt_signal"] is None
            and result["record_directory"] == str(folder) and result["resource_policy"] == helper.RESOURCE_POLICY
            and inputs["resource_policy"] == helper.RESOURCE_POLICY
            and inputs["base_r2_input_fingerprint"] == fp and inputs["selected_inputs"] == content
            and inputs["export_input"] == export and inputs["config_delta"] == {}
            and inputs["resource_inputs"] == helper.resource_inputs(e)
            and inputs["fresh_directory"] == fresh["directory"]
            and prepared["started_utc"] == result["started_utc"], "actual preexec failure lineage differs")
    e.bind(inputs["fresh_phase_result"], Path(fresh["directory"]) / "phase-result.json")
    config = folder / "additional-nanoda-config.json"
    require(helper.strict_policy_matches(e.json(config, True), export, 2), "failed preexec strict config differs")
    python = inputs["argv"][0]
    argv = [python, str(old_source), "--child", str(folder)]
    env = phase_environment("extra-nanoda", folder, python)
    env["NANODA_REAL_BINARY"] = str(helper.RESOURCE_BINARY)
    require(inputs["argv"] == argv and inputs["environment"] == env
            and inputs["environment_keys"] == sorted(env) and helper.CF_KEY not in env
            and inputs["cwd"] == str(WORKSPACE) and inputs["timeout_seconds"] == 7200,
            "original preexec declared argv/environment differs")
    stage = folder / "stages" / helper.STAGE
    finished = e.json(stage / "finished.json", True); start = e.json(stage / "prepared.json", True)
    raw = e.identity(stage / "raw.log", True)
    require(type(finished["exit_code"]) is int and finished["exit_code"] == 1 and finished["reason"] is None
            and finished["schema"] == "eth-ci-stage/1" and finished["name"] == helper.STAGE
            and all(finished.get(k) == v for k,v in start.items()) and finished["argv"] == argv
            and finished["cwd"] == str(WORKSPACE) and finished["timeout_seconds"] == 7200
            and result["stage_receipts"] == [finished]
            and raw["sha256"] == finished["raw_log_sha256"] == "f384b5c2c40e0e661b81aa604ae8672a24e6613b536aecba804ea25821090503"
            and raw["size_bytes"] == finished["raw_log_bytes"] == 848,
            "closed preexec guard failure stage/raw differs")
    text = (stage / "raw.log").read_text()
    require("child resource protocol/environment differs" in text and "WORKER_RESOURCE " not in text
            and not (folder / "worker-resource.json").exists()
            and not list((folder / "nanoda-records").glob("nanoda-*")),
            "preexec failure unexpectedly reached checker launch evidence")
    outer_path = BASE / "logs/native-worker-stack256-r2-checkpoint.json"
    outer = e.json(outer_path, True); outer_raw = PROJECT / outer["log_path"]
    raw_outer = e.identity(outer_raw, True)
    require(outer["agent"] == "codex-eth-replication" and outer["task"] == "external-eth-proof-replication-20261104"
            and outer["revision_event_id"] == 4044 and outer["exit_code"] == 1 and outer["timed_out"] is False
            and raw_outer["sha256"] == outer["log_sha256"] == "694e0b7dc13d25a56f1d66996bae5d5820cc42704d3c71705549f6401f3ec72e"
            and raw_outer["size_bytes"] == outer["log_size"], "actual preexec outer DIGEST differs")
    last = next((line for line in reversed(outer_raw.read_text().splitlines()) if line.startswith('{"')), None)
    require(last is not None and json.loads(last) == result, "preexec outer final result differs")
    begun = number(finished["started_utc_epoch"]); ended = begun + number(finished["wall_seconds"])
    number(finished["child_cpu_seconds"]); number(outer["cpu_seconds"]); number(outer["wall_seconds"])
    require(fresh["end"] <= begun and utc(result["started_utc"]) <= begun
            and ended <= utc(result["finished_utc"]) + 1, "preexec failure chronology differs")
    return {"name":"preexec-environment-failure", "directory":str(folder),
            "verdict":"FAILED before Nano launch: exact environment guard rejected SDK-added metadata; not a checker result",
            "result":e.identity(folder / "retry-result.json"), "inputs":e.identity(folder / "retry-inputs.json"),
            "stage":finished, "raw":raw, "outer_receipt":e.identity(outer_path), "outer_digest":outer,
            "start":begun, "end":ended, "nano_launched":False}


def aggregate(evidence, folders, build_path, outer_paths, scheduling_paths, failed_folder, failed_outer, retry_folder):
    content, fp, expected = pinned_inputs(evidence)
    helper = retry_metadata(evidence)
    require(fp == helper.BASE_FP, "revised protocol requires exact common original R2 inputs")
    build = source_build(evidence, build_path)
    phases = {n: closed_phase(evidence, n, folders[n], content, fp) for n in ORIGINAL_PHASES}
    identities = {n: identity_phase(phases[n], expected) for n in ["pre-identity", "post-identity"]}
    audit = audit_phase(phases["audit"])
    lines = phases["comparator"]["raw_path"].read_bytes().splitlines()
    require(b"Your solution is okay!" in lines and b"Lean default kernel accepts the solution" in lines,
            "original Comparator exact acceptance lines missing")
    export = export_phase(evidence, phases["selected-export"])
    failure = helper.failed_attempt(evidence, failed_folder, failed_outer, content, export)
    preexec = preexec_environment_failure(evidence, helper, content, fp, export, phases["original-fresh"])
    phases["extra-nanoda"] = closed_retry(evidence, helper, retry_folder, content, fp, export, phases["original-fresh"], failure)
    require(preexec["end"] <= phases["extra-nanoda"]["start"], "revised environment retry must follow retained preexec failure")
    nano = nano_phase(evidence, phases["extra-nanoda"], export, threads=2,
                      binary=helper.RESOURCE_BINARY, recorder=helper.RESOURCE_RECORDER)
    require(len({p["python"] for p in phases.values()}) == 1, "interpreter path differs across revised campaign")
    ordered = sorted(list(phases.values()) + [failure, preexec], key=lambda p: p["start"])
    require(ordered[0]["name"] == "pre-identity" and ordered[1]["name"] == "trace"
            and ordered[-1]["name"] == "post-identity" and build["end"] <= ordered[0]["start"] + 1
            and all(a["end"] <= z["start"] + 1 for a,z in zip(ordered, ordered[1:])), "mixed campaign order/overlap invalid")
    require(phases["selected-export"]["end"] <= failure["start"] and phases["extra-nanoda"]["end"] <= phases["post-identity"]["start"],
            "export/failure/retry/postidentity order invalid")
    scheduling = [BASE / "logs" / n for n in ["temporary-suspension-r1.json", "temporary-resumption-r1.json",
                  "memory-pressure-suspension-r2.json", "memory-pressure-resumption-r3.json", "memory-pressure-resumption-r4.json"]]
    scheduling_hashes = {"temporary-suspension-r1.json": "73584dc6355248c7899afe15e527281af1a0ac5641071d78ff321a655b2341ef", "temporary-resumption-r1.json": "7765cec437c7dd350ff481edf35dd76d4df8e87f04b223240860bda90c12689f", "memory-pressure-suspension-r2.json": "34d3b7d059439eea0b9d5a41df8470fad59b22b524403b62b1ea58e1a018ca95", "memory-pressure-resumption-r3.json": "de271acadc3b41a6556f614aafcd9595bf7f9ff762821b72ddc9947c88b095db", "memory-pressure-resumption-r4.json": "810e07a6d0b5c63f77ec064f91f998f4ab5b0fee948d72b8f210670a2451f9d5"}
    require(all(evidence.identity(p)["sha256"] == scheduling_hashes[p.name] for p in scheduling), "recorded manual scheduling evidence changed")
    build["scheduling_receipts"] = [evidence.identity(p, True) for p in dict.fromkeys(scheduling + list(scheduling_paths))]
    outer = {}
    if outer_paths:
        require(set(outer_paths) == set(ORIGINAL_PHASES), "optional outer wrappers require exactly seven original successful phases")
        for name,path in outer_paths.items():
            _,record,raw = checkpoint_wrapper(evidence,path)
            final = next((line for line in reversed(raw.read_text().splitlines()) if line.startswith('{"')),None)
            require(final is not None and json.loads(final)==phases[name]["result"], "outer successful phase result differs")
            outer[name] = {"receipt":evidence.identity(path),"checkpoint":record}
    evidence.stable()
    successful_cpu = sum(p["stage"]["child_cpu_seconds"] for p in phases.values())
    successful_wall = sum(p["stage"]["wall_seconds"] for p in phases.values())
    failed_cpu = number(failure["stage"]["child_cpu_seconds"]); failed_wall = number(failure["stage"]["wall_seconds"])
    return {"format":"openai-eth-native-replication-result-v2","protocol_variant":helper.PROTOCOL,
            "observed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "verdict":"PASS under explicitly revised worker-stack256 Nanoda resource-build protocol; original R2 Nanoda attempt remains FAILED",
            "all_required_native_checks_passed":True,"original_r2_protocol_passed":False,"verbatim_upstream_linux_ci_reproduction":False,
            "source":{"repository":"https://github.com/openai/math.git","commit":expected["source_commit"],"mathlib_commit":"d13f23b723b8a846827a245b89c10fc7d3f11612","lean_version":"4.34.1","lean_commit":"5045d0056413266e57c625dcd7c365b10e377c52","closure_module_copies":3092},
            "targets":[{"name":TARGET,"module":MODULE,"challenge":CHALLENGE}],"selected_input_fingerprint":fp,"selected_inputs":content,
            "source_build":build,"identity_pre_post":identities,"axiom_audit":audit,
            "comparator":{"commit":"865edc14486c3388e9225daa971da8e157488c3e","driver_compiler":"4.35.0","builtin_kernel":"Lean.kernelEnv.replay in the4.35-linked Comparator; not the separate original4.34.1 fresh checker","proof_export_sdk":"4.34.1","original_config_nanoda":False,"config":evidence.identity(CONFIG),"required_lines":["Lean default kernel accepts the solution","Your solution is okay!"]},
            "resource_tool_preparation":{"build":evidence.json(helper.TOOLS/"build-result-r1.json"),"probe":evidence.json(helper.TOOLS/"worker-probe-result-r1.json"),"tiny_controls":evidence.json(helper.TOOLS/"tiny-controls-r1/control-result-r1.json"),"scope":"Separate resource-tool preparation; CPU/wall not included in principal proof phase totals because timing may overlap originalfresh."},
            "additional_nanoda":dict(nano,source_commit="68d5ca9db226849b41a6fff59d796ff19d0a8840",exporter_source_commit="076e8e57707e813375e8f9da8bf989799ace9680",resource_policy=helper.RESOURCE_POLICY,actual_worker_resource_event=phases["extra-nanoda"]["worker_resource"],resource_build_inputs=helper.resource_inputs(evidence)),
            "retained_original_nanoda_failure":failure,"retained_resource_preexec_environment_failure":preexec,
            "platform_metadata_revision":{"key":helper.CF_KEY,"value_sha256":helper.CF_VALUE_SHA256,"guard":"Exact constructed and actual child environment equality retained; only pinned SDK-added key is explicitly included.","public_value":"Redact actual CF value in public data copies; retain key and SHA."},"retry_source":evidence.identity(RETRY_SOURCE),
            "original_fresh":{"module":MODULE,"original_version":"4.34.1","scope":"Original same-Lean-implementation safe/nonpartial imported-environment replay; axioms admitted, constructors/recursors postchecked. Separate from Comparator4.35 internal replay and RustNanoda independent implementation."},
            "phases":[{"name":n,"protocol":"explicit-resource-retry" if n=="extra-nanoda" else "original-r2","directory":phases[n]["directory"],"result":evidence.identity(Path(phases[n]["directory"])/("retry-result.json" if n=="extra-nanoda" else "phase-result.json")),"stage":phases[n]["stage"]} for n in PHASES],
            "resource_use":{"successful_logical_phase_child_cpu_seconds":successful_cpu,"successful_logical_phase_wall_seconds_summed":successful_wall,"retained_failed_phase_child_cpu_seconds":failed_cpu,"retained_failed_phase_wall_seconds":failed_wall,"source_build_checkpoint_cpu_seconds":build["checkpoint"]["cpu_seconds"],"source_build_checkpoint_wall_seconds":build["checkpoint"]["wall_seconds"],"principal_nonoverlapping_child_cpu_seconds":build["checkpoint"]["cpu_seconds"]+successful_cpu+failed_cpu+preexec["stage"]["child_cpu_seconds"],"principal_nonoverlapping_wall_seconds_summed":build["checkpoint"]["wall_seconds"]+successful_wall+failed_wall+preexec["stage"]["wall_seconds"],"preexec_environment_failure_stage_child_cpu_seconds":preexec["stage"]["child_cpu_seconds"],"preexec_environment_failure_stage_wall_seconds":preexec["stage"]["wall_seconds"],"preexec_environment_failure_outer_checkpoint_cpu_seconds":preexec["outer_digest"]["cpu_seconds"],"preexec_environment_failure_outer_checkpoint_wall_seconds":preexec["outer_digest"]["wall_seconds"],"failed_outer_digest_includes_failed_inner":True,"successful_outer_wrappers":outer,"nested_nanoda_cpu_already_included":True,"paid_cloud_spend_usd":0,"scope":"Source+seven original successful stages+newworkerstackretry+retained failed original stage+retained preexec-environment failure stage. Resource-tool build/probe/control costs are separately recorded and may overlap originalfresh; they are excluded from these principal nonoverlapping stage sums. Nestedchecker and outerwrappers not added again. UTCgap separate from source monotonicwall; sharedhost/manualpauses, no isolated performance/RSS or actualNanoda worker stackextent measurement."},
            "claim_limits":["Original two-thread Nanoda attempt failed with SIGABRT worker stack overflow, not a logical rejection; it is not relabeled as passed.","New Nanoda resource binary is derived from exact68d5 source with ONLY STACK_SIZE16MiBto256MiB. Original strict2threads, payload, per-declaration logic and axiom policy remain unchanged. Compiled requested stack and harmless OS probe do not measure stack extent in actual Nano workers. Two recorded preexec mainstack-limit snapshots are unchanged; no mainstack limit is modified by this helper. Unsupported serial/mainstack proposal was never executed on ETH and remains preserved.","Native fake Landrun supplies no OS isolation; no verbatim Linux CI reproduction.","Comparator builtin Lean4.35 replay and original Lean4.34.1 fresh replay share the Lean implementation; RustNanoda is the independent checker implementation.","Exact formal target replication only; computational-model interpretation, practical SAT performance and SHA256d advantage are separate.","Trusted dependency caches were used; no binary rederivation or missing archive provenance is invented.","Large export and both actual checked gzip archives remain local; public artifacts contain metadata/hashes only.","Launcher constructs minimal environment; workspace helper prepends/resets selected paths rather than generally sanitizing inherited variables."],
            "artifacts":list(evidence.rows.values()),"public_small_artifacts":[evidence.rows[p] for p in sorted(evidence.public)]}

def write_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--failed-nanoda-phase", type=Path, required=True)
    parser.add_argument("--failed-outer-receipt", type=Path, required=True)
    parser.add_argument("--nanoda-retry", type=Path, required=True)
    parser.add_argument("--phase", action="append", default=[], metavar="NAME=DIRECTORY")
    parser.add_argument("--outer-receipt", action="append", default=[], metavar="NAME=FILE")
    parser.add_argument("--scheduling-receipt", action="append", default=[], type=Path,
                        help="additional actual later source pause/resumption receipt, never a guessed path")
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    output = canonical(args.output_directory)
    require(output.is_relative_to(OUTPUT_ROOT) and output != OUTPUT_ROOT, "choose a new owned aggregate output directory")
    output.mkdir(parents=True, exist_ok=False)
    evidence = Evidence()
    started, cpu = time.monotonic(), time.process_time()
    write_json(output / "aggregation-prepared.json", {"schema": "openai-native-aggregation/1", "status": "incomplete",
               "argv": sys.argv, "aggregator": evidence.identity(Path(__file__)), "proof_execution": False})
    try:
        folders = mappings(args.phase, True, ORIGINAL_PHASES)
        outer = mappings(args.outer_receipt, False, ORIGINAL_PHASES)
        result = aggregate(evidence, folders, canonical(args.build_receipt), outer,
                           [canonical(path) for path in args.scheduling_receipt],
                           canonical(args.failed_nanoda_phase), canonical(args.failed_outer_receipt), canonical(args.nanoda_retry))
        result["aggregation_resources"] = {"own_cpu_seconds": time.process_time() - cpu,
                                            "wall_seconds": time.monotonic() - started, "scope": "Read/hash/decompression/aggregation only; no proof execution."}
        write_json(output / "native-replication-result.json", result)
        write_json(output / "native-replication-artifacts.json", {"artifacts": result["artifacts"],
                   "public_small_artifacts": result["public_small_artifacts"], "large_exports_publication": "Hashes only; no export copies made."})
        text = ("# Native OpenAI revised-resource replication\n\nSeven original R2 checks and the explicitly revised worker-stack256 Nanoda resource-build retry closed successfully. The original two-thread Nanoda attempt failed with SIGABRT worker stack overflow and remains retained with its hashes/resources. A separate resource-R2 attempt failed before Nano launch when the exact environment guard observed SDK-added metadata; this failed attempt and costs also remain preserved. Resource-R3 explicitly pins that sole CF metadata value by SHA and retains exact full environment equality. A separately hashed binary changes only the compiled requested worker-stack constant16MiB to256MiB from pinned68d5. Original strict two-thread policy and payload remain unchanged; no main-stack limit or checker logic patch. Actual Nano worker stack extent is unmeasured. Unsupported main-stack proposals remain preserved and were never run on ETH.\n\nComparator internal replay uses linked Lean4.35, separate from original4.34.1 fresh replay; RustNanoda is the independent implementation. Native fake Landrun provides no OS isolation. Exact receipts, clocks, failed and successful archive hashes, resource scopes and limitations are in the companion JSON. Large exports remain local; no practical SAT/mining result inferred.\n")
        with (output / "report.md").open("x") as stream:
            stream.write(text); stream.flush(); os.fsync(stream.fileno())
        write_json(output / "aggregation-finished.json", {"schema": "openai-native-aggregation/1", "status": "passed",
                   "result": evidence.identity(output / "native-replication-result.json")})
        print(json.dumps({"status": "passed", "result": evidence.identity(output / "native-replication-result.json")}))
        return 0
    except Exception as error:
        write_json(output / "aggregation-finished.json", {"schema": "openai-native-aggregation/1", "status": "failed",
                   "error": type(error).__name__ + ": " + str(error), "proof_execution": False})
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
