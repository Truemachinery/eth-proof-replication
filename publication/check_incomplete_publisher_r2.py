#!/usr/bin/env python3
"""Small negative-route adapter fixtures; no real evidence or export copied.

The guard is replaced by a tiny, explicitly fake pinned module in a temporary
tree. This tests the real thin wrapper and unchanged a72 planner, not factual
closure validation. Export checks either refuse before mkdir or use a stub.
"""
from pathlib import Path
from unittest.mock import patch
import copy
import importlib.util
import json
import tempfile
import time

BASE = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


wrapper = load("incomplete_wrapper_fixture", BASE / "publish_native_incomplete_r1.py")


def main():
    start, cpu = time.monotonic(), time.process_time(); checks = []
    original_core = (BASE/wrapper.CORE).read_bytes()
    original_positive = (BASE/"publication/native_worker_guard_r1.py").read_bytes()
    assert wrapper.digest(original_core) == wrapper.CORE_SHA
    assert wrapper.digest(original_positive) == "68d3ef6d9e0c3d4ae436b2901f4ac483cfa49a5f65982ca07d7e56ea7a21c726"
    with tempfile.TemporaryDirectory(prefix="eth-incomplete-adapter-") as temporary:
        base = Path(temporary).resolve()
        def put(name, data):
            raw = data if isinstance(data, bytes) else (json.dumps(data, indent=2)+"\n").encode()
            p=base/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            return {"path":str(p),"sha256":wrapper.digest(raw),"size_bytes":len(raw)}
        put(wrapper.CORE, original_core)
        put("publish_native_incomplete_r1.py", (BASE/"publish_native_incomplete_r1.py").read_bytes())
        put("publication/native_worker_guard_r1.py", original_positive)
        positive = load("unchanged_a72_fixture", base/wrapper.CORE)
        files,logs={},{}
        selected={"launcher":{"sha256":"fe3b12c0b8312a6b0cdb5ec1c6d88933cbff796bc92e9403682735d25348c19c"}}
        fp=wrapper.digest(json.dumps(selected,sort_keys=True,separators=(",",":")).encode())
        originals={n:p for n,p in positive.NATIVE_RESULTS.items() if p!="extra-nanoda"}
        for name,phase in originals.items():
            folder=positive.NATIVE_DIRS[phase]; stage=folder+"/stages/"+phase
            inputs={"phase":phase,"selected_inputs":selected,"input_fingerprint":fp,"argv":["synthetic",phase],"cwd":str(base/"workspace"),"timeout_seconds":1}
            inp=put(folder+"/phase-inputs.json",inputs); raw=b"synthetic closed original stage\n"
            prep={"schema":"eth-ci-stage/1","name":phase,"argv":inputs["argv"],"cwd":inputs["cwd"],"timeout_seconds":1,"stdout_is_export":False}
            put(stage+"/prepared.json",prep);put(stage+"/raw.log",raw)
            done={**prep,"exit_code":0,"reason":None,"raw_log_sha256":wrapper.digest(raw),"raw_log_bytes":len(raw)}
            fin=put(stage+"/finished.json",done)
            result={"schema":"openai-native-phase/1","phase":phase,"status":"passed","interrupt_signal":None,
                    "record_directory":str(base/folder),"started_utc":"2026-01-01T00:00:00Z","finished_utc":"2026-01-01T00:00:01Z",
                    "input_fingerprint":fp,"phase_inputs":inp,"stage_finished":fin,"stage_receipts":[done]}
            put(name,result);put(folder+"/phase-prepared.json",{k:result[k] for k in ["schema","phase","record_directory","started_utc"]})
            for n in [name,folder+"/phase-inputs.json",folder+"/phase-prepared.json",stage+"/prepared.json",stage+"/finished.json",stage+"/raw.log"]:
                files[n]="completed_log" if n.endswith("raw.log") else "completed_receipt" if n==name else "manifest"
            logs[stage+"/raw.log"]={"receipt":name,"exit_code":0,"timed_out":False,"raw_log_sha256":wrapper.digest(raw),"raw_log_bytes":len(raw)}
        negative="openai/native-retry-records/worker-stack256-r3-02/retry-result.json"
        raw_name="openai/native-retry-records/worker-stack256-r3-02/stages/worker-stack256-nanoda/raw.log"
        put(negative,{"status":"failed","checker_exit_code":None});raw=b"synthetic cap reached\n";put(raw_name,raw)
        files.update({negative:"completed_receipt",raw_name:"completed_log"})
        logs[raw_name]={"receipt":negative,"exit_code":124,"timed_out":True,"raw_log_sha256":wrapper.digest(raw),"raw_log_bytes":len(raw)}
        helper="openai/nanoda_worker_stack_retry_r3.py";put(helper,b"# synthetic frozen helper\n");files[helper]="source"
        selection_name="publication/native-incomplete-selection-r1.json"
        files[selection_name]="manifest"
        state={"publication_mode":wrapper.MODE,"verdict":wrapper.VERDICT,"original_lean_suite_passed":True,
               "all_required_native_checks_passed":False,"expanded_suite_passed":False,
               "independent_nanoda_acceptance_observed":False,"independent_nanoda_accepted":None,
               "map":selection_name,"files":files,"closed_log_bindings":logs,"omitted_large_assets":[],
               "scope":"Synthetic trusted gate only; no real closure result"}
        put(selection_name,state)
        fake_source=b'''import json\ndef native_incomplete_selection(base,name,publisher):\n    if name != "publication/native-incomplete-selection-r1.json":\n        raise ValueError("wrong synthetic incomplete map")\n    result=json.loads(publisher.read_stable(base,name))\n    result["map_sha256"]=publisher.sha(publisher.read_stable(base,name))\n    return result\n'''
        put(wrapper.GUARD,fake_source)
        with patch.object(wrapper,"GUARD_SHA",wrapper.digest(fake_source)):
            envelope=wrapper.make_plan(base,selection_name)
            assert set(envelope["plan"]["receipt_paths"])==set(originals)
            assert negative not in envelope["plan"]["receipt_paths"]
            assert next(r for r in envelope["plan"]["items"] if r["path"]==helper)["kind"]=="source"
            checks.append("valid synthetic negative plan retains seven positive originals and source helper; failed Rust is not positive")
            def refuses(label,fn):
                try:fn()
                except (ValueError,KeyError):pass
                else:raise AssertionError(label)
                checks.append(label)
            for label,change in [
                ("expanded PASS refused",lambda p:p.update(expanded_suite_passed=True)),
                ("observed Rust acceptance refused",lambda p:p.update(independent_nanoda_acceptance_observed=True)),
                ("checker acceptance true refused",lambda p:p.update(independent_nanoda_accepted=True)),
                ("unknown acceptance field omitted refused",lambda p:p.pop("independent_nanoda_accepted")),
                ("original suite missing refused",lambda p:p.update(original_lean_suite_passed=False)),
                ("all-checks PASS refused",lambda p:p.update(all_required_native_checks_passed=True))]:
                changed=copy.deepcopy(state);change(changed);put(selection_name,changed)
                refuses(label,lambda:wrapper.make_plan(base,selection_name))
            put(selection_name,state)
            refuses("failed Rust added as positive receipt refused",lambda:wrapper.make_plan(base,selection_name,[negative]))
            refuses("negative map refused by unchanged positive worker gate",lambda:positive.native_final_selection(base,selection_name))
            def export_refuses(label,mutate):
                changed=copy.deepcopy(envelope);mutate(changed)
                refuses(label,lambda:wrapper.export_plan(base,changed,"must-not-exist"))
                assert not(base/"publication/must-not-exist").exists()
            export_refuses("wrong outer plan route refused",lambda p:p.update(schema="eth-public-export/1"))
            export_refuses("changed reviewed source pin refused",lambda p:p.update(publisher_sha256="a"*64))
            export_refuses("wrapper source omitted refused",lambda p:p["plan"].update(items=[r for r in p["plan"]["items"] if r["path"]!="publish_native_incomplete_r1.py"]))
            export_refuses("missing postidentity positive receipt refused",lambda p:p["plan"]["receipt_paths"].remove(positive.NATIVE_DIRS["post-identity"]+"/phase-result.json"))
            export_refuses("retained terminal negative omitted refused",lambda p:p["plan"].update(items=[r for r in p["plan"]["items"] if r["path"]!=negative]))
            export_refuses("retained terminal binding promoted refused",lambda p:p["plan"]["completed_log_bindings"][raw_name].update(exit_code=0))
            # Trace a valid outer dispatch without executing the copy/export code.
            core=wrapper.private_adapter(base)
            with patch.object(core,"export_plan",return_value={"status":"synthetic-dispatch-only"}) as call,patch.object(wrapper,"private_adapter",return_value=core):
                result=wrapper.export_plan(base,envelope,"not-created")
                assert result["status"]=="synthetic-dispatch-only" and call.call_count==1
            assert not(base/"publication/not-created").exists()
            checks.append("valid negative route dispatch preserves incomplete status without executing export")
        assert (base/wrapper.CORE).read_bytes()==original_core
        assert (base/"publication/native_worker_guard_r1.py").read_bytes()==original_positive
    assert (BASE/wrapper.CORE).read_bytes()==original_core
    assert (BASE/"publication/native_worker_guard_r1.py").read_bytes()==original_positive
    checks.append("positive a72 publisher and68 guard remain byte-identical")
    report={"schema":"eth-incomplete-publisher-adapter-controls/1","status":"passed","checks":checks,
            "wrapper_sha256":wrapper.digest((BASE/"publish_native_incomplete_r1.py").read_bytes()),"source_sha256":wrapper.digest(Path(__file__).read_bytes()),
            "positive_publisher_sha256":wrapper.CORE_SHA,"scope":"Synthetic trusted metadata gate substituted in temporary files; no factual guard validation, real evidence, checker, network or export copy",
            "cpu_seconds":time.process_time()-cpu,"wall_seconds":time.monotonic()-start}
    p=BASE/"publication/incomplete-publisher-control-result-r2.json"
    with p.open("x") as f:f.write(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":"passed","checks":len(checks),"cpu_seconds":report["cpu_seconds"],"wall_seconds":report["wall_seconds"]}))


if __name__=="__main__":main()
