#!/usr/bin/env python3
"""Explicit new Nanoda resource-build retry after fresh closes, before post-identity.

New binary changes only the compiled requested worker stack16MiB to256MiB.
Original two-thread strict policy, export and checker logic remain unchanged.
Original failed Nano and unsupported main-stack diagnostics remain retained.
No process changes its main-stack limit, and actual Nano worker extent is unmeasured.
"""
import argparse
import datetime
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE / "native-retry-records"
BASE_FP = "c84c8907998f23cc282a29ae7fef4a37cbaff735327096e748afe546af8c4f52"
BASE_SHA = "a4d5e8bffd81a7100121c01e7ee2fa40ca94d595a8e524624ce1774457f29341"
PROTOCOL = "openai-native-r2-nanoda-worker-stack256-cfenv-r3"
CF_KEY = "__CF_USER_TEXT_ENCODING"
CF_VALUE_SHA256 = "bfea86ae0b123713ac5b1af20b2dd4ead4f0bb81822ed654e80347e6fa420f3b"
STAGE = "worker-stack256-nanoda"
TOOLS = BASE.parent / "verification-tools-worker-stack256"
RESOURCE_BINARY = TOOLS / "target/release/nanoda_bin"
RESOURCE_RECORDER = TOOLS / "record_nanoda.py"
RESOURCE_POLICY = {"nanoda_num_threads": 2, "compiled_requested_worker_stack_bytes": 268435456,
                   "original_compiled_requested_worker_stack_bytes": 16777216,
                   "checker_binary_changed": True, "checker_logic_patch": False,
                   "main_stack_limits_changed": False, "actual_nanoda_worker_extent_measured": False,
                   "export_changed": False, "axiom_policy_changed": False, "config_changed": False}
RESOURCE_PINS = {"tool-manifest-r1.json": "f90219aaeedd7bbff3746eff8167c99b8d075d1045ae5c4363bc8ebb425bc30d",
    "source-provenance-r1.json": "b73658a2cec0410e1df0a90c446c5f15c0cf3a28875131027972ddece9c71dc7",
    "build-result-r1.json": "9746cc46746f11d88d5d0f3f5ad1458e05a57627abb90fd6d60c6f42ebef325e",
    "resource-only.patch": "8772472e7acd9c5900d01db457b7e7ba6d5e2273c57e3f939fa5d2485412659f",
    "worker-probe-result-r1.json": "c2d1e9442e256121dff3f627d3a6db0deb184ec5ca6d9c498dd9910a272c65cd",
    "tiny-controls-r1/control-result-r1.json": "c539e45b86bf71fbfb4b69d61a2cf3654681baf3a159ed9a2ffd6a4c7b6ccd8b",
    "record_nanoda.py": "c34f36d630d182708937a5280b6eda8d0723fa0ffdd85caf8fc54af17b332f48",
    "target/release/nanoda_bin": "10e1a4ebdb6fa606ca8d7a60774d8af0655294ab0b19d03a838a5ba746b7c2d9"}
INTERRUPTED = None


def base_module():
    path = BASE / "aggregate_native_result_r4.py"
    import hashlib
    if hashlib.sha256(path.read_bytes()).hexdigest() != BASE_SHA:
        raise ValueError("pinned R4 metadata validator changed")
    spec = importlib.util.spec_from_file_location("retry_metadata_base_r4", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy(export, threads):
    if type(threads) is not int or threads not in (1, 2):
        raise ValueError("only reviewed serial/failed-original thread policies exist")
    return {"use_stdin": False, "export_file_path": export["path"],
            "permitted_axioms": ["propext", "Quot.sound", "Classical.choice"],
            "unpermitted_axiom_hard_error": True, "num_threads": threads,
            "nat_extension": True, "string_extension": True}


def strict_policy_matches(actual, export, threads):
    return (actual == policy(export, threads) and type(actual.get("num_threads")) is int
            and actual.get("use_stdin") is False and actual.get("unpermitted_axiom_hard_error") is True
            and actual.get("nat_extension") is True and actual.get("string_extension") is True)


def original_nano_records(e, folder, export, threads, exit_code):
    """Bind actual recorded inputs and result; recording_complete is not acceptance."""
    m = base_module()
    paths = sorted((folder / "nanoda-records").glob("nanoda-*"))
    m.require(len(paths) == 1, "expected exactly one actual checker record")
    record = m.canonical(paths[0])
    m.require(not (record / "99-error.json").exists(), "checker recorder error exists")
    zero = e.json(record / "00-prepared.json", True)
    one = e.json(record / "01-started.json", True)
    two = e.json(record / "02-finished.json", True)
    config_path = folder / "additional-nanoda-config.json"
    config = e.identity(config_path, True)
    expected = policy(export, threads)
    m.require(strict_policy_matches(e.json(config_path), export, threads)
              and strict_policy_matches(e.json(record / "effective-config.json", True), export, threads),
              "strict actual checker policy differs")
    m.require(all(two.get(k) == v for k, v in zero.items()) and two["recording_complete"] is True
              and two["inputs_unchanged"] is True and two["policy_changes_by_recorder"] is False
              and type(two["checker_exit_code"]) is int and two["checker_exit_code"] == exit_code
              and type(two["wrapper_exit_code"]) is int and two["wrapper_exit_code"] == exit_code
              and two["effective_policy"] == expected and two["cwd"] == str(m.WORKSPACE)
              and two["mode"] == "native_fake_landrun_unsandboxed"
              and two["wrapper_argv"] == [str(m.NANODA_RECORDER), str(config_path)]
              and one["checker_argv"] == two["checker_argv"] == [str(m.NANODA), str(config_path)],
              "checker recording lineage/policy/result differs")
    for before, after, actual in [(two["binary_before"], two["binary_after"], e.identity(m.NANODA)),
                                  (two["config_before"], two["config_after"], config),
                                  (two["export_before"], two["export_after"], export)]:
        m.require(all(before[k] == after[k] == actual[k] for k in ["path", "sha256", "size_bytes"]),
                  "actual checked input changed/differs")
    e.bind(two["config_archive"], record / "effective-config.json")
    m.require(e.identity(record / "effective-config.json")["sha256"] == config["sha256"],
              "actual forwarded and archived config bytes differ")
    e.bind(two["shim"], m.SHIM)
    e.bind(two["wrapper_source"], m.NANODA_RECORDER)
    archive = e.bind(two["export_archive"]["gzip"], record / "export.ndjson.gz")
    m.require(two["export_archive"]["uncompressed_sha256"] == export["sha256"]
              and two["export_archive"]["uncompressed_size_bytes"] == export["size_bytes"], "archive payload binding differs")
    return {"record_directory": str(record), "finished_receipt": e.identity(record / "02-finished.json"),
            "gzip": archive, "small_records": [e.identity(record / n) for n in
            ["00-prepared.json", "01-started.json", "02-finished.json", "effective-config.json"]],
            "effective_policy": expected, "checker_cpu_seconds": m.number(two["checker_cpu_seconds"]),
            "checker_wall_seconds": m.number(two["checker_wall_seconds"]), "checker_exit_code": exit_code,
            "meaning": "Actual exit is separate from recording completeness; original failed attempt is never relabeled."}


def failed_attempt(e, folder, outer_path, content, export):
    m = base_module()
    folder = m.canonical(folder)
    m.require(folder == m.RECORD_ROOT / "r2-06-extra-nanoda", "supply the actual original failed attempt")
    result = e.json(folder / "phase-result.json", True)
    inputs = e.json(folder / "phase-inputs.json", True)
    prepared = e.json(folder / "phase-prepared.json", True)
    stage_dir = folder / "stages/extra-nanoda"
    stage = e.json(stage_dir / "finished.json", True)
    start = e.json(stage_dir / "prepared.json", True)
    raw = e.identity(stage_dir / "raw.log", True)
    m.require(result["status"] == "failed" and result["schema"] == "openai-native-phase/1"
              and result["phase"] == "extra-nanoda" and result["interrupt_signal"] is None
              and result["input_fingerprint"] == inputs["input_fingerprint"] == BASE_FP
              and inputs["selected_inputs"] == content and inputs["export_input"] == export
              and prepared["started_utc"] == result["started_utc"]
              and result["stage_receipts"] == [stage] and stage["exit_code"] == -6 and stage["reason"] is None
              and all(stage[k] == v for k, v in start.items())
              and stage["argv"] == inputs["argv"] == m.phase_command("extra-nanoda", folder, inputs["argv"][0])
              and inputs["environment"] == m.phase_environment("extra-nanoda", folder, inputs["argv"][0])
              and raw["sha256"] == stage["raw_log_sha256"] == "590ccc60513da51ab0aad98c32b68c0f485d0fda4958c7255feb5175c55bc4e2"
              and raw["size_bytes"] == stage["raw_log_bytes"] == 101, "original stack-overflow failure evidence differs")
    m.require(b"stack overflow" in (stage_dir / "raw.log").read_bytes(), "original resource failure text missing")
    nano = original_nano_records(e, folder, export, 2, -6)
    m.require(nano["gzip"]["sha256"] == "c9408fc5dedf81e411e1a259c160804b10f8ae8ccce6b2abefff2170c0cbb789"
              and nano["gzip"]["size_bytes"] == 453732564, "failed checked archive identity differs")
    outer = e.json(outer_path, True)  # Actual plain CLI DIGEST, not an invented exec wrapper.
    outer_raw = m.canonical(m.PROJECT / outer["log_path"])
    outer_identity = e.identity(outer_raw, True)
    m.require(outer["exit_code"] == 125 and outer["timed_out"] is False and outer["revision_event_id"] == 4013
              and outer["agent"] == "codex-eth-replication" and outer["task"] == "external-eth-proof-replication-20261104"
              and outer_identity["sha256"] == outer["log_sha256"] == "0599976a37cdc35a45d160484af270befd31eeae4f440c90af69bd4381cc8ca4"
              and outer_identity["size_bytes"] == outer["log_size"], "actual failed outer DIGEST differs")
    final_line = next((line for line in reversed(outer_raw.read_text().splitlines()) if line.startswith('{"')), None)
    m.require(final_line is not None and json.loads(final_line) == result,
              "failed outer raw does not contain the exact retained phase result")
    return {"directory": str(folder), "phase_result": e.identity(folder / "phase-result.json"),
            "inputs": e.identity(folder / "phase-inputs.json"), "raw": raw, "stage": stage, "nanoda": nano,
            "outer_receipt": e.identity(outer_path), "outer_digest": outer,
            "start": stage["started_utc_epoch"], "end": stage["started_utc_epoch"] + stage["wall_seconds"],
            "verdict": "FAILED: SIGABRT worker stack overflow; not a logical rejection or kernel acceptance."}


def retry_folder(value):
    m = base_module()
    path = m.canonical(value)
    m.require(path.is_relative_to(ROOT) and path != ROOT, "choose exclusive owned retry directory")
    return path


def nano_records(e, folder, export, threads=2, exit_code=0):
    """Bind actual recorded inputs and result; recording_complete is not acceptance."""
    m = base_module()
    m.require(threads == 2 and exit_code == 0, "only strict two-thread accepted resource retry is supported")
    paths = sorted((folder / "nanoda-records").glob("nanoda-*"))
    m.require(len(paths) == 1, "expected exactly one actual checker record")
    record = m.canonical(paths[0])
    m.require(not (record / "99-error.json").exists(), "checker recorder error exists")
    zero = e.json(record / "00-prepared.json", True)
    one = e.json(record / "01-started.json", True)
    two = e.json(record / "02-finished.json", True)
    config_path = folder / "additional-nanoda-config.json"
    config = e.identity(config_path, True)
    expected = policy(export, threads)
    m.require(strict_policy_matches(e.json(config_path), export, threads)
              and strict_policy_matches(e.json(record / "effective-config.json", True), export, threads),
              "strict actual checker policy differs")
    m.require(all(two.get(k) == v for k, v in zero.items()) and two["recording_complete"] is True
              and two["inputs_unchanged"] is True and two["policy_changes_by_recorder"] is False
              and type(two["checker_exit_code"]) is int and two["checker_exit_code"] == exit_code
              and type(two["wrapper_exit_code"]) is int and two["wrapper_exit_code"] == exit_code
              and two["effective_policy"] == expected and two["cwd"] == str(m.WORKSPACE)
              and two["mode"] == "native_fake_landrun_unsandboxed"
              and two["wrapper_argv"] == [str(RESOURCE_RECORDER), str(config_path)]
              and one["checker_argv"] == two["checker_argv"] == [str(RESOURCE_BINARY), str(config_path)],
              "checker recording lineage/policy/result differs")
    for before, after, actual in [(two["binary_before"], two["binary_after"], e.identity(RESOURCE_BINARY)),
                                  (two["config_before"], two["config_after"], config),
                                  (two["export_before"], two["export_after"], export)]:
        m.require(all(before[k] == after[k] == actual[k] for k in ["path", "sha256", "size_bytes"]),
                  "actual checked input changed/differs")
    e.bind(two["config_archive"], record / "effective-config.json")
    m.require(e.identity(record / "effective-config.json")["sha256"] == config["sha256"],
              "actual forwarded and archived config bytes differ")
    e.bind(two["shim"], m.SHIM)
    e.bind(two["wrapper_source"], RESOURCE_RECORDER)
    archive = e.bind(two["export_archive"]["gzip"], record / "export.ndjson.gz")
    m.require(two["export_archive"]["uncompressed_sha256"] == export["sha256"]
              and two["export_archive"]["uncompressed_size_bytes"] == export["size_bytes"], "archive payload binding differs")
    return {"record_directory": str(record), "finished_receipt": e.identity(record / "02-finished.json"),
            "gzip": archive, "small_records": [e.identity(record / n) for n in
            ["00-prepared.json", "01-started.json", "02-finished.json", "effective-config.json"]],
            "effective_policy": expected, "checker_cpu_seconds": m.number(two["checker_cpu_seconds"]),
            "checker_wall_seconds": m.number(two["checker_wall_seconds"]), "checker_exit_code": exit_code,
            "meaning": "Actual exit is separate from recording completeness; original failed attempt is never relabeled."}


def resource_inputs(e):
    m = base_module()
    rows = {}
    for name, sha in RESOURCE_PINS.items():
        row = e.identity(TOOLS / name, not name.startswith("target/"))
        m.require(row["sha256"] == sha, "resource-profile tool/provenance drift: " + name)
        rows[name] = row
    provenance = e.json(TOOLS / "source-provenance-r1.json")
    m.require(provenance["base_commit"] == "68d5ca9db226849b41a6fff59d796ff19d0a8840"
              and provenance["tracked_files"] == 29 and provenance["only_changed"] == ["src/lib.rs"]
              and provenance["source_input_set_exact"] is True and provenance["hardlinks_used"] is False,
              "resource source scope differs")
    names = []
    for row in provenance["original_before"]:
        name = row["relative_path"]; names.append(name)
        e.bind(row["original"], m.TOOLS / "nanoda-source" / name)
    for row in provenance["copy_after"]:
        e.bind(row["copy_after"], TOOLS / "source" / row["relative_path"])
    actual = sorted(str(p.relative_to(TOOLS / "source")) for p in (TOOLS / "source").rglob("*") if p.is_file())
    m.require(len(set(names)) == 29 and actual == sorted(names)
              and not any(p.is_symlink() for p in (TOOLS / "source").rglob("*")), "resource source input set differs")
    for row in provenance["preserved"].values(): e.bind(row, Path(row["path"]))
    manifest = e.json(TOOLS / "tool-manifest-r1.json")
    e.bind(manifest["binaries"]["nanoda"], RESOURCE_BINARY)
    build = e.json(TOOLS / "build-result-r1.json")
    e.bind(build["new_binary"], RESOURCE_BINARY)
    m.require(build["status"] == "passed" and build["exit_code"] == 0
              and build["original_source_binary_recorder_manifest_unchanged"] is True,
              "resource build did not close normally")
    return rows


def retry_environment(folder, python):
    env = base_module().phase_environment("extra-nanoda", folder, python)
    env["NANODA_REAL_BINARY"] = str(RESOURCE_BINARY)
    value = os.environ[CF_KEY]
    base_module().require(hashlib.sha256(value.encode()).hexdigest() == CF_VALUE_SHA256,
                          "unexpected macOS runtime metadata hash")
    env[CF_KEY] = value
    return env


def child(folder):
    m = base_module(); folder = retry_folder(folder); e = m.Evidence()
    inputs = e.json(folder / "retry-inputs.json")
    m.require(inputs["protocol_variant"] == PROTOCOL and inputs["base_r2_input_fingerprint"] == BASE_FP
              and inputs["resource_policy"] == RESOURCE_POLICY and dict(os.environ) == inputs["environment"],
              "child resource protocol/environment differs")
    e.bind(inputs["retry_source"], Path(__file__))
    m.require(inputs["resource_inputs"] == resource_inputs(e), "resource input bindings changed")
    config = folder / "additional-nanoda-config.json"
    m.require(strict_policy_matches(e.json(config), inputs["export_input"], 2), "child strict original policy differs")
    before = list(resource.getrlimit(resource.RLIMIT_STACK))
    after = list(resource.getrlimit(resource.RLIMIT_STACK))
    m.require(before == after, "main stack limits changed")
    actual = {"schema": "native-nanoda-worker-resource/2", "protocol_variant": PROTOCOL,
              "pid": os.getpid(), "pgid": os.getpgrp(), "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "retry_source": e.identity(Path(__file__)), "resource_policy": RESOURCE_POLICY,
              "resource_inputs": inputs["resource_inputs"],
              "main_stack_limits_before": before, "main_stack_limits_after": after,
              "main_stack_limits_changed": False, "actual_nanoda_worker_extent_measured": False,
              "environment": dict(os.environ), "environment_keys": sorted(os.environ),
              "exec_argv": [sys.executable, str(RESOURCE_RECORDER), str(config)], "cwd": os.getcwd()}
    m.write_json(folder / "worker-resource.json", actual)
    print("WORKER_RESOURCE " + json.dumps(actual, sort_keys=True), flush=True)
    os.execve(sys.executable, actual["exec_argv"], dict(os.environ))


def interrupted(signum, frame):
    global INTERRUPTED
    INTERRUPTED = signum
    signal.signal(signal.SIGINT, signal.SIG_IGN); signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise KeyboardInterrupt("resource retry interrupted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--record-directory", type=Path)
    parser.add_argument("--export-phase", type=Path)
    parser.add_argument("--failed-phase", type=Path)
    parser.add_argument("--failed-outer-receipt", type=Path)
    parser.add_argument("--fresh-phase", type=Path)
    args = parser.parse_args()
    if args.child is not None:
        return child(args.child)
    if not all([args.record_directory, args.export_phase, args.failed_phase, args.failed_outer_receipt, args.fresh_phase]):
        parser.error("supply explicit new retry directory, successful export/fresh and original failed phase/outer receipt")
    m = base_module(); e = m.Evidence(); folder = retry_folder(args.record_directory)
    folder.mkdir(parents=True, exist_ok=False)
    result = {"schema": "openai-native-resource-retry/1", "protocol_variant": PROTOCOL,
              "logical_check": "extra-nanoda", "status": "failed", "record_directory": str(folder),
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "original_r2_attempt_passed": False, "resource_policy": RESOURCE_POLICY}
    m.write_json(folder / "retry-prepared.json", result)
    recorder = None; code = 125
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    try:
        content, fp, _ = m.pinned_inputs(e)
        m.require(fp == BASE_FP, "original R2 inputs changed")
        successful_export = m.closed_phase(e, "selected-export", args.export_phase, content, fp)
        export = m.export_phase(e, successful_export)
        m.require(export["sha256"] == "bdbc9afe336fea99b01bc4eced6e4232153afdefe13a1095cdc5ca9499e3f573"
                  and export["size_bytes"] == 2355666449, "different selected export supplied")
        failure = failed_attempt(e, args.failed_phase, args.failed_outer_receipt, content, export)
        fresh = m.closed_phase(e, "original-fresh", args.fresh_phase, content, fp)
        m.require(failure["end"] <= fresh["start"] and fresh["end"] <= datetime.datetime.now().timestamp(),
                  "original fresh must close after failure and before retry starts")
        config = policy(export, 2)
        original = e.json(Path(failure["directory"]) / "additional-nanoda-config.json")
        m.require(original == config, "resource retry changes strict original config")
        m.write_json(folder / "additional-nanoda-config.json", config)
        resource_rows = resource_inputs(e)
        env = retry_environment(folder, sys.executable)
        (folder / "home").mkdir(); (folder / "tmp").mkdir()
        argv = [sys.executable, str(Path(__file__).resolve()), "--child", str(folder)]
        inputs = {"schema": "openai-native-resource-retry-inputs/1", "protocol_variant": PROTOCOL,
                  "base_r2_input_fingerprint": fp, "selected_inputs": content,
                  "retry_source": e.identity(Path(__file__)), "resource_policy": RESOURCE_POLICY,
                  "resource_inputs": resource_rows,
                  "export_input": export, "failed_attempt": failure,
                  "fresh_phase_result": e.identity(Path(fresh["directory"]) / "phase-result.json"),
                  "fresh_directory": fresh["directory"], "argv": argv, "cwd": str(m.WORKSPACE),
                  "environment": env, "environment_keys": sorted(env), "timeout_seconds": 7200,
                  "config_delta": {}}
        m.write_json(folder / "retry-inputs.json", inputs)
        spec = importlib.util.spec_from_file_location("retry_frozen_recorder", BASE / "native-recorder-r1/record.py")
        rec = importlib.util.module_from_spec(spec); spec.loader.exec_module(rec)
        recorder = rec.Recorder(folder / "stages")
        receipt = recorder.run(STAGE, argv, m.WORKSPACE, env, timeout=7200)
        nano = nano_records(e, folder, export, 2, 0)
        actual = e.json(folder / "worker-resource.json", True)
        m.require(actual["main_stack_limits_before"] == actual["main_stack_limits_after"]
                  and actual["main_stack_limits_changed"] is False and actual["resource_policy"] == RESOURCE_POLICY
                  and actual["environment"] == env and actual["resource_inputs"] == resource_rows
                  and actual["retry_source"] == inputs["retry_source"], "actual child resource/env differs")
        e.stable()
        result.update(status="passed", base_r2_input_fingerprint=fp,
                      retry_inputs=e.identity(folder / "retry-inputs.json"), failed_attempt=failure,
                      worker_resource=e.identity(folder / "worker-resource.json"), nanoda=nano,
                      stage_finished=e.identity(folder / "stages" / STAGE / "finished.json"))
        code = 0
    except BaseException as error:
        result["error"] = type(error).__name__ + ": " + str(error)
        if isinstance(error, subprocess.CalledProcessError):
            code = error.returncode if 0 < error.returncode < 256 else 125
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN); signal.signal(signal.SIGINT, signal.SIG_IGN)
        result.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      interrupt_signal=INTERRUPTED, stage_receipts=recorder.receipts if recorder else [])
        if INTERRUPTED is not None:
            result["status"] = "failed"; code = 128 + INTERRUPTED
        m.write_json(folder / "retry-result.json", result)
        print(json.dumps(result, sort_keys=True), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
