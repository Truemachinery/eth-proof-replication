#!/usr/bin/env python3
"""Small real-gate header/refusal controls, not a synthetic proof acceptance.

Complete hash-bound fake closure headers are rebound after each mutation. They
deliberately contain no original phase rows; a correctly labelled header alone
must still fail the seven-original check. No campaign or large file is read.
"""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import time
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


pub=load("incomplete_controls_original_publisher",BASE/"publish_package.py")
gate=load("incomplete_controls_real_gate",BASE/"publication/native_interrupted_guard_r1.py")


def main():
    start,cpu=time.monotonic(),time.process_time();checks=[]
    source_bytes={n:(BASE/n).read_bytes() for n in [gate.HELPERS,"publication/native_worker_guard_r1.py",gate.CLOSURE_SOURCE,"openai/aggregate_native_result_r7.py"]}
    assert pub.sha(source_bytes[gate.HELPERS])==gate.HELPERS_SHA
    assert pub.sha(source_bytes[gate.CLOSURE_SOURCE])==gate.CLOSURE_SHA
    def run_case(label,target,change,expected):
        with tempfile.TemporaryDirectory(prefix="eth-negative-header-") as temporary:
            base=Path(temporary).resolve()
            def put(name,value):
                raw=value if isinstance(value,bytes) else (json.dumps(value,indent=2)+"\n").encode()
                p=base/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
                return {"path":str(p),"sha256":pub.sha(raw),"size_bytes":len(raw)}
            for n,raw in source_bytes.items():put(n,raw)
            source=put(gate.CLOSURE_SOURCE,source_bytes[gate.CLOSURE_SOURCE])
            claims={"schema":gate.SCHEMA,"verdict":gate.VERDICT,"original_lean_suite_passed":True,
                    "all_required_native_checks_passed":False,"expanded_suite_passed":False,"original_r2_protocol_passed":False,
                    "additional_nanoda_verification":"INTERRUPTED","independent_nanoda_acceptance_observed":False,
                    "independent_nanoda_accepted":None,"checker_exit_code":None,
                    "input_fingerprint":"c84c8907998f23cc282a29ae7fef4a37cbaff735327096e748afe546af8c4f52",
                    "artifacts":[],"public_small_artifacts":[],"original_seven_phase_results":[],"resource_use":{"interrupted_attempt_final_child_cpu_seconds":None,"interrupted_attempt_final_wall_seconds":None,"total_campaign_final_child_cpu_seconds":None,"total_campaign_final_wall_seconds":None}}
            selection={"schema":"eth-native-interrupted-selection/1","aggregate_directory":gate.DIRECTORY,
                       "publication_mode":gate.MODE,"verdict":gate.VERDICT,
                       "original_lean_suite_passed":True,"expanded_suite_passed":False,"all_required_native_checks_passed":False,
                       "original_r2_protocol_passed":False,"independent_nanoda_acceptance_observed":False,
                       "independent_nanoda_accepted":None,"checker_exit_code":None,"additional_nanoda_verification":"INTERRUPTED","interrupt_signal":15,"attempt_timed_out":False,"final_attempt_cpu_seconds":None,"final_attempt_wall_seconds":None}
            closing={"schema":gate.SCHEMA,"status":"interrupted_evidence_closed","expanded_suite_passed":False}
            if target=="selection":change(selection)
            elif target=="result":change(claims)
            elif target=="closing":change(closing)
            elif target=="source":source=put(gate.CLOSURE_SOURCE,source_bytes[gate.CLOSURE_SOURCE]+b"\n")
            elif target=="metadata":put(gate.HELPERS,source_bytes[gate.HELPERS]+b"\n")
            outputs={}
            outputs["closure-prepared.json"]=put(gate.DIRECTORY+"/closure-prepared.json",{"schema":gate.SCHEMA,"status":"preparing_interrupted_closure","source":source,"proof_execution":False})
            outputs["native-interrupted-result.json"]=put(gate.DIRECTORY+"/native-interrupted-result.json",claims)
            outputs["native-interrupted-artifacts.json"]=put(gate.DIRECTORY+"/native-interrupted-artifacts.json",{"artifacts":[],"public_small_artifacts":[]})
            outputs["report.md"]=put(gate.DIRECTORY+"/report.md",b"Synthetic header only; expanded Rust incomplete\n")
            closing.update(result=outputs["native-interrupted-result.json"],report=outputs["report.md"],artifacts_manifest=outputs["native-interrupted-artifacts.json"])
            outputs["closure-finished.json"]=put(gate.DIRECTORY+"/closure-finished.json",closing)
            selection["aggregate_files"]=outputs
            name="publication/native-interrupted-selection-r1.json";put(name,selection)
            try:gate.native_interrupted_selection(base,name,pub.native_publisher_api())
            except ValueError as error:
                assert expected in str(error),(label,str(error))
            else:raise AssertionError("header accepted without required original evidence: "+label)
            checks.append(label)
    root_error="interrupted selection must explicitly preserve unknown results/costs"
    result_error="interrupted result invents acceptance/costs or artifact bindings differ"
    run_case("correctly labelled closed header still refuses absent seven original phases",None,None,"exact seven original successful phases missing")
    for key,value in [("schema","eth-native-final-selection/2"),("expanded_suite_passed",True),("all_required_native_checks_passed",True),
                      ("original_lean_suite_passed",False),("original_r2_protocol_passed",True),("independent_nanoda_acceptance_observed",True)]:
        run_case("coherently rebound map "+key+" refused","selection",lambda d,k=key,v=value:d.update({k:v}),root_error)
    for key in ["independent_nanoda_accepted","checker_exit_code"]:
        run_case("omitted nullable map field "+key+" refused","selection",lambda d,k=key:d.pop(k),root_error)
    for key,value in [("interrupt_signal",15.0),("attempt_timed_out",True),("final_attempt_cpu_seconds",1.0)]:
        run_case("invented interruption map "+key+" refused","selection",lambda d,k=key,v=value:d.update({k:v}),root_error)
    for key,value in [("expanded_suite_passed",True),("all_required_native_checks_passed",True),("independent_nanoda_acceptance_observed",True)]:
        run_case("coherently rebound result "+key+" refused","result",lambda d,k=key,v=value:d.update({k:v}),result_error)
    for key in ["independent_nanoda_accepted","checker_exit_code"]:
        run_case("omitted nullable result field "+key+" refused","result",lambda d,k=key:d.pop(k),result_error)
    run_case("invented final campaign cost refused","result",lambda d:d["resource_use"].update(total_campaign_final_child_cpu_seconds=1.0),"unknown final attempt/campaign costs were invented")
    run_case("unclosed negative seal refused","closing",lambda d:d.update(status="closure_validation_failed"),"reviewed interrupted closure has no final seal")
    run_case("coherently rebound closure source drift refused","source",None,"reviewed interrupted closure has no final seal")
    run_case("metadata helper source drift refused","metadata",None,"frozen incomplete metadata helpers changed")
    assert pub.sha((BASE/"publish_package.py").read_bytes())=="a72ed2f73b37daaa375ee62c238897ba8e86c7549292bf5e3d6f1412fcc8675c"
    checks.append("positive publisher source remains a72")
    report={"schema":"eth-interrupted-metadata-controls/1","status":"passed","checks":checks,
            "guard_sha256":pub.sha((BASE/"publication/native_interrupted_guard_r1.py").read_bytes()),"source_sha256":pub.sha(Path(__file__).read_bytes()),
            "scope":"Real gate with hash-bound fake headers that must refuse before original phase reads; no actual closure acceptance or proof/kernel/WIP/export work",
            "cpu_seconds":time.process_time()-cpu,"wall_seconds":time.monotonic()-start}
    pub.save(BASE/"publication/interrupted-metadata-control-result-r1.json",report)
    print(json.dumps({"status":"passed","checks":len(checks),"cpu_seconds":report["cpu_seconds"],"wall_seconds":report["wall_seconds"]}))


if __name__=="__main__":main()
