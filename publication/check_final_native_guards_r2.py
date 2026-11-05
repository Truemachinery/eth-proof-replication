#!/usr/bin/env python3
"""Coherently rebound synthetic negatives; no real verifier or proof work."""
import importlib.util
import json
from pathlib import Path
import tempfile
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fixture_r1", HERE / "check_final_native_guards_r1.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
pub = fixture.pub


def main():
    started, cpu = time.monotonic(), time.process_time(); checks = []
    cases = ["boolean exit", "nonzero exit", "reason", "timeout", "raw size", "raw hash", "preparation argv",
             "phase failed", "phase interrupted", "phase open interval", "selected-input fingerprint"]
    with tempfile.TemporaryDirectory(prefix="eth-native-rebound-") as temporary:
        root = Path(temporary).resolve()
        for i, case in enumerate(cases):
            base = root / str(i); write, identity, reseal = fixture.fixture(base)
            folder = pub.NATIVE_DIRS["trace"]; stage = folder + "/stages/trace"
            result = json.loads((base / folder / "phase-result.json").read_text())
            finished = json.loads((base / stage / "finished.json").read_text())
            if case == "boolean exit": finished["exit_code"] = True
            elif case == "nonzero exit": finished["exit_code"] = 1
            elif case == "reason": finished["reason"] = "synthetic failure"
            elif case == "timeout": finished["timed_out"] = True
            elif case == "raw size": finished["raw_log_bytes"] += 1
            elif case == "raw hash": finished["raw_log_sha256"] = "e" * 64
            elif case == "preparation argv":
                begin = json.loads((base / stage / "prepared.json").read_text()); begin["argv"] = ["other-synthetic"]
                write(stage + "/prepared.json", begin)
            elif case == "phase failed": result["status"] = "failed"
            elif case == "phase interrupted": result["interrupt_signal"] = 15
            elif case == "phase open interval": result.pop("finished_utc")
            elif case == "selected-input fingerprint":
                inputs = json.loads((base / folder / "phase-inputs.json").read_text()); inputs["input_fingerprint"] = "e" * 64
                write(folder + "/phase-inputs.json", inputs); result["phase_inputs"] = identity(folder + "/phase-inputs.json")
            write(stage + "/finished.json", finished)
            result["stage_receipts"] = [finished]; result["stage_finished"] = identity(stage + "/finished.json")
            write(folder + "/phase-result.json", result)
            try: pub.completed_receipt(base, folder + "/phase-result.json")
            except (ValueError, KeyError): checks.append("coherently rebound " + case + " rejected")
            else: raise AssertionError(case + " accepted")
        base = root / "missing-eight"; write, identity, reseal = fixture.fixture(base)
        name = pub.NATIVE_AGGREGATE + "/native-replication-result.json"
        result = json.loads((base / name).read_text()); result["phases"].pop(); write(name, result); reseal()
        try: pub.native_final_selection(base, fixture.MAP)
        except ValueError as error:
            assert "eight explicit phases" in str(error); checks.append("hash-valid final aggregate missing one phase rejected")
        else: raise AssertionError("seven-phase aggregate accepted")
        base = root / "after-plan"; write, identity, reseal = fixture.fixture(base)
        plan = pub.make_plan(base, [], native_final_map=fixture.MAP)
        (base / pub.NATIVE_DIRS["post-identity"] / "phase-result.json").unlink()
        try: pub.export_plan(base, plan, "must-not-exist")
        except (ValueError, OSError):
            assert not (base / "publication/must-not-exist").exists(); checks.append("post-plan phase loss refused before destination creation")
        else: raise AssertionError("post-plan loss accepted")
    report = {"schema": "eth-final-native-guard-controls/2", "status": "passed", "synthetic_only": True,
              "coherent_reference_rebinding": True, "no_lean_checker_network_or_real_evidence_execution": True,
              "checks": checks, "publisher_sha256": pub.sha((HERE.parent / "publish_package.py").read_bytes()),
              "control_source_sha256": pub.sha(Path(__file__).read_bytes()),
              "fixture_source_sha256": pub.sha((HERE / "check_final_native_guards_r1.py").read_bytes()),
              "cpu_seconds": time.process_time() - cpu, "wall_seconds": time.monotonic() - started}
    pub.save(HERE / "final-native-guard-control-result-r2.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
