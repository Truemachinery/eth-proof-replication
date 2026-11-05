#!/usr/bin/env python3
"""Synthetic metadata/adapter controls; no proof, running evidence, or export read.

Retry fixtures replace only the absolute-path-specific config hash and synthetic
CF-value hash in an in-memory module. Production source anchors stay unchanged.
The adapter fixture substitutes a trusted metadata gate to test selection wiring,
not that gate's proof semantics. Its tiny export is exclusive and temporary.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy
import importlib.util
import json
import os
import tempfile
import time

BASE = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


pub = load("publisher_worker_controls", BASE / "publish_package.py")
guard = load("worker_gate_controls", BASE / "publication/native_worker_guard_r1.py")


def main():
    start, cpu = time.monotonic(), time.process_time(); checks = []
    helper_bytes = (BASE / guard.HELPER).read_bytes()
    assert pub.sha(helper_bytes) == guard.HELPER_SHA
    def record(label, action, refuses=False):
        try: action()
        except (ValueError, KeyError, FileNotFoundError):
            if not refuses: raise
        else:
            if refuses: raise AssertionError("unexpected acceptance: " + label)
        checks.append(label)

    def retry_fixture(base, change=None):
        def path(n): return str(base / n)
        def put(n, value):
            raw = value if isinstance(value, bytes) else (json.dumps(value, indent=2) + "\n").encode()
            p = base / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
            return {"path": path(n), "sha256": pub.sha(raw), "size_bytes": len(raw)}
        def ref(n, digest, size=1): return {"path": path(n), "sha256": digest, "size_bytes": size}
        folder = guard.RETRY; phase = "worker-stack256-nanoda"
        export = ref(guard.EXPORT_NAME, guard.EXPORT_SHA, guard.EXPORT_SIZE)
        cfg = {"use_stdin": False, "export_file_path": export["path"], "permitted_axioms": ["propext", "Quot.sound", "Classical.choice"],
               "unpermitted_axiom_hard_error": True, "num_threads": 2, "nat_extension": True, "string_extension": True}
        policy = copy.deepcopy(guard.POLICY)
        model = {"status": "passed", "code": 0, "config": cfg, "policy": policy, "helper": helper_bytes,
                 "binary_sha": guard.BINARY_SHA, "export": export, "worker_changed": False, "recording_complete": True,
                 "timed_out": False, "raw_suffix": b"", "protocol": guard.PROTOCOL}
        if change: change(model)
        cfg_ref = put(folder + "/additional-nanoda-config.json", model["config"])
        source = put(guard.HELPER, model["helper"])
        pins = {n: ref(guard.TOOLS + "/" + n, h) for n, h in guard.PINS.items()}
        pins["target/release/nanoda_bin"] = ref(guard.BINARY, model["binary_sha"], 1260088)
        env = {guard.CF_KEY: "0xabc:0xdef:0x123", "NANODA_REAL_BINARY": path(guard.BINARY)}
        inputs = {"schema": "openai-native-resource-retry-inputs/1", "protocol_variant": model["protocol"],
                  "base_r2_input_fingerprint": guard.FP, "resource_policy": model["policy"], "export_input": model["export"],
                  "config_delta": {}, "retry_source": source, "resource_inputs": pins, "environment": env,
                  "environment_keys": sorted(env), "argv": ["/usr/bin/python3", path(guard.HELPER), "--child", path(folder)],
                  "cwd": path("openai/workspace"), "timeout_seconds": 7200}
        inputs_ref = put(folder + "/retry-inputs.json", inputs)
        worker = {"schema": "native-nanoda-worker-resource/2", "protocol_variant": model["protocol"],
                  "resource_policy": model["policy"], "resource_inputs": pins, "environment": env, "environment_keys": sorted(env),
                  "retry_source": source, "main_stack_limits_before": [123, 456], "main_stack_limits_after": [123, 456],
                  "main_stack_limits_changed": model["worker_changed"], "actual_nanoda_worker_extent_measured": False,
                  "pid": 12345, "pgid": 12345, "cwd": path("openai/workspace"),
                  "exec_argv": ["/usr/bin/python3", path(guard.TOOLS + "/record_nanoda.py"), cfg_ref["path"]]}
        worker_ref = put(folder + "/worker-resource.json", worker)
        raw = b"WORKER_RESOURCE " + json.dumps(worker).encode() + b"\n" + model["raw_suffix"]
        stage_path = folder + "/stages/" + phase
        prepared = {"schema": "eth-ci-stage/1", "name": phase, "argv": inputs["argv"], "cwd": inputs["cwd"],
                    "timeout_seconds": 7200, "stdout_is_export": False}
        put(stage_path + "/prepared.json", prepared); put(stage_path + "/raw.log", raw)
        stage = {**prepared, "exit_code": model["code"], "reason": None, "timed_out": model["timed_out"],
                 "raw_log_sha256": pub.sha(raw), "raw_log_bytes": len(raw)}
        stage_ref = put(stage_path + "/finished.json", stage)
        nr = folder + "/nanoda-records/nanoda-12345-synthetic"
        eff = put(nr + "/effective-config.json", model["config"])
        zero = put(nr + "/00-prepared.json", {})
        argv = [path(guard.BINARY), cfg_ref["path"]]
        one = put(nr + "/01-started.json", {"checker_argv": argv})
        gz = ref(nr + "/export.ndjson.gz", "f" * 64, 32)
        two = {"recording_complete": model["recording_complete"], "inputs_unchanged": True,
               "policy_changes_by_recorder": False, "checker_exit_code": model["code"], "wrapper_exit_code": model["code"],
               "effective_policy": model["config"], "checker_argv": argv,
               "wrapper_argv": [path(guard.TOOLS + "/record_nanoda.py"), cfg_ref["path"]],
               "mode": "native_fake_landrun_unsandboxed", "started_at": "2026-01-01T00:00:00Z", "finished_at": "2026-01-01T00:00:01Z",
               "binary_before": ref(guard.BINARY, model["binary_sha"], 1260088), "binary_after": ref(guard.BINARY, model["binary_sha"], 1260088),
               "export_before": model["export"], "export_after": model["export"], "config_before": cfg_ref, "config_after": cfg_ref,
               "config_archive": eff, "wrapper_source": ref(guard.TOOLS + "/record_nanoda.py", guard.RECORDER_SHA, 8494),
               "export_archive": {"uncompressed_sha256": model["export"]["sha256"], "uncompressed_size_bytes": model["export"]["size_bytes"], "gzip": gz}}
        two_ref = put(nr + "/02-finished.json", two)
        result = {"schema": "openai-native-resource-retry/1", "status": model["status"], "protocol_variant": model["protocol"],
                  "logical_check": "extra-nanoda", "original_r2_attempt_passed": False, "interrupt_signal": None,
                  "record_directory": path(folder), "base_r2_input_fingerprint": guard.FP, "resource_policy": model["policy"],
                  "started_utc": "2026-01-01T00:00:00Z", "finished_utc": "2026-01-01T00:00:01Z", "retry_inputs": inputs_ref,
                  "worker_resource": worker_ref, "stage_finished": stage_ref, "stage_receipts": [stage],
                  "nanoda": {"finished_receipt": two_ref, "small_records": [zero, one, two_ref, eff], "gzip": gz, "checker_exit_code": model["code"]}}
        put(folder + "/retry-prepared.json", {"started_utc": result["started_utc"], "protocol_variant": model["protocol"]})
        put(folder + "/retry-result.json", result)
        return cfg_ref["sha256"], pub.sha(env[guard.CF_KEY].encode())

    cases = [("closed synthetic retry accepted without asset/binary files", None, False),
             ("coherently rebound failed status refused", lambda m: m.update(status="failed"), True),
             ("coherently rebound checker nonzero refused", lambda m: m.update(code=-6), True),
             ("coherently rebound timeout refused", lambda m: m.update(timed_out=True), True),
             ("coherently rebound weakened axiom policy refused", lambda m: m["config"].update(unpermitted_axiom_hard_error=False), True),
             ("coherently rebound extra axiom refused", lambda m: m["config"]["permitted_axioms"].append("sorryAx"), True),
             ("coherently rebound thread change refused", lambda m: m["config"].update(num_threads=1), True),
             ("coherently rebound resource binary drift refused", lambda m: m.update(binary_sha="a" * 64), True),
             ("coherently rebound helper drift refused", lambda m: m.update(helper=helper_bytes+b"\n"), True),
             ("coherently rebound changed main stack refused", lambda m: m.update(worker_changed=True), True),
             ("coherently rebound missing completion refused", lambda m: m.update(recording_complete=False), True),
             ("coherently rebound old protocol refused", lambda m: m.update(protocol="openai-native-r2-nanoda-worker-stack256-r2"), True),
             ("duplicate raw worker event refused", lambda m: m.update(raw_suffix=b"WORKER_RESOURCE {}\n"), True)]
    for label, change, refuses in cases:
        with tempfile.TemporaryDirectory(prefix="eth-retry-guard-") as temp:
            base = Path(temp).resolve(); cfg_sha, cf_sha = retry_fixture(base, change)
            with patch.object(guard, "CONFIG_SHA", cfg_sha), patch.object(guard, "CF_SHA", cf_sha):
                record(label, lambda: guard.native_retry_bundle(base, guard.RETRY + "/retry-result.json", pub.native_publisher_api()), refuses)
            assert not (base / guard.EXPORT_NAME).exists() and not (base / guard.BINARY).exists()
    record("unnamed retry root refused", lambda: guard.native_retry_bundle(BASE, "openai/other/retry-result.json", pub.native_publisher_api()), True)
    record("unnamed Rust extension refused", lambda: pub.relative_path("publication/other.rs"), True)
    record("unnamed patch extension refused", lambda: pub.relative_path("publication/other.patch"), True)
    record("named Rust and patch accepted", lambda: [pub.relative_path(x) for x in pub.NAMED_PATCHES | pub.NAMED_RUST_SOURCES])
    record("original failed Nano is excluded from positive receipt set", lambda: (_ for _ in ()).throw(AssertionError()) if pub.NATIVE_DIRS["extra-nanoda"] + "/phase-result.json" in pub.NATIVE_POSITIVE_RESULTS else None)
    # Missing actual final data must refuse rather than inspect running retry files.
    with tempfile.TemporaryDirectory(prefix="eth-missing-final-") as temp:
        record("absent final map refused", lambda: guard.native_final_selection(Path(temp), "publication/native-final-selection-r1.json", pub.native_publisher_api()), True)
    report = {"schema": "eth-worker-publication-controls/1", "status": "passed", "checks": checks,
              "publisher_sha256": pub.sha((BASE / "publish_package.py").read_bytes()),
              "guard_sha256": pub.sha((BASE / "publication/native_worker_guard_r1.py").read_bytes()),
              "source_sha256": pub.sha(Path(__file__).read_bytes()), "cpu_seconds": time.process_time()-cpu,
              "wall_seconds": time.monotonic()-start,
              "scope": "Synthetic small metadata; fixture-only config-path/CF hashes, not production anchor substitutions; no proof, WIP evidence, binaries or large assets read"}
    pub.save(BASE / "publication/worker-publication-control-result-r1.json", report)
    print(json.dumps({"status": "passed", "checks": len(checks), "cpu_seconds": report["cpu_seconds"], "wall_seconds": report["wall_seconds"]}))


if __name__ == "__main__": main()
