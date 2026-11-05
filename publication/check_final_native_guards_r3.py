#!/usr/bin/env python3
"""Synthetic final-plan omission controls; no verifier or proof execution."""
import copy
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
    with tempfile.TemporaryDirectory(prefix="eth-native-selection-") as temporary:
        base = Path(temporary).resolve(); fixture.fixture(base)
        plan = pub.make_plan(base, [], native_final_map=fixture.MAP)
        exported = pub.export_plan(base, plan, "complete-fixture")
        assert (base / exported["release"] / "PUBLIC_MANIFEST.json").is_file()
        checks.append("complete synthetic final plan still exports")
        paths = [fixture.MAP, pub.NATIVE_AGGREGATE + "/aggregation-finished.json",
                 pub.NATIVE_DIRS["trace"] + "/phase-inputs.json", pub.NATIVE_DIRS["trace"] + "/stages/trace/raw.log",
                 pub.NATIVE_DIRS["trace"] + "/phase-result.json"]
        for i, path in enumerate(paths):
            modified = copy.deepcopy(plan); modified["items"] = [r for r in modified["items"] if r["path"] != path]
            name = "must-not-exist-" + str(i)
            try: pub.export_plan(base, modified, name)
            except ValueError as error:
                assert "omitted" in str(error) and not (base / "publication" / name).exists()
                checks.append("required selected evidence omission rejected: " + path)
            else: raise AssertionError("selected evidence omission accepted")
        modified = copy.deepcopy(plan); modified["receipt_paths"].remove(pub.NATIVE_DIRS["trace"] + "/phase-result.json")
        try: pub.export_plan(base, modified, "missing-receipt")
        except ValueError as error:
            assert "omitted" in str(error) and not (base / "publication/missing-receipt").exists()
            checks.append("native final receipt-list omission rejected")
        else: raise AssertionError("receipt omission accepted")
    report = {"schema": "eth-final-native-guard-controls/3", "status": "passed", "synthetic_only": True,
              "no_lean_checker_network_or_real_evidence_execution": True, "checks": checks,
              "publisher_sha256": pub.sha((HERE.parent / "publish_package.py").read_bytes()),
              "control_source_sha256": pub.sha(Path(__file__).read_bytes()),
              "cpu_seconds": time.process_time() - cpu, "wall_seconds": time.monotonic() - started}
    pub.save(HERE / "final-native-guard-control-result-r3.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
