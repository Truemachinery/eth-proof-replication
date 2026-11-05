#!/usr/bin/env python3
"""Synthetic transport/acceptance guards only; never run Lean or a checker."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication_guard", ROOT / "publish_package.py")
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)
MAP = "publication/native-final-selection-r1.json"


def fixture(base):
    base = base.resolve()
    def write(name, value):
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else (json.dumps(value, indent=2) + "\n").encode())
    def identity(name):
        data = (base / name).read_bytes()
        return {"path": str((base / name).resolve()), "sha256": pub.sha(data), "size_bytes": len(data)}
    selected = {"launcher": {"sha256": "fe3b12c0b8312a6b0cdb5ec1c6d88933cbff796bc92e9403682735d25348c19c"}}
    fingerprint = pub.sha(json.dumps(selected, sort_keys=True, separators=(",", ":")).encode())
    write(pub.NATIVE_AGGREGATOR, (ROOT / pub.NATIVE_AGGREGATOR).read_bytes())
    for phase, folder in pub.NATIVE_DIRS.items():
        stage = folder + "/stages/" + phase
        inputs = {"phase": phase, "selected_inputs": selected, "input_fingerprint": fingerprint,
                  "argv": ["synthetic-only"], "cwd": str(base), "timeout_seconds": 1}
        start = {"schema": "eth-ci-stage/1", "name": phase, "argv": inputs["argv"],
                 "cwd": str(base), "timeout_seconds": 1, "stdout_is_export": False}
        write(stage + "/prepared.json", start); write(stage + "/raw.log", b"synthetic only\n")
        finished = {**start, "exit_code": 0, "reason": None, "raw_log_sha256": identity(stage + "/raw.log")["sha256"],
                    "raw_log_bytes": identity(stage + "/raw.log")["size_bytes"]}
        write(stage + "/finished.json", finished); write(folder + "/phase-inputs.json", inputs)
        prepared = {"schema": "openai-native-phase/1", "phase": phase, "status": "failed",
                    "record_directory": str(base / folder), "started_utc": "2026-11-05T00:00:00Z"}
        write(folder + "/phase-prepared.json", prepared)
        write(folder + "/phase-result.json", {**prepared, "status": "passed", "finished_utc": "2026-11-05T00:00:01Z",
              "interrupt_signal": None, "input_fingerprint": fingerprint, "phase_inputs": identity(folder + "/phase-inputs.json"),
              "stage_finished": identity(stage + "/finished.json"), "stage_receipts": [finished]})
    export_folder = pub.NATIVE_DIRS["selected-export"]
    export = {"path": str(base / export_folder / "selected-solution.ndjson"), "sha256": "a" * 64, "size_bytes": 123}
    write(export_folder + "/export-capture.json", {"schema": "native-direct-fd-export/2", "complete": True,
          "child_exit_code": 0, "export": export})
    mutate = json.loads((base / export_folder / "phase-result.json").read_text())
    mutate.update(export=export, capture_receipt=identity(export_folder + "/export-capture.json"))
    write(export_folder + "/phase-result.json", mutate)
    nano_folder = pub.NATIVE_DIRS["extra-nanoda"]; directory = nano_folder + "/nanoda-records/nanoda-synthetic"
    policy = {"use_stdin": False, "export_file_path": export["path"], "permitted_axioms": ["propext", "Quot.sound", "Classical.choice"],
              "unpermitted_axiom_hard_error": True, "num_threads": 2, "nat_extension": True, "string_extension": True}
    write(nano_folder + "/additional-nanoda-config.json", policy); write(directory + "/effective-config.json", policy)
    archive = {"path": str(base / directory / "export.ndjson.gz"), "sha256": "b" * 64, "size_bytes": 77}
    zero = {"effective_policy": policy, "checker_argv": ["synthetic-only"], "started_at": "2026-11-05T00:00:00Z"}
    write(directory + "/00-prepared.json", zero); write(directory + "/01-started.json", {"checker_argv": zero["checker_argv"]})
    two = {**zero, "finished_at": "2026-11-05T00:00:01Z", "recording_complete": True, "inputs_unchanged": True,
           "checker_exit_code": 0, "wrapper_exit_code": 0, "policy_changes_by_recorder": False,
           "export_before": export, "export_after": export, "config_archive": identity(directory + "/effective-config.json"),
           "export_archive": {"uncompressed_sha256": export["sha256"], "uncompressed_size_bytes": export["size_bytes"], "gzip": archive}}
    write(directory + "/02-finished.json", two)
    mutate = json.loads((base / nano_folder / "phase-result.json").read_text())
    mutate["nanoda"] = {"finished_receipt": identity(directory + "/02-finished.json"), "gzip": archive,
                         "small_records": [identity(directory + "/" + n) for n in ["00-prepared.json", "01-started.json", "02-finished.json", "effective-config.json"]]}
    write(nano_folder + "/phase-result.json", mutate)
    build_name = "openai/logs/synthetic-source-closure.json"; build_raw = "openai/logs/source-build-gated-r4.txt"
    write(build_raw, b"Build completed successfully (1 jobs).\n")
    write(build_name, {"final_exec_exit_code": 0, "exec_session_id": 11317, "checkpoint_run_result":
          {"exit_code": 0, "timed_out": False, "log_sha256": identity(build_raw)["sha256"], "log_size": identity(build_raw)["size_bytes"]}})
    aggregate = {"format": "openai-eth-native-replication-result-v1", "all_required_native_checks_passed": True,
                 "verbatim_upstream_linux_ci_reproduction": False, "selected_input_fingerprint": fingerprint,
                 "selected_inputs": selected, "artifacts": [], "public_small_artifacts": [],
                 "additional_nanoda": {"actual_export": export, "retained_gzip": archive},
                 "source_build": {"receipt": identity(build_name), "raw": identity(build_raw)}, "phases": []}
    for phase, folder in pub.NATIVE_DIRS.items():
        result = json.loads((base / folder / "phase-result.json").read_text())
        aggregate["phases"].append({"name": phase, "directory": str(base / folder), "result": identity(folder + "/phase-result.json"), "stage": result["stage_receipts"][0]})
    write(pub.NATIVE_AGGREGATE + "/native-replication-result.json", aggregate)
    write(pub.NATIVE_AGGREGATE + "/native-replication-artifacts.json", {"artifacts": [], "public_small_artifacts": []})
    write(pub.NATIVE_AGGREGATE + "/report.md", b"Synthetic fixture, no proof execution.\n")
    write(pub.NATIVE_AGGREGATE + "/aggregation-prepared.json", {"schema": "openai-native-aggregation/1", "proof_execution": False, "aggregator": identity(pub.NATIVE_AGGREGATOR)})
    def reseal():
        write(pub.NATIVE_AGGREGATE + "/aggregation-finished.json", {"schema": "openai-native-aggregation/1", "status": "passed", "result": identity(pub.NATIVE_AGGREGATE + "/native-replication-result.json")})
        write(MAP, {"schema": "eth-native-final-selection/1", "aggregate_directory": pub.NATIVE_AGGREGATE,
                    "aggregate_files": {n: identity(pub.NATIVE_AGGREGATE + "/" + n) for n in pub.NATIVE_AGGREGATE_FILES}, "reviews": []})
    reseal()
    return write, identity, reseal


def main():
    started, cpu = time.monotonic(), time.process_time(); checks = []
    with tempfile.TemporaryDirectory(prefix="eth-final-native-guards-") as temporary:
        root = Path(temporary).resolve()
        base = root / "valid"; fixture(base)
        selected = pub.native_final_selection(base, MAP)
        assert len([n for n in selected["files"] if n.endswith("/phase-result.json")]) == 8
        assert not any(p.suffix in {".ndjson", ".gz"} for p in base.rglob('*'))
        checks += ["complete synthetic eight-phase selection accepted", "missing large assets are not read or copied"]
        plan = pub.make_plan(base, [], native_final_map=MAP)
        exported = pub.export_plan(base, plan, "synthetic-only")
        assert (base / exported["release"] / "PUBLIC_MANIFEST.json").is_file()
        checks.append("synthetic plan and export preserve native evidence classes")
        cases = ["no seal", "failed seal", "missing phase", "failed phase", "raw drift", "wrong raw size", "boolean exit",
                 "interrupted", "input drift", "bad capture", "nanoda failure", "nanoda export mismatch", "bad config", "gzip lineage", "outside review"]
        for i, case in enumerate(cases):
            base = root / str(i); write, identity, reseal = fixture(base)
            trace = pub.NATIVE_DIRS["trace"]
            if case == "no seal": (base / pub.NATIVE_AGGREGATE / "aggregation-finished.json").unlink()
            elif case == "missing phase": (base / trace / "phase-result.json").unlink()
            elif case == "raw drift": write(trace + "/stages/trace/raw.log", b"changed\n")
            else:
                target = pub.NATIVE_AGGREGATE + "/aggregation-finished.json" if case == "failed seal" else trace + "/phase-result.json"
                if case in {"wrong raw size", "boolean exit"}: target = trace + "/stages/trace/finished.json"
                if case == "input drift": target = trace + "/phase-inputs.json"
                if case == "bad capture": target = pub.NATIVE_DIRS["selected-export"] + "/export-capture.json"
                if case in {"nanoda failure", "nanoda export mismatch", "gzip lineage"}: target = pub.NATIVE_DIRS["extra-nanoda"] + "/nanoda-records/nanoda-synthetic/02-finished.json"
                if case == "bad config": target = pub.NATIVE_DIRS["extra-nanoda"] + "/additional-nanoda-config.json"
                if case == "outside review": target = MAP
                d = json.loads((base / target).read_text())
                if case == "failed seal": d["status"] = "failed"
                elif case == "failed phase": d["status"] = "failed"
                elif case == "wrong raw size": d["raw_log_bytes"] += 1
                elif case == "boolean exit": d["exit_code"] = True
                elif case == "interrupted": d["interrupt_signal"] = 15
                elif case == "input drift": d["input_fingerprint"] = "0" * 64
                elif case == "bad capture": d["complete"] = False
                elif case == "nanoda failure": d["checker_exit_code"] = 1
                elif case == "nanoda export mismatch": d["export_archive"]["uncompressed_sha256"] = "c" * 64
                elif case == "bad config": d["unpermitted_axiom_hard_error"] = False
                elif case == "gzip lineage": d["export_archive"]["gzip"]["sha256"] = "c" * 64
                elif case == "outside review": d["reviews"] = [{"path": "private-notes.md", "sha256": "d" * 64, "size_bytes": 1}]
                write(target, d)
                if case == "failed seal":
                    mapping = json.loads((base / MAP).read_text()); mapping["aggregate_files"]["aggregation-finished.json"] = identity(target); write(MAP, mapping)
            try: pub.native_final_selection(base, MAP)
            except (ValueError, OSError, KeyError): checks.append(case + " rejected")
            else: raise AssertionError(case + " accepted")
        try: pub.relative_path("openai/native-phase-records/r2-02-trace/stages/trace/live.raw.log")
        except ValueError: checks.append("unnamed live raw log rejected")
        else: raise AssertionError("live log accepted")
    report = {"schema": "eth-final-native-guard-controls/1", "status": "passed", "synthetic_only": True,
              "no_lean_checker_network_or_real_evidence_execution": True, "checks": checks,
              "publisher_sha256": pub.sha((ROOT / "publish_package.py").read_bytes()),
              "control_source_sha256": pub.sha(Path(__file__).read_bytes()),
              "cpu_seconds": time.process_time() - cpu, "wall_seconds": time.monotonic() - started}
    pub.save(ROOT / "publication/final-native-guard-control-result-r1.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
