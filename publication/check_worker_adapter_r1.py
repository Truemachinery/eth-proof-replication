#!/usr/bin/env python3
"""Tiny adapter-only export controls with a substituted trusted metadata gate.

This tests omission/refreeze wiring and privacy on fake evidence, not the real
gate's acceptance semantics. No running proof directory is read or modified.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy
import importlib.util
import json
import tempfile
import time

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publisher_adapter_controls", BASE / "publish_package.py")
pub = importlib.util.module_from_spec(spec); spec.loader.exec_module(pub)


def main():
    start, cpu = time.monotonic(), time.process_time(); checks = []
    with tempfile.TemporaryDirectory(prefix="eth-adapter-control-") as temp:
        base = Path(temp).resolve()
        map_name = "publication/native-final-selection-r1.json"
        files, bindings, bundles, receipts = {map_name: "manifest"}, {}, {}, {}
        def put(name, data):
            p = base / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
        put(map_name, b'{"schema":"synthetic-adapter-map"}\n')
        for i, name in enumerate(sorted(pub.NATIVE_POSITIVE_RESULTS)):
            if name == pub.NATIVE_RETRY_RESULT:
                raw = pub.NATIVE_RETRY_DIR + "/stages/worker-stack256-nanoda/raw.log"
            else:
                phase = pub.NATIVE_RESULTS[name]; raw = pub.NATIVE_DIRS[phase] + "/stages/" + phase + "/raw.log"
            prepared = str(Path(name).parent / "adapter-prepared.json")
            payload = ("synthetic successful stage " + str(i) + "\n").encode()
            put(name, b'{"exit_code":0,"timed_out":false}\n'); put(raw, payload); put(prepared, b"{}\n")
            files.update({name: "completed_receipt", raw: "completed_log", prepared: "manifest"})
            bindings[raw] = {"receipt": name, "exit_code": 0, "timed_out": False,
                             "raw_log_sha256": pub.sha(payload), "raw_log_bytes": len(payload)}
            bundles[name] = [name, raw, prepared]
            receipts[name] = ({"exit_code": 0, "timed_out": False}, [(raw, pub.sha(payload), len(payload))])
        failed = pub.NATIVE_DIRS["extra-nanoda"] + "/phase-result.json"
        negative_raw = pub.NATIVE_DIRS["extra-nanoda"] + "/stages/extra-nanoda/raw.log"
        put(failed, b'{"status":"failed","exit_code":-6}\n'); put(negative_raw, b"synthetic retained stack overflow\n")
        files.update({failed: "completed_receipt", negative_raw: "completed_log"})
        bindings[negative_raw] = {"receipt": failed, "exit_code": -6, "timed_out": False,
                                  "raw_log_sha256": pub.sha((base/negative_raw).read_bytes()), "raw_log_bytes": (base/negative_raw).stat().st_size}
        native = {"map": map_name, "map_sha256": pub.sha((base/map_name).read_bytes()), "files": files,
                  "closed_log_bindings": bindings,
                  "omitted_large_assets": [{"recorded_checker_accepted": True}, {"recorded_checker_accepted": False}],
                  "scope": "synthetic metadata gate for adapter controls only"}
        fake = SimpleNamespace(native_final_selection=lambda *_: copy.deepcopy(native))
        def completed(_, name):
            if name == failed:
                raise ValueError("failed original cannot enter positive completed_receipt path")
            return receipts[name]
        with patch.multiple(pub, REPORTS=set(), SOURCES=set(), MANIFESTS=set(), WORKFLOW_LOGS={}), \
             patch.object(pub, "native_worker_module", return_value=fake), \
             patch.object(pub, "completed_receipt", side_effect=completed), \
             patch.object(pub, "native_result_files", side_effect=lambda _, n: bundles[n]):
            plan = pub.make_plan(base, [], native_final_map=map_name)
            assert set(plan["receipt_paths"]) == pub.NATIVE_POSITIVE_RESULTS and failed not in plan["receipt_paths"]
            assert plan["completed_log_bindings"] == bindings
            checks.append("positive receipt list excludes retained original failure; all negative raw bindings retained")
            def refuse(label, mutate):
                changed = copy.deepcopy(plan); mutate(changed)
                try: pub.export_plan(base, changed, "refused-" + str(len(checks)))
                except ValueError: pass
                else: raise AssertionError(label)
                assert not (base/"publication"/("refused-"+str(len(checks)))).exists()
                checks.append(label)
            refuse("missing retained failure refused before destination", lambda p: p.update(items=[r for r in p["items"] if r["path"] != failed]))
            post = pub.NATIVE_DIRS["post-identity"] + "/phase-result.json"
            refuse("missing final post-identity receipt refused", lambda p: p["receipt_paths"].remove(post))
            prepared = bundles[post][-1]
            refuse("missing closed phase bundle member refused", lambda p: p.update(items=[r for r in p["items"] if r["path"] != prepared]))
            refuse("changed final gate snapshot refused", lambda p: p["native_final"].update(scope="forged"))
            refuse("changed negative log exit binding refused", lambda p: p["completed_log_bindings"][negative_raw].update(exit_code=0))
            refuse("failed original promoted to positive receipt refused", lambda p: p["receipt_paths"].append(failed))
            selected_raw = next(iter(bindings)); old = (base/selected_raw).read_bytes(); put(selected_raw, old+b"drift")
            refuse("raw drift after freeze refused", lambda p: None)
            put(selected_raw, old)
            result = pub.export_plan(base, plan, "synthetic-adapter-pass")
            manifest = json.loads((base/"publication/synthetic-adapter-pass/PUBLIC_MANIFEST.json").read_bytes())
            assert len(manifest["omitted_large_assets"]) == 2 and manifest["omitted_large_assets"][1]["recorded_checker_accepted"] is False
            checks.append("exclusive temporary synthetic export retains both accepted and failed asset metadata")
    report = {"schema": "eth-worker-publication-adapter-controls/1", "status": "passed", "checks": checks,
              "publisher_sha256": pub.sha((BASE/"publish_package.py").read_bytes()), "source_sha256": pub.sha(Path(__file__).read_bytes()),
              "cpu_seconds": time.process_time()-cpu, "wall_seconds": time.monotonic()-start,
              "scope": "Trusted gate substituted with fake closed metadata only; no proof/WIP files, large assets or actual R8 release"}
    pub.save(BASE/"publication/worker-adapter-control-result-r1.json", report)
    print(json.dumps({"status":"passed","checks":len(checks),"cpu_seconds":report["cpu_seconds"],"wall_seconds":report["wall_seconds"]}))


if __name__ == "__main__": main()
