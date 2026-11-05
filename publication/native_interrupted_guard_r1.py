"""Publication metadata gate for the separately sealed interrupted Rust attempt.

Never calls positive or terminal-nonzero admission. A recovered log fragment and
empty capture are observations, not invented completed stages/checker results.
Root supplies a map only after recovery, post-identity and combined saved review.
"""
import json
from pathlib import Path
import re
import types

HELPERS = "publication/native_incomplete_guard_r1.py"
HELPERS_SHA = "3c3d8696d58d90bead5a85da288b946d5c7bc995a6ede983f5c1fafd07706319"
CLOSURE_SOURCE = "openai/aggregate_native_interrupted_r1.py"
CLOSURE_SHA = "3893f6fd2ce5eca22fd99f57994bd25891367b729e31587f0d1a13e0ca9e243f"
DIRECTORY = "openai/native-interrupted-records/worker-stack256-r1-01"
SCHEMA = "openai-native-interrupted-result/1"
VERDICT = "ORIGINAL_LEAN_SUITE_PASS_ADDITIONAL_NANODA_INTERRUPTED"
MODE = "original-lean-pass-additional-nanoda-interrupted"
RECOVERY = "openai/logs/interruption-recovery-observation-r1.json"
RECOVERY_SHA = "89be8382a7c68dc549f31799154532a58819aba47c1b2b9e5dcfa7b6c70e6939"
OUTER_EMPTY = "openai/logs/native-worker-stack256-cf-r3-checkpoint.json"
OUTER_RAW = "openai/logs/native-worker-stack256-cf-r3-checkpoint.txt"
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
RESULT_SHA = "e0662f9de6c8699328549233d19c9438c1029951ac0ab3c55361824c78d848b0"
NANO = "openai/native-retry-records/worker-stack256-r3-02/nanoda-records/nanoda-38848-vymihcgo"
OUTPUTS = {"closure-prepared.json", "native-interrupted-result.json", "native-interrupted-artifacts.json", "report.md", "closure-finished.json"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def helper_modules(base, publisher):
    source = publisher.read_stable(Path(base), HELPERS)
    require(publisher.sha(source) == HELPERS_SHA, "frozen incomplete metadata helpers changed")
    helper = types.ModuleType("interrupted_pinned_metadata_helpers")
    exec(compile(source, str(Path(base) / HELPERS), "exec"), helper.__dict__)
    return helper, helper.metadata(base, publisher)


def recovered_facts(g, m):
    require(g.p.sha(g.read(RECOVERY)) == RECOVERY_SHA, "fixed recovery observation changed")
    recovery = g.obj(RECOVERY)
    require(recovery.get("schema") == "eth-proof-interruption-recovery/1"
            and m.integer(recovery.get("known_checker_pid"), 38877)
            and m.integer(recovery.get("known_recorder_pid"), 38848) and m.integer(recovery.get("known_pgid"), 38848)
            and recovery.get("process_observation", {}).get("matching_known_pid_or_group_rows") == []
            and m.integer(recovery.get("process_observation", {}).get("exit_code"), 0)
            and recovery.get("checker_exit_code") is None and recovery.get("independent_nanoda_accepted") is None
            and recovery.get("independent_nanoda_acceptance_observed") is False
            and recovery.get("final_child_cpu_seconds") is None and recovery.get("timeout_observed") is False,
            "recovery record asserts an execution result or different process observation")
    sd = m.RETRY + "/stages/worker-stack256-nanoda"
    missing = {sd + "/finished.json", NANO + "/02-finished.json", NANO + "/99-error.json"}
    existing = {OUTER_EMPTY, OUTER_RAW, m.RETRY + "/retry-result.json", m.RETRY + "/retry-prepared.json",
                m.RETRY + "/retry-inputs.json", m.RETRY + "/worker-resource.json", sd + "/prepared.json", sd + "/raw.log",
                NANO + "/00-prepared.json", NANO + "/01-started.json"}
    rows = recovery.get("artifacts", [])
    require(len(rows) == 13 and {r.get("path") for r in rows} == missing | existing, "exact recovery artifact set differs")
    for row in rows:
        name = row["path"]
        if name in missing:
            require(row.get("exists") is False and not (g.base / name).exists() and not (g.base / name).is_symlink(), "a missing closing artifact appeared")
        else:
            require(row.get("exists") is True, "recovery existing artifact changed")
            # The zero-byte JSON capture is deliberately NOT a JSON document or
            # selected file: the core publisher parses selected .json documents.
            raw = g.p.read_stable(g.base, name) if name == OUTER_EMPTY else g.read(name, "recovered_log" if name.endswith((".txt", "raw.log")) else "manifest")
            require(row.get("sha256") == g.p.sha(raw) and m.integer(row.get("size_bytes"), len(raw)), "recovered bytes changed: " + name)
            if name == OUTER_EMPTY:
                require(raw == b"" and row["sha256"] == EMPTY_SHA, "outer empty capture was replaced")
    attempted = g.obj(m.RETRY + "/retry-result.json", "completed_receipt")
    require(g.p.sha(g.read(m.RETRY + "/retry-result.json", "completed_receipt")) == RESULT_SHA
            and attempted.get("schema") == "openai-native-resource-retry/1" and attempted.get("status") == "failed"
            and attempted.get("protocol_variant") == m.PROTOCOL and attempted.get("logical_check") == "extra-nanoda"
            and attempted.get("original_r2_attempt_passed") is False and m.integer(attempted.get("interrupt_signal"), 15)
            and attempted.get("stage_receipts") == [] and attempted.get("resource_policy") == m.POLICY
            and "PermissionError" in attempted.get("error", "") and "[Errno 1]" in attempted.get("error", "")
            and g.p.closed_times(attempted.get("started_utc"), attempted.get("finished_utc")), "actual interruption result differs")
    interrupted_logs = {}
    for name in (OUTER_RAW, sd + "/raw.log"):
        raw = g.read(name, "recovered_log")
        interrupted_logs[name] = {"observation": RECOVERY, "exit_code": None, "timed_out": False,
                                  "final_child_cpu_seconds": None, "final_wall_seconds": None,
                                  "raw_log_sha256": g.p.sha(raw), "raw_log_bytes": len(raw),
                                  "scope": "Stable recovery-observed log fragment; no completed stage, checker exit, final CPU or outer DIGEST inferred"}
    return recovery, attempted, sorted(missing), interrupted_logs


def launched_inputs(g, m, result):
    folder = m.RETRY
    inputs, worker = g.obj(folder + "/retry-inputs.json"), g.obj(folder + "/worker-resource.json")
    export_phase = g.obj("openai/native-phase-records/r2-05-selected-export/phase-result.json")
    export = export_phase["export"]
    g.reference(export, m.EXPORT_NAME, m.EXPORT_SHA, m.EXPORT_SIZE)
    require(inputs.get("schema") == "openai-native-resource-retry-inputs/1" and inputs.get("protocol_variant") == m.PROTOCOL
            and inputs.get("base_r2_input_fingerprint") == m.FP and inputs.get("selected_inputs") == result["source_and_tool_inputs"]
            and inputs.get("export_input") == export and inputs.get("config_delta") == {} and inputs.get("resource_policy") == m.POLICY
            and result.get("resource_profile_inputs") == inputs.get("resource_inputs"), "interrupted input lineage differs")
    g.bind(inputs["retry_source"], m.HELPER, "source")
    require(inputs["retry_source"]["sha256"] == m.HELPER_SHA, "frozen R3 source differs")
    require(set(inputs["resource_inputs"]) == set(m.PINS) | {"target/release/nanoda_bin"}, "resource input set differs")
    for short, digest in {**m.PINS, "target/release/nanoda_bin": m.BINARY_SHA}.items():
        g.reference(inputs["resource_inputs"][short], m.TOOLS + "/" + short, digest)
    env = inputs["environment"]; python = inputs["argv"][0]
    require(worker.get("schema") == "native-nanoda-worker-resource/2" and worker.get("protocol_variant") == m.PROTOCOL
            and worker.get("resource_policy") == m.POLICY and worker.get("resource_inputs") == inputs["resource_inputs"]
            and worker.get("retry_source") == inputs["retry_source"] and worker.get("environment") == env
            and worker.get("environment_keys") == inputs.get("environment_keys") == sorted(env)
            and g.p.sha(env.get(m.CF_KEY, "").encode()) == m.CF_SHA and env.get("NANODA_REAL_BINARY") == g.path(m.BINARY)
            and inputs["argv"] == [python, g.path(m.HELPER), "--child", g.path(folder)]
            and worker.get("exec_argv") == [python, g.path(m.TOOLS + "/record_nanoda.py"), g.path(folder + "/additional-nanoda-config.json")]
            and inputs.get("cwd") == worker.get("cwd") == g.path("openai/workspace")
            and m.integer(inputs.get("timeout_seconds"), 7200) and m.integer(worker.get("pid"), 38848) and m.integer(worker.get("pgid"), 38848)
            and worker.get("main_stack_limits_before") == worker.get("main_stack_limits_after")
            and worker.get("main_stack_limits_changed") is False and worker.get("actual_nanoda_worker_extent_measured") is False,
            "actual launched resource/environment event differs")
    sd = folder + "/stages/worker-stack256-nanoda"
    stage = g.obj(sd + "/prepared.json")
    require(stage.get("schema") == "eth-ci-stage/1" and stage.get("name") == "worker-stack256-nanoda"
            and stage.get("argv") == inputs["argv"] and stage.get("cwd") == inputs["cwd"]
            and m.integer(stage.get("timeout_seconds"), 7200) and stage.get("stdout_is_export") is False,
            "prepared stage differs; no stage completion is admitted")
    raw = g.read(sd + "/raw.log", "recovered_log")
    require([json.loads(line[len(b"WORKER_RESOURCE "):]) for line in raw.splitlines() if line.startswith(b"WORKER_RESOURCE ")] == [worker],
            "recovered worker event differs")
    zero, one = g.obj(NANO + "/00-prepared.json"), g.obj(NANO + "/01-started.json")
    wanted = m.config(g, folder, export)
    require(zero.get("effective_policy") == wanted and zero.get("policy_changes_by_recorder") is False
            and zero.get("mode") == "native_fake_landrun_unsandboxed" and zero.get("cwd") == g.path("openai/workspace")
            and zero.get("wrapper_argv") == [g.path(m.TOOLS + "/record_nanoda.py"), g.path(folder + "/additional-nanoda-config.json")]
            and zero.get("checker_argv") == one.get("checker_argv") == [g.path(m.BINARY), g.path(folder + "/additional-nanoda-config.json")]
            and m.integer(one.get("pid"), 38877) and m.same_identity(zero.get("export_before", {}), export),
            "actual checker launch/payload/policy differs")
    g.reference(zero["binary_before"], m.BINARY, m.BINARY_SHA, 1260088)
    g.reference(zero["wrapper_source"], m.TOOLS + "/record_nanoda.py", m.RECORDER_SHA, 8494)
    g.bind(zero["config_before"], folder + "/additional-nanoda-config.json")
    g.bind(zero["config_archive"], NANO + "/effective-config.json")
    require(g.obj(NANO + "/effective-config.json") == wanted
            and g.read(NANO + "/effective-config.json") == g.read(folder + "/additional-nanoda-config.json"), "prepared effective config differs")
    archive = zero["export_archive"]
    require(archive.get("uncompressed_sha256") == export["sha256"] and m.integer(archive.get("uncompressed_size_bytes"), export["size_bytes"]),
            "prepared archive payload identity differs")
    g.reference(archive["gzip"], NANO + "/export.ndjson.gz")
    return {"receipt": NANO + "/00-prepared.json", "archive_role": "prepared_for_interrupted_attempt",
            "recording_complete": False, "checker_exit_code": None, "recorded_checker_accepted": False,
            "independent_nanoda_accepted": None, "acceptance_observed": False, "final_child_cpu_seconds": None,
            "inputs_unchanged_during_check": None, "timeout_observed": False,
            "raw_sha256": export["sha256"], "raw_size_bytes": export["size_bytes"],
            "gzip_sha256": archive["gzip"]["sha256"], "gzip_size_bytes": archive["gzip"]["size_bytes"],
            "availability": "Prepared attempt archive retained locally, not published or accepted",
            "identity_source": "Closed interrupted result and prepared/recovery metadata; no large-asset rehash by packager"}


def interrupted_summary(g, h, m, result):
    recovery, attempted, missing, logs = recovered_facts(g, m)
    summary = result["additional_interrupted_attempt"]
    null_fields = {"checker_exit_code", "independent_nanoda_accepted", "inputs_unchanged_during_check", "final_child_cpu_seconds", "final_wall_seconds"}
    require(summary.get("name") == "interrupted-additional-nanoda" and summary.get("directory") == g.path(m.RETRY)
            and summary.get("classification") == "INTERRUPTED_SIGNAL_15_NO_TERMINAL_CHECKER_RECORD"
            and m.integer(summary.get("interrupt_signal"), 15) and summary.get("acceptance_observed") is False
            and summary.get("recording_complete") is False and summary.get("timeout_observed") is False
            and null_fields <= set(summary) and all(summary[k] is None for k in null_fields)
            and summary.get("observed_terminal_checker_records") == []
            and summary.get("archive_role") == "prepared_for_attempt; never described as checked-and-accepted"
            and summary.get("missing_artifacts") == [g.path(n) for n in recovery_missing_order(recovery)]
            and summary.get("recorded_interruption_finish_utc") == attempted["finished_utc"]
            and summary.get("recovery_observed_end_utc") == recovery["observed_end_utc"], "interruption observations were replaced or final fields invented")
    for key, name, kind in [
        ("result", m.RETRY + "/retry-result.json", "completed_receipt"),
        ("prepared_stage_receipt", m.RETRY + "/stages/worker-stack256-nanoda/prepared.json", "manifest"),
        ("raw", m.RETRY + "/stages/worker-stack256-nanoda/raw.log", "recovered_log"),
        ("worker_event", m.RETRY + "/worker-resource.json", "manifest"),
        ("recovery_observation", RECOVERY, "manifest"),
        ("outer_raw_fragment", OUTER_RAW, "recovered_log"),
    ]:
        g.bind(summary[key], name, kind)
    # Gate.reference requires a positive size; the exceptional zero-byte capture
    # is checked directly instead and is never selected as JSON for publication.
    require(summary["outer_capture"].get("path") == g.path(OUTER_EMPTY)
            and summary["outer_capture"].get("sha256") == EMPTY_SHA
            and m.integer(summary["outer_capture"].get("size_bytes"), 0), "empty outer capture identity differs")
    prepared = g.obj(m.RETRY + "/stages/worker-stack256-nanoda/prepared.json")
    require(summary.get("prepared_stage") == prepared, "prepared stage data differs")
    launches = summary.get("actual_launch_records", [])
    require(len(launches) == 3, "launched Nano records missing")
    for row, short in zip(launches, ("00-prepared.json", "01-started.json", "effective-config.json")):
        g.bind(row, NANO + "/" + short)
    asset = launched_inputs(g, m, result)
    g.reference(summary["archive"], NANO + "/export.ndjson.gz", asset["gzip_sha256"], asset["gzip_size_bytes"])
    return asset, logs, [{"path": OUTER_EMPTY, "sha256": EMPTY_SHA, "size_bytes": 0,
                          "role": "Preserved empty capture, not a JSON document or checkpoint DIGEST",
                          "identity_source": RECOVERY, "availability": "Retained locally; not parsed or copied as JSON"}]


def recovery_missing_order(recovery):
    return [row["path"] for row in recovery["artifacts"] if row["exists"] is False]


def native_interrupted_selection(base, map_name, publisher):
    h, m = helper_modules(base, publisher); g = m.Gate(base, publisher)
    require(re.fullmatch(r"publication/native-interrupted-selection-r[1-9][0-9]*\.json", map_name), "interrupted map namespace differs")
    selection = g.obj(map_name)
    require(selection.get("schema") == "eth-native-interrupted-selection/1" and selection.get("aggregate_directory") == DIRECTORY
            and set(selection.get("aggregate_files", {})) == OUTPUTS and selection.get("publication_mode") == MODE
            and selection.get("verdict") == VERDICT and selection.get("original_lean_suite_passed") is True
            and selection.get("expanded_suite_passed") is False and selection.get("all_required_native_checks_passed") is False
            and selection.get("original_r2_protocol_passed") is False and selection.get("independent_nanoda_acceptance_observed") is False
            and selection.get("additional_nanoda_verification") == "INTERRUPTED" and m.integer(selection.get("interrupt_signal"), 15)
            and selection.get("attempt_timed_out") is False
            and {"checker_exit_code", "independent_nanoda_accepted", "final_attempt_cpu_seconds", "final_attempt_wall_seconds"} <= set(selection)
            and all(selection[k] is None for k in ("checker_exit_code", "independent_nanoda_accepted", "final_attempt_cpu_seconds", "final_attempt_wall_seconds")),
            "interrupted selection must explicitly preserve unknown results/costs")
    for short, row in selection["aggregate_files"].items():
        g.bind(row, DIRECTORY + "/" + short, "report" if short.endswith(".md") else "manifest")
    prepared, closing = g.obj(DIRECTORY + "/closure-prepared.json"), g.obj(DIRECTORY + "/closure-finished.json")
    g.bind(prepared["source"], CLOSURE_SOURCE, "source")
    require(prepared.get("schema") == closing.get("schema") == SCHEMA and prepared.get("status") == "preparing_interrupted_closure"
            and prepared.get("proof_execution") is False and prepared["source"]["sha256"] == CLOSURE_SHA
            and closing.get("status") == "interrupted_evidence_closed" and closing.get("expanded_suite_passed") is False,
            "reviewed interrupted closure has no final seal")
    result = json.loads(g.bind(closing["result"], DIRECTORY + "/native-interrupted-result.json"))
    g.bind(closing["report"], DIRECTORY + "/report.md", "report")
    artifacts = json.loads(g.bind(closing["artifacts_manifest"], DIRECTORY + "/native-interrupted-artifacts.json"))
    require(result.get("schema") == SCHEMA and result.get("verdict") == VERDICT and result.get("original_lean_suite_passed") is True
            and result.get("all_required_native_checks_passed") is False and result.get("expanded_suite_passed") is False
            and result.get("original_r2_protocol_passed") is False and result.get("additional_nanoda_verification") == "INTERRUPTED"
            and result.get("independent_nanoda_acceptance_observed") is False and result.get("input_fingerprint") == m.FP
            and {"checker_exit_code", "independent_nanoda_accepted"} <= set(result)
            and result["checker_exit_code"] is None and result["independent_nanoda_accepted"] is None
            and artifacts.get("artifacts") == result.get("artifacts") and artifacts.get("public_small_artifacts") == result.get("public_small_artifacts"),
            "interrupted result invents acceptance/costs or artifact bindings differ")
    resource = result["resource_use"]
    unknown = {"interrupted_attempt_final_child_cpu_seconds", "interrupted_attempt_final_wall_seconds", "total_campaign_final_child_cpu_seconds", "total_campaign_final_wall_seconds"}
    require(unknown <= set(resource) and all(resource[k] is None for k in unknown), "unknown final attempt/campaign costs were invented")
    g.read(HELPERS, "source"); g.read(h.METADATA_SOURCE, "source")
    require(publisher.sha(g.read(m.AGGREGATOR, "source")) == m.AGGREGATOR_SHA, "reviewed R7 metadata source differs")
    export = h.original_phases(g, m, publisher, result)
    m.tool_metadata(g)
    old_asset = h.retained_failures(g, m, result, export)
    asset, interrupted_logs, omissions = interrupted_summary(g, h, m, result)
    h.build_closure(g, m, result)
    reviews = selection.get("reviews", [])
    require(len({r["path"] for r in reviews}) == len(reviews) and m.REQUIRED_REVIEWS <= {r["path"] for r in reviews}, "combined saved review/report missing")
    for row in reviews:
        name = row["path"]; require(name in m.REVIEWS, "review is not explicitly named")
        g.bind({**row, "path": g.path(name)}, name, "report" if name.endswith(".md") else "manifest")
    return {"map": map_name, "map_sha256": publisher.sha(g.read(map_name)), "files": g.files,
            "publication_mode": MODE, "verdict": VERDICT, "original_lean_suite_passed": True,
            "expanded_suite_passed": False, "all_required_native_checks_passed": False, "original_r2_protocol_passed": False,
            "additional_nanoda_verification": "INTERRUPTED", "interrupt_signal": 15, "attempt_timed_out": False,
            "independent_nanoda_acceptance_observed": False, "independent_nanoda_accepted": None, "checker_exit_code": None,
            "final_attempt_cpu_seconds": None, "final_attempt_wall_seconds": None,
            "closed_log_bindings": g.logs, "interrupted_log_bindings": interrupted_logs,
            "omitted_large_assets": [asset, old_asset], "omitted_observation_files": omissions,
            "scope": "Metadata/allowlist consistency only; recovery is not a terminal checker/stage receipt, timeout or complete cost record"}
