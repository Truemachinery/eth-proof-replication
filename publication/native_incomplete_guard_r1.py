"""Fixed metadata/allowlist gate for a closed, explicitly incomplete Rust attempt.

This is disjoint from positive publication admission. It neither runs nor replaces
the pinned incomplete-closure validator. The root creates a map only after the
actual terminal attempt, final identity, closure seal and combined saved review.
Large exports/binaries/source trees are never read or copied by this module.
"""
import json
from pathlib import Path, PurePosixPath
import re
import types

METADATA_SOURCE = "publication/native_worker_guard_r1.py"
METADATA_SHA = "68d3ef6d9e0c3d4ae436b2901f4ac483cfa49a5f65982ca07d7e56ea7a21c726"
CLOSURE_SOURCE = "openai/aggregate_native_incomplete_r2.py"
CLOSURE_SHA = "97d65f2fcc779f4e8ea5473716c7da21cb6dea98c9ca81a76e9a80658fff8940"
DIRECTORY = "openai/native-incomplete-records/worker-stack256-r2-01"
SCHEMA = "openai-native-incomplete-result/1"
VERDICT = "ORIGINAL_LEAN_SUITE_PASS_ADDITIONAL_NANODA_INCOMPLETE"
PUBLICATION_MODE = "original-lean-pass-additional-nanoda-incomplete"
OUTPUTS = {"closure-prepared.json", "native-incomplete-result.json", "native-incomplete-artifacts.json", "report.md", "closure-finished.json"}
OUTER_NAMES = {
    "openai/logs/native-worker-stack256-cf-r3-checkpoint.json": "openai/logs/native-worker-stack256-cf-r3-checkpoint.txt",
}
SCHEDULE = {
    "temporary-suspension-r1.json": "73584dc6355248c7899afe15e527281af1a0ac5641071d78ff321a655b2341ef",
    "temporary-resumption-r1.json": "7765cec437c7dd350ff481edf35dd76d4df8e87f04b223240860bda90c12689f",
    "memory-pressure-suspension-r2.json": "34d3b7d059439eea0b9d5a41df8470fad59b22b524403b62b1ea58e1a018ca95",
    "memory-pressure-resumption-r3.json": "de271acadc3b41a6556f614aafcd9595bf7f9ff762821b72ddc9947c88b095db",
    "memory-pressure-resumption-r4.json": "810e07a6d0b5c63f77ec064f91f998f4ab5b0fee948d72b8f210670a2451f9d5",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def same_nullable_exit(actual, expected):
    return actual is None if expected is None else type(actual) is int and actual == expected


def metadata(base, publisher):
    """Load only hash-pinned, side-effect-free small publication helpers."""
    source = publisher.read_stable(Path(base), METADATA_SOURCE)
    require(publisher.sha(source) == METADATA_SHA, "reviewed metadata helpers changed")
    module = types.ModuleType("pinned_native_publication_metadata")
    exec(compile(source, str(Path(base) / METADATA_SOURCE), "exec"), module.__dict__)
    return module


def name_from_reference(g, row):
    require(isinstance(row, dict) and isinstance(row.get("path"), str), "missing evidence reference")
    return str(Path(row["path"]).relative_to(g.base))


def original_phases(g, m, publisher, result):
    rows = result.get("original_seven_phase_results", [])
    require([r.get("name") for r in rows] == list(m.ORIGINAL), "exact seven original successful phases missing")
    for row in rows:
        phase = row["name"]; i = m.PHASES.index(phase) + 1
        folder = "openai/native-phase-records/r2-" + str(i).zfill(2) + "-" + phase
        name = folder + "/phase-result.json"
        g.bind(row["result"], name, "completed_receipt")
        bundle = publisher.native_phase_bundle(g.base, name)
        require(bundle["result"]["input_fingerprint"] == m.FP
                and bundle["inputs"]["selected_inputs"] == result["source_and_tool_inputs"]
                and row.get("stage") == bundle["result"]["stage_receipts"][0], "original phase/result lineage differs")
        for item in bundle["files"]:
            g.read(item, "completed_log" if item.endswith("raw.log") else "completed_receipt" if item == name else "manifest")
        raw_name, digest, size = bundle["raw"]
        g.logs[raw_name] = {"receipt": name, "exit_code": 0, "timed_out": False, "raw_log_sha256": digest, "raw_log_bytes": size}
    export_phase = g.obj("openai/native-phase-records/r2-05-selected-export/phase-result.json")
    export = export_phase["export"]; g.reference(export, m.EXPORT_NAME, m.EXPORT_SHA, m.EXPORT_SIZE)
    capture = json.loads(g.bind(export_phase["capture_receipt"], "openai/native-phase-records/r2-05-selected-export/export-capture.json"))
    require(capture.get("schema") == "native-direct-fd-export/2" and capture.get("complete") is True
            and m.integer(capture.get("child_exit_code"), 0) and capture.get("export") == export, "selected export is not closed")
    return export


def retained_failures(g, m, result, export):
    failure = result["retained_original_nanoda_failure"]
    require(failure.get("directory") == g.path(m.FAILED), "original failure directory differs")
    failed = json.loads(g.bind(failure["phase_result"], m.FAILED + "/phase-result.json", "completed_receipt"))
    inputs = g.obj(m.FAILED + "/phase-inputs.json"); g.obj(m.FAILED + "/phase-prepared.json")
    require(failed.get("status") == "failed" and failed.get("phase") == "extra-nanoda"
            and failed.get("input_fingerprint") == inputs.get("input_fingerprint") == m.FP, "original failed stage was relabeled")
    stage, raw = g.stage(m.FAILED, "extra-nanoda", failed, inputs, -6)
    require(g.p.sha(raw) == "590ccc60513da51ab0aad98c32b68c0f485d0fda4958c7255feb5175c55bc4e2"
            and len(raw) == 101 and b"stack overflow" in raw and failure.get("stage") == stage,
            "actual original overflow evidence differs")
    _, _, asset = m.nano(g, m.FAILED, failure["nanoda"], export, -6, m.OLD_BINARY, m.OLD_BINARY_SHA, "verification-tools/record_nanoda.py")
    require(asset["gzip_sha256"] == "c9408fc5dedf81e411e1a259c160804b10f8ae8ccce6b2abefff2170c0cbb789"
            and asset["gzip_size_bytes"] == 453732564, "original failed archive differs")
    m.outer_failure(g, failure, "openai/logs/native-r2-extra-nanoda-checkpoint.json", "openai/logs/native-r2-extra-nanoda-checkpoint.txt",
                    4013, 125, "0599976a37cdc35a45d160484af270befd31eeae4f440c90af69bd4381cc8ca4", failed)
    pre = result["retained_preexec_environment_failure"]
    require(pre.get("directory") == g.path(m.PREEXEC) and pre.get("nano_launched") is False, "preexec negative missing")
    pre_result = json.loads(g.bind(pre["result"], m.PREEXEC + "/retry-result.json", "completed_receipt"))
    pre_inputs = json.loads(g.bind(pre["inputs"], m.PREEXEC + "/retry-inputs.json"))
    g.obj(m.PREEXEC + "/retry-prepared.json"); m.config(g, m.PREEXEC, export)
    require(pre_result.get("status") == "failed" and pre_result.get("protocol_variant") == "openai-native-r2-nanoda-worker-stack256-r2"
            and pre_result.get("original_r2_attempt_passed") is False, "preexec failure relabeled")
    pre_stage, pre_raw = g.stage(m.PREEXEC, "worker-stack256-nanoda", pre_result, pre_inputs, 1)
    require(g.p.sha(pre_raw) == "f384b5c2c40e0e661b81aa604ae8672a24e6613b536aecba804ea25821090503"
            and len(pre_raw) == 848 and b"WORKER_RESOURCE " not in pre_raw and pre.get("stage") == pre_stage
            and not (g.base / m.PREEXEC / "worker-resource.json").exists()
            and not list((g.base / m.PREEXEC / "nanoda-records").glob("nanoda-*")), "preexec failure unexpectedly launched checker")
    require(g.p.sha(g.read("openai/nanoda_worker_stack_retry_r2.py", "source")) == "59931d7b0d00ba5651322e6a3e1efb9524223334ce74ee767891dd95534557fc"
            and g.p.sha(g.read(m.PREEXEC + "/retry-result.json")) == "d6b716803c4d9d36b02052bcd04b7cc40d38195973939c59ec2b25f628db627d", "preexec source/result drift")
    m.outer_failure(g, pre, "openai/logs/native-worker-stack256-r2-checkpoint.json", "openai/logs/native-worker-stack256-r2-checkpoint.txt",
                    4044, 1, "694e0b7dc13d25a56f1d66996bae5d5820cc42704d3c71705549f6401f3ec72e", pre_result)
    m.mainstack_negatives(g)
    wanted = {"openai/nanoda_serial_stack_retry_r1.py", "openai/aggregate_native_result_r5.py",
              "publication/negative-evidence/main-stack-control-4023.txt", "publication/negative-evidence/main-stack-diagnostic-4025.txt"}
    rows = result.get("retained_mainstack_negative_artifacts", [])
    require(len(rows) == 4 and {name_from_reference(g, r) for r in rows} == wanted, "unsupported-mainstack history incomplete")
    for row in rows:
        name = name_from_reference(g, row)
        g.bind(row, name, "source" if name.endswith(".py") else "completed_log")
    return asset


def terminal_attempt(g, m, result, export):
    summary = result["additional_terminal_attempt"]; folder = m.RETRY
    require(summary.get("name") == "terminal-additional-nanoda" and summary.get("directory") == g.path(folder)
            and summary.get("acceptance_observed") is False
            and {"checker_exit_code", "independent_nanoda_accepted", "inputs_unchanged_during_check"} <= set(summary),
            "terminal nonacceptance summary differs or nullable observation fields are missing")
    attempted = json.loads(g.bind(summary["result"], folder + "/retry-result.json", "completed_receipt"))
    prepared, inputs = g.obj(folder + "/retry-prepared.json"), g.obj(folder + "/retry-inputs.json")
    require(attempted.get("schema") == "openai-native-resource-retry/1" and attempted.get("status") == "failed"
            and attempted.get("protocol_variant") == m.PROTOCOL and attempted.get("logical_check") == "extra-nanoda"
            and attempted.get("original_r2_attempt_passed") is False and attempted.get("interrupt_signal") is None
            and attempted.get("record_directory") == g.path(folder) and attempted.get("resource_policy") == m.POLICY
            and prepared.get("started_utc") == attempted.get("started_utc") and prepared.get("protocol_variant") == m.PROTOCOL
            and g.p.closed_times(attempted.get("started_utc"), attempted.get("finished_utc"))
            and inputs.get("schema") == "openai-native-resource-retry-inputs/1" and inputs.get("protocol_variant") == m.PROTOCOL
            and inputs.get("base_r2_input_fingerprint") == m.FP
            and inputs.get("selected_inputs") == result["source_and_tool_inputs"] and inputs.get("export_input") == export
            and inputs.get("config_delta") == {} and inputs.get("resource_policy") == m.POLICY, "attempt is not the closed reviewed negative")
    g.bind(inputs["retry_source"], m.HELPER, "source")
    require(inputs["retry_source"]["sha256"] == m.HELPER_SHA, "reviewed R3 helper changed")
    require(set(inputs["resource_inputs"]) == set(m.PINS) | {"target/release/nanoda_bin"}, "resource input set differs")
    for short, digest in {**m.PINS, "target/release/nanoda_bin": m.BINARY_SHA}.items():
        g.reference(inputs["resource_inputs"][short], m.TOOLS + "/" + short, digest)
    require(result.get("resource_profile_inputs") == inputs["resource_inputs"], "closure/resource inputs differ")
    m.config(g, folder, export)
    sd = folder + "/stages/worker-stack256-nanoda"
    stage, start = g.obj(sd + "/finished.json"), g.obj(sd + "/prepared.json")
    raw = g.bind(summary["raw"], sd + "/raw.log", "completed_log")
    code = stage.get("exit_code")
    require(type(code) is int and code != 0 and stage.get("schema") == "eth-ci-stage/1"
            and stage.get("name") == "worker-stack256-nanoda" and stage.get("stdout_is_export") is False
            and all(stage.get(k) == v for k, v in start.items()) and stage.get("argv") == inputs.get("argv")
            and stage.get("cwd") == inputs.get("cwd") == g.path("openai/workspace")
            and m.integer(stage.get("timeout_seconds"), 7200) and m.integer(inputs.get("timeout_seconds"), 7200)
            and stage.get("raw_log_sha256") == g.p.sha(raw) and m.integer(stage.get("raw_log_bytes"), len(raw))
            and attempted.get("stage_receipts") == [stage] and summary.get("stage") == stage,
            "terminal stage is running, accepted, or not hash-bound")
    classification = "stage_timeout_checker_acceptance_unobserved" if code == 124 and stage.get("reason") == "stage timeout" else "terminal_stage_failure_checker_acceptance_unobserved"
    require(summary.get("classification") == classification, "terminal stage classification differs")
    g.logs[sd + "/raw.log"] = {"receipt": folder + "/retry-result.json", "exit_code": code,
                               "timed_out": stage.get("timed_out") if type(stage.get("timed_out")) is bool else classification.startswith("stage_timeout") if code == 124 else None,
                               "raw_log_sha256": g.p.sha(raw), "raw_log_bytes": len(raw),
                               "scope": "Terminal stage failure; no inferred checker logical rejection or acceptance"}
    worker = json.loads(g.bind(summary["worker_event"], folder + "/worker-resource.json"))
    env = inputs["environment"]; python = inputs["argv"][0]
    require(worker.get("schema") == "native-nanoda-worker-resource/2" and worker.get("protocol_variant") == m.PROTOCOL
            and worker.get("retry_source") == inputs["retry_source"] and worker.get("resource_policy") == m.POLICY
            and worker.get("resource_inputs") == inputs["resource_inputs"] and worker.get("environment") == env
            and worker.get("environment_keys") == inputs.get("environment_keys") == sorted(env)
            and g.p.sha(env.get(m.CF_KEY, "").encode()) == m.CF_SHA and env.get("NANODA_REAL_BINARY") == g.path(m.BINARY)
            and inputs["argv"] == [python, g.path(m.HELPER), "--child", g.path(folder)]
            and worker.get("exec_argv") == [python, g.path(m.TOOLS + "/record_nanoda.py"), g.path(folder + "/additional-nanoda-config.json")]
            and worker.get("cwd") == g.path("openai/workspace") and type(worker.get("pid")) is int and worker["pid"] == worker.get("pgid")
            and worker.get("main_stack_limits_before") == worker.get("main_stack_limits_after")
            and isinstance(worker.get("main_stack_limits_before"), list) and len(worker["main_stack_limits_before"]) == 2
            and all(type(v) is int for v in worker["main_stack_limits_before"])
            and worker.get("main_stack_limits_changed") is False and worker.get("actual_nanoda_worker_extent_measured") is False,
            "actual worker event/resource/environment differs")
    require([json.loads(line[len(b"WORKER_RESOURCE "):]) for line in raw.splitlines() if line.startswith(b"WORKER_RESOURCE ")] == [worker], "raw worker event differs")
    launches = summary.get("actual_launch_records", [])
    require(len(launches) == 3, "actual launch records missing")
    first = name_from_reference(g, launches[0])
    require(re.fullmatch(re.escape(folder) + r"/nanoda-records/nanoda-" + str(worker["pid"]) + r"-[A-Za-z0-9_-]+/00-prepared\.json", first), "checker record root/PID differs")
    record = str(PurePosixPath(first).parent)
    names = [record + "/" + n for n in ("00-prepared.json", "01-started.json", "effective-config.json")]
    for name, ref in zip(names, launches):
        g.bind(ref, name)
    zero, one, effective = g.obj(names[0]), g.obj(names[1]), g.obj(names[2])
    wanted = m.config(g, folder, export)
    require(effective == wanted and zero.get("effective_policy") == wanted and zero.get("policy_changes_by_recorder") is False
            and zero.get("mode") == "native_fake_landrun_unsandboxed" and zero.get("cwd") == g.path("openai/workspace")
            and one.get("checker_argv") == zero.get("checker_argv") == [g.path(m.BINARY), g.path(folder + "/additional-nanoda-config.json")]
            and zero.get("wrapper_argv") == [g.path(m.TOOLS + "/record_nanoda.py"), g.path(folder + "/additional-nanoda-config.json")]
            and type(one.get("pid")) is int and one["pid"] > 0
            and m.same_identity(zero.get("export_before", {}), export), "launched checker/policy/export differs")
    g.reference(zero["binary_before"], m.BINARY, m.BINARY_SHA, 1260088)
    g.reference(zero["wrapper_source"], m.TOOLS + "/record_nanoda.py", m.RECORDER_SHA, 8494)
    g.bind(zero["config_before"], folder + "/additional-nanoda-config.json")
    g.bind(zero["config_archive"], names[2])
    require(g.read(names[2]) == g.read(folder + "/additional-nanoda-config.json"), "effective config bytes differ")
    archive = zero["export_archive"]
    require(archive.get("uncompressed_sha256") == export["sha256"] and m.integer(archive.get("uncompressed_size_bytes"), export["size_bytes"])
            and m.same_identity(summary.get("archive", {}), archive.get("gzip", {})), "prepared archive/export identity differs")
    g.reference(archive["gzip"], record + "/export.ndjson.gz")
    present = [record + "/" + n for n in ("02-finished.json", "99-error.json") if (g.base / record / n).exists()]
    observed = summary.get("observed_terminal_checker_records", [])
    require("observed_terminal_checker_records" in summary and type(observed) is list
            and len(present) <= 1 and len(observed) == len(present) and [name_from_reference(g, r) for r in observed] == present,
            "optional terminal checker record set conflicts or differs")
    checker_code, accepted, complete, unchanged = None, None, False, None
    for name, ref in zip(present, observed):
        terminal = json.loads(g.bind(ref, name))
        checker_code = terminal.get("checker_exit_code")
        require(checker_code is None or type(checker_code) is int and checker_code != 0, "checker0 or invalid exit cannot use incomplete path")
        if name.endswith("02-finished.json"):
            require(type(checker_code) is int and terminal.get("recording_complete") is True and terminal.get("inputs_unchanged") is True
                    and m.integer(terminal.get("wrapper_exit_code"), checker_code)
                    and all(terminal.get(k) == v for k, v in zero.items())
                    and m.same_identity(terminal.get("export_after", {}), export), "closed checker nonzero recording differs")
            g.reference(terminal["binary_after"], m.BINARY, m.BINARY_SHA, 1260088)
            g.bind(terminal["config_after"], folder + "/additional-nanoda-config.json")
            accepted, complete, unchanged = False, True, True
        else:
            require(terminal.get("recording_complete") is False, "error record asserts completion")
            accepted = False if checker_code is not None else None
    require(same_nullable_exit(summary.get("checker_exit_code"), checker_code) and "checker_exit_code" in summary
            and summary.get("independent_nanoda_accepted") is accepted
            and summary.get("recording_complete") is complete and summary.get("inputs_unchanged_during_check") is unchanged
            and same_nullable_exit(result.get("checker_exit_code"), checker_code) and "checker_exit_code" in result
            and result.get("independent_nanoda_accepted") is accepted
            and summary.get("archive_role") == "prepared_for_attempt; never described as checked-and-accepted",
            "unknown checker fields were invented or acceptance asserted")
    outer_name = name_from_reference(g, summary["outer_receipt"])
    require(outer_name in OUTER_NAMES, "terminal outer receipt is not explicitly named")
    outer = json.loads(g.bind(summary["outer_receipt"], outer_name)); outer_raw_name = OUTER_NAMES[outer_name]
    outer_raw = g.read(outer_raw_name, "completed_log")
    expected_exit = code if 0 < code < 256 else 125
    require(outer.get("agent") == "codex-eth-replication" and outer.get("task") == "external-eth-proof-replication-20261104"
            and m.integer(outer.get("exit_code"), expected_exit) and outer.get("timed_out") is False
            and outer.get("log_sha256") == g.p.sha(outer_raw) and m.integer(outer.get("log_size"), len(outer_raw))
            and summary.get("outer_digest") == outer, "terminal outer digest differs")
    last = next((line for line in reversed(outer_raw.splitlines()) if line.startswith(b'{"')), None)
    require(last is not None and json.loads(last) == attempted, "terminal outer raw lacks the actual failed result")
    g.logs[outer_raw_name] = {"receipt": outer_name, "exit_code": expected_exit, "timed_out": False,
                              "raw_log_sha256": g.p.sha(outer_raw), "raw_log_bytes": len(outer_raw)}
    asset = {"receipt": names[0], "archive_role": "prepared_for_attempt", "recording_complete": complete,
             "checker_exit_code": checker_code, "recorded_checker_accepted": False,
             "independent_nanoda_accepted": accepted, "acceptance_observed": False,
             "inputs_unchanged_during_check": unchanged, "raw_sha256": export["sha256"], "raw_size_bytes": export["size_bytes"],
             "gzip_sha256": archive["gzip"]["sha256"], "gzip_size_bytes": archive["gzip"]["size_bytes"],
             "availability": "Prepared attempt archive retained locally; not published or described as accepted",
             "identity_source": "Pinned closed incomplete-result and actual prepared receipts; packager did not hash large assets"}
    return asset, accepted


def build_closure(g, m, result):
    build = result["source_build"]; name = "openai/logs/source-build-gated-r4-receipt.json"
    wrapper = json.loads(g.bind(build["receipt"], name)); cp = wrapper["checkpoint_run_result"]
    raw_name = "openai/logs/source-build-gated-r4.txt"; raw = g.bind(build["raw"], raw_name, "completed_log")
    require(m.integer(wrapper.get("exec_session_id"), 11317) and m.integer(wrapper.get("final_exec_exit_code"), 0)
            and m.integer(cp.get("exit_code"), 0) and cp.get("timed_out") is False
            and cp.get("log_sha256") == g.p.sha(raw) and m.integer(cp.get("log_size"), len(raw))
            and re.search(rb"(?m)^Build completed successfully \([0-9]+ jobs\)\.$", raw), "source build not closed/hash-bound")
    g.logs[raw_name] = {"receipt": name, "exit_code": 0, "timed_out": False, "raw_log_sha256": g.p.sha(raw), "raw_log_bytes": len(raw)}
    rows = build.get("scheduling_receipts", [])
    require(len(rows) == 5 and {name_from_reference(g, r) for r in rows} == {"openai/logs/" + n for n in SCHEDULE}, "scheduling record set differs")
    for row in rows:
        name = name_from_reference(g, row)
        require(g.p.sha(g.bind(row, name)) == SCHEDULE[PurePosixPath(name).name], "manual scheduling record differs")


def native_incomplete_selection(base, map_name, publisher):
    m = metadata(base, publisher); g = m.Gate(base, publisher)
    require(re.fullmatch(r"publication/native-incomplete-selection-r[1-9][0-9]*\.json", map_name), "incomplete map namespace differs")
    selection = g.obj(map_name)
    require(selection.get("schema") == "eth-native-incomplete-selection/1" and selection.get("aggregate_directory") == DIRECTORY
            and set(selection.get("aggregate_files", {})) == OUTPUTS
            and selection.get("publication_mode") == PUBLICATION_MODE and selection.get("verdict") == VERDICT
            and selection.get("original_lean_suite_passed") is True and selection.get("expanded_suite_passed") is False
            and selection.get("all_required_native_checks_passed") is False and selection.get("original_r2_protocol_passed") is False
            and selection.get("independent_nanoda_acceptance_observed") is False
            and "independent_nanoda_accepted" in selection and "checker_exit_code" in selection,
            "incomplete selection root/output set or explicit verdict differs")
    for short, row in selection["aggregate_files"].items():
        g.bind(row, DIRECTORY + "/" + short, "report" if short.endswith(".md") else "manifest")
    prepared, closing = g.obj(DIRECTORY + "/closure-prepared.json"), g.obj(DIRECTORY + "/closure-finished.json")
    g.bind(prepared["source"], CLOSURE_SOURCE, "source")
    require(prepared.get("schema") == closing.get("schema") == SCHEMA and prepared.get("status") == "preparing_negative_closure"
            and prepared.get("proof_execution") is False and prepared["source"]["sha256"] == CLOSURE_SHA
            and closing.get("status") == "negative_evidence_closed" and closing.get("expanded_suite_passed") is False,
            "reviewed incomplete closure seal missing")
    result = json.loads(g.bind(closing["result"], DIRECTORY + "/native-incomplete-result.json"))
    g.bind(closing["report"], DIRECTORY + "/report.md", "report")
    artifacts = json.loads(g.bind(closing["artifacts_manifest"], DIRECTORY + "/native-incomplete-artifacts.json"))
    require(result.get("schema") == SCHEMA and result.get("verdict") == VERDICT
            and {"checker_exit_code", "independent_nanoda_accepted"} <= set(result)
            and result.get("original_lean_suite_passed") is True and result.get("all_required_native_checks_passed") is False
            and result.get("expanded_suite_passed") is False and result.get("original_r2_protocol_passed") is False
            and result.get("additional_nanoda_verification") == "INCOMPLETE" and result.get("independent_nanoda_acceptance_observed") is False
            and result.get("input_fingerprint") == m.FP and artifacts.get("artifacts") == result.get("artifacts")
            and artifacts.get("public_small_artifacts") == result.get("public_small_artifacts"), "incomplete verdict or artifact lists differ")
    g.read(METADATA_SOURCE, "source")
    require(publisher.sha(g.read(m.AGGREGATOR, "source")) == m.AGGREGATOR_SHA, "reviewed R7 metadata source changed")
    export = original_phases(g, m, publisher, result)
    m.tool_metadata(g)
    old_asset = retained_failures(g, m, result, export)
    terminal_asset, accepted = terminal_attempt(g, m, result, export)
    require(selection["independent_nanoda_accepted"] is accepted
            and same_nullable_exit(selection["checker_exit_code"], terminal_asset["checker_exit_code"]),
            "selection invented terminal checker observations")
    build_closure(g, m, result)
    reviews = selection.get("reviews", [])
    require(len({r["path"] for r in reviews}) == len(reviews) and m.REQUIRED_REVIEWS <= {r["path"] for r in reviews}, "final combined review/report missing")
    for row in reviews:
        name = row["path"]; require(name in m.REVIEWS, "review is not explicitly named")
        g.bind({**row, "path": g.path(name)}, name, "report" if name.endswith(".md") else "manifest")
    return {"map": map_name, "map_sha256": publisher.sha(g.read(map_name)), "files": g.files,
            "publication_mode": PUBLICATION_MODE, "verdict": VERDICT, "original_lean_suite_passed": True,
            "expanded_suite_passed": False, "all_required_native_checks_passed": False, "original_r2_protocol_passed": False,
            "independent_nanoda_acceptance_observed": False, "independent_nanoda_accepted": accepted,
            "checker_exit_code": terminal_asset["checker_exit_code"], "closed_log_bindings": g.logs,
            "omitted_large_assets": [terminal_asset, old_asset],
            "scope": "Metadata/allowlist consistency only; no positive Rust verdict, second closure verification or large-asset rehash"}
