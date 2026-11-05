#!/usr/bin/env python3
"""Seal the original Lean suite plus a terminal nonaccepted additional Nano attempt.

Metadata/hashing only. This is disjoint from the positive R7 aggregate, never an
OR/fallback acceptance branch. Refuses a running attempt or recorded Nano exit0.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
R7 = BASE / "aggregate_native_result_r7.py"
R7_SHA = "be05f1310f22170cbc4564b9e35ad4fcb07b2515608aefeb88243e4d918c15d9"
TERMINAL = BASE / "native-retry-records/worker-stack256-r3-02"
OUTPUT = BASE / "native-incomplete-records"
SCHEMA = "openai-native-incomplete-result/1"
VERDICT = "ORIGINAL_LEAN_SUITE_PASS_ADDITIONAL_NANODA_INCOMPLETE"


def metadata():
    if hashlib.sha256(R7.read_bytes()).hexdigest() != R7_SHA:
        raise ValueError("frozen positive R7 validator changed")
    spec = importlib.util.spec_from_file_location("negative_closure_reviewed_r7", R7)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def classify_stage(stage):
    code = stage.get("exit_code"); reason = stage.get("reason")
    if type(code) is not int or code == 0:
        raise ValueError("negative closure requires an actual nonzero terminal stage")
    if code == 124 and reason == "stage timeout":
        return "stage_timeout_checker_acceptance_unobserved"
    return "terminal_stage_failure_checker_acceptance_unobserved"


def terminal_retry(m, e, h, content, fp, export, fresh, failure, preexec, outer_path):
    folder = m.canonical(TERMINAL)
    # Read actual closed failure before reading its other records or large assets.
    result = e.json(folder / "retry-result.json", True)
    m.require(result.get("schema") == "openai-native-resource-retry/1" and result.get("status") == "failed"
              and result.get("protocol_variant") == h.PROTOCOL and result.get("logical_check") == "extra-nanoda"
              and result.get("original_r2_attempt_passed") is False and result.get("interrupt_signal") is None
              and result.get("record_directory") == str(folder) and result.get("resource_policy") == h.RESOURCE_POLICY,
              "actual R3 attempt is running, successful, interrupted or not the reviewed terminal failure")
    prepared = e.json(folder / "retry-prepared.json", True)
    inputs = e.json(folder / "retry-inputs.json", True)
    m.require(prepared["started_utc"] == result["started_utc"] and prepared["protocol_variant"] == h.PROTOCOL
              and inputs["schema"] == "openai-native-resource-retry-inputs/1" and inputs["protocol_variant"] == h.PROTOCOL
              and inputs["base_r2_input_fingerprint"] == fp and inputs["selected_inputs"] == content
              and inputs["resource_policy"] == h.RESOURCE_POLICY and inputs["resource_inputs"] == h.resource_inputs(e)
              and inputs["export_input"] == export and inputs["config_delta"] == {}
              and inputs["failed_attempt"] == failure and inputs["fresh_directory"] == fresh["directory"],
              "terminal attempt original/resource input lineage differs")
    e.bind(inputs["retry_source"], m.RETRY_SOURCE)
    e.bind(inputs["fresh_phase_result"], Path(fresh["directory"]) / "phase-result.json")
    config = folder / "additional-nanoda-config.json"
    m.require(h.strict_policy_matches(e.json(config, True), export, 2)
              and e.identity(config)["sha256"] == e.identity(Path(failure["directory"]) / config.name)["sha256"],
              "strict original config bytes differ")
    python = inputs["argv"][0]
    m.require(inputs["argv"] == [python, str(m.RETRY_SOURCE), "--child", str(folder)]
              and inputs["environment"] == h.retry_environment(folder, python)
              and inputs["environment_keys"] == sorted(inputs["environment"])
              and inputs["cwd"] == str(m.WORKSPACE) and inputs["timeout_seconds"] == 7200,
              "exact terminal argv/environment/cap differs")
    sd = folder / "stages" / h.STAGE
    stage = e.json(sd / "finished.json", True); start = e.json(sd / "prepared.json", True)
    raw = e.identity(sd / "raw.log", True); classification = classify_stage(stage)
    m.require(stage["schema"] == "eth-ci-stage/1" and stage["name"] == h.STAGE
              and all(stage.get(k) == v for k,v in start.items()) and result["stage_receipts"] == [stage]
              and stage["argv"] == inputs["argv"] and stage["cwd"] == str(m.WORKSPACE)
              and stage["timeout_seconds"] == 7200 and stage["stdout_is_export"] is False
              and stage["raw_log_sha256"] == raw["sha256"] and stage["raw_log_bytes"] == raw["size_bytes"],
              "terminal stage closure/raw binding differs")
    begun = m.number(stage["started_utc_epoch"]); ended = begun + m.number(stage["wall_seconds"])
    m.number(stage["child_cpu_seconds"])
    m.require(preexec["end"] <= begun and fresh["end"] <= begun
              and m.utc(result["started_utc"]) <= begun and ended <= m.utc(result["finished_utc"]) + 1,
              "terminal retry chronology differs")
    if classification.startswith("stage_timeout"):
        m.require(stage["wall_seconds"] >= stage["timeout_seconds"] - 1,
                  "reported timeout did not reach the recorded stage cap")
    worker = e.json(folder / "worker-resource.json", True)
    m.require(worker["schema"] == "native-nanoda-worker-resource/2" and worker["protocol_variant"] == h.PROTOCOL
              and worker["retry_source"] == inputs["retry_source"] and worker["resource_policy"] == h.RESOURCE_POLICY
              and worker["resource_inputs"] == inputs["resource_inputs"] and worker["environment"] == inputs["environment"]
              and worker["environment_keys"] == inputs["environment_keys"] and worker["cwd"] == str(m.WORKSPACE)
              and worker["exec_argv"] == [python, str(h.RESOURCE_RECORDER), str(config)]
              and type(worker["pid"]) is int and worker["pid"] == worker["pgid"]
              and type(worker["main_stack_limits_before"]) is list and len(worker["main_stack_limits_before"]) == 2
              and all(type(v) is int for v in worker["main_stack_limits_before"])
              and worker["main_stack_limits_before"] == worker["main_stack_limits_after"]
              and worker["main_stack_limits_changed"] is False and worker["actual_nanoda_worker_extent_measured"] is False
              and begun - 1 <= m.utc(worker["observed_utc"]) <= ended + 1, "actual preexec worker event differs")
    events = [json.loads(line[len("WORKER_RESOURCE "):]) for line in (sd / "raw.log").read_text().splitlines()
              if line.startswith("WORKER_RESOURCE ")]
    m.require(events == [worker], "raw worker event differs from saved actual event")
    records = list((folder / "nanoda-records").glob("nanoda-*"))
    m.require(len(records) == 1, "expected exactly one actual launched Nano record")
    record = m.canonical(records[0]); zero = e.json(record / "00-prepared.json", True)
    one = e.json(record / "01-started.json", True)
    m.require(record.name.startswith("nanoda-" + str(worker["pid"]) + "-")
              and type(one["pid"]) is int and one["pid"] > 0
              and one["checker_argv"] == zero["checker_argv"] == [str(h.RESOURCE_BINARY), str(config)]
              and zero["wrapper_argv"] == [str(h.RESOURCE_RECORDER), str(config)]
              and zero["cwd"] == str(m.WORKSPACE) and zero["mode"] == "native_fake_landrun_unsandboxed"
              and zero["policy_changes_by_recorder"] is False and zero["effective_policy"] == h.policy(export,2)
              and begun - 1 <= m.utc(zero["started_at"]) <= m.utc(one["started_at"]) <= ended + 1,
              "actual prepared/start checker lineage differs")
    for key,path in [("binary_before",h.RESOURCE_BINARY),("config_before",config),("wrapper_source",h.RESOURCE_RECORDER),("shim",m.SHIM)]:
        e.bind(zero[key],path)
    m.require(all(zero["export_before"][k] == export[k] for k in ["path","sha256","size_bytes"]),
              "prepared checker payload differs")
    e.bind(zero["config_archive"],record / "effective-config.json",True)
    m.require(e.identity(config)["sha256"] == e.identity(record / "effective-config.json")["sha256"],
              "prepared forwarded/effective config bytes differ")
    archive = zero["export_archive"]
    m.require(archive["uncompressed_sha256"] == export["sha256"] and archive["uncompressed_size_bytes"] == export["size_bytes"],
              "prepared archive identity differs")
    gz = e.bind(archive["gzip"],record / "export.ndjson.gz")
    accepted = None; checker_code = None; complete = False; unchanged_during = None; observed = []
    if (record / "02-finished.json").exists():
        two = e.json(record / "02-finished.json",True)
        checker_code = two.get("checker_exit_code")
        m.require(type(checker_code) is int and checker_code != 0
                  and two.get("wrapper_exit_code") == checker_code and two.get("recording_complete") is True
                  and two.get("inputs_unchanged") is True and all(two.get(k) == v for k,v in zero.items())
                  and m.utc(one["started_at"]) <= m.utc(two["finished_at"]) <= ended + 1,
                  "closed Nano acceptance or inconsistent completion cannot use incomplete path")
        for key,path in [("binary_after",h.RESOURCE_BINARY),("config_after",config)]:e.bind(two[key],path)
        m.require(all(two["export_after"][k] == export[k] for k in ["path","sha256","size_bytes"]),"finished payload differs")
        accepted=False;complete=True;unchanged_during=True;observed.append(e.identity(record / "02-finished.json"))
    if (record / "99-error.json").exists():
        error=e.json(record / "99-error.json",True)
        m.require(error.get("recording_complete") is False and error.get("checker_exit_code") != 0,
                  "recorder error reports checker0 or contradictory completion")
        observed.append(e.identity(record / "99-error.json"))
    # Missing02 is an incomplete recorder observation, never an invented checker exit.
    outer_path=m.canonical(outer_path)
    m.require(outer_path.parent == BASE / "logs", "actual outer receipt must be an owned logs JSON")
    outer=e.json(outer_path,True);out_raw=m.canonical(m.PROJECT / outer["log_path"])
    m.require(out_raw.parent == BASE / "logs", "outer raw path outside owned logs")
    out_id=e.identity(out_raw,True)
    expected_outer = stage["exit_code"] if 0 < stage["exit_code"] < 256 else 125
    m.require(outer["agent"] == "codex-eth-replication" and outer["task"] == "external-eth-proof-replication-20261104"
              and type(outer["exit_code"]) is int and outer["exit_code"] == expected_outer and outer["timed_out"] is False
              and outer["log_sha256"] == out_id["sha256"] and outer["log_size"] == out_id["size_bytes"],
              "actual failed plain checkpoint DIGEST differs")
    last=next((line for line in reversed(out_raw.read_text().splitlines()) if line.startswith('{"')),None)
    m.require(last is not None and json.loads(last) == result,"outer final failed result differs")
    return {"name":"terminal-additional-nanoda","directory":str(folder),"result":e.identity(folder / "retry-result.json"),
            "stage":stage,"raw":raw,"start":begun,"end":ended,"classification":classification,
            "checker_exit_code":checker_code,"independent_nanoda_accepted":accepted,"acceptance_observed":False,
            "recording_complete":complete,"inputs_unchanged_during_check":unchanged_during,
            "actual_launch_records":[e.identity(record / n) for n in ["00-prepared.json","01-started.json","effective-config.json"]],
            "observed_terminal_checker_records":observed,"archive":gz,
            "archive_role":"prepared_for_attempt; never described as checked-and-accepted",
            "worker_event":e.identity(folder / "worker-resource.json"),"outer_receipt":e.identity(outer_path),"outer_digest":outer,
            "meaning":"Terminal outer/stage timeout or failure is not a checker logical rejection. Missing02 leaves checker exit and during-check unchanged status unknown."}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-receipt",type=Path,required=True)
    parser.add_argument("--phase",action="append",default=[],metavar="NAME=DIRECTORY")
    parser.add_argument("--failed-original-outer",type=Path,required=True)
    parser.add_argument("--terminal-outer-receipt",type=Path,required=True)
    parser.add_argument("--output-directory",type=Path,required=True)
    args=parser.parse_args();m=metadata();out=m.canonical(args.output_directory)
    m.require(out.is_relative_to(OUTPUT) and out != OUTPUT,"choose exclusive incomplete-result directory")
    out.mkdir(parents=True,exist_ok=False);e=m.Evidence();start=time.monotonic();cpu=time.process_time()
    m.write_json(out/"closure-prepared.json",{"schema":SCHEMA,"status":"preparing_negative_closure","source":e.identity(Path(__file__)),"proof_execution":False})
    try:
        terminal=e.json(TERMINAL/"retry-result.json",True)
        m.require(terminal.get("status")=="failed","terminal actual R3 failed result required before other validation")
        folders=m.mappings(args.phase,True,m.ORIGINAL_PHASES);content,fp,expected=m.pinned_inputs(e);h=m.retry_metadata(e)
        build=m.source_build(e,args.build_receipt)
        phases={n:m.closed_phase(e,n,folders[n],content,fp) for n in m.ORIGINAL_PHASES}
        identities={n:m.identity_phase(phases[n],expected) for n in ['pre-identity','post-identity']};audit=m.audit_phase(phases['audit'])
        lines=phases['comparator']['raw_path'].read_bytes().splitlines()
        m.require(b'Your solution is okay!' in lines and b'Lean default kernel accepts the solution' in lines,'original Comparator sentinels missing')
        export=m.export_phase(e,phases['selected-export'])
        failure=h.failed_attempt(e,m.RECORD_ROOT/'r2-06-extra-nanoda',args.failed_original_outer,content,export)
        preexec=m.preexec_environment_failure(e,h,content,fp,export,phases['original-fresh'])
        additional=terminal_retry(m,e,h,content,fp,export,phases['original-fresh'],failure,preexec,args.terminal_outer_receipt)
        ordered=sorted(list(phases.values())+[failure,preexec,additional],key=lambda r:r['start'])
        m.require(ordered[0]['name']=='pre-identity' and ordered[1]['name']=='trace' and ordered[-1]['name']=='post-identity'
                  and build['end']<=ordered[0]['start']+1 and all(a['end']<=z['start']+1 for a,z in zip(ordered,ordered[1:]))
                  and phases['selected-export']['end']<=failure['start']<=phases['original-fresh']['start']
                  and additional['end']<=phases['post-identity']['start'], 'negative campaign chronology/postidentity-last differs')
        negfiles=[BASE/'nanoda_serial_stack_retry_r1.py',BASE/'aggregate_native_result_r5.py']
        negatives=[e.identity(p,True) for p in negfiles]
        # Main-stack diagnostics are immutable local public-suitable byte copies, not new runs.
        copy_manifest=e.json(m.TREE/'publication/main-stack-negative-evidence-r1.json',True)
        m.require(e.identity(m.TREE/'publication/main-stack-negative-evidence-r1.json')['sha256']=='2f73ad24b712336207a470162e4cf22c23653fb7e7e16ede19e0a811ccbe95f9','mainstack negative copy manifest drift')
        for r in copy_manifest['records']:
            p=m.TREE/r['copy_path'];a=e.identity(p,True)
            m.require(a['sha256']==r['copy_sha256']==r['source_sha256'] and a['size_bytes']==r['copy_size_bytes']==r['source_size_bytes'],'mainstack negative bytes differ')
            negatives.append(a)
        e.stable();principal=[p['stage'] for p in phases.values()]+[failure['stage'],preexec['stage'],additional['stage']]
        result={"schema":SCHEMA,"verdict":VERDICT,"original_lean_suite_passed":True,"all_required_native_checks_passed":False,
                "expanded_suite_passed":False,"original_r2_protocol_passed":False,"additional_nanoda_verification":"INCOMPLETE",
                "independent_nanoda_acceptance_observed":False,"independent_nanoda_accepted":additional['independent_nanoda_accepted'],
                "checker_exit_code":additional['checker_exit_code'],"input_fingerprint":fp,"source_build":build,
                "source_and_tool_inputs":content,"original_seven_phase_results":[{"name":n,"result":e.identity(Path(phases[n]['directory'])/'phase-result.json'),"stage":phases[n]['stage']} for n in m.ORIGINAL_PHASES],
                "identity_pre_post":identities,"target_axiom_audit":audit,"additional_terminal_attempt":additional,
                "retained_original_nanoda_failure":failure,"retained_preexec_environment_failure":preexec,
                "retained_mainstack_negative_artifacts":negatives,"resource_profile_inputs":h.resource_inputs(e),
                "resource_use":{"source_build_checkpoint_cpu_seconds":build['checkpoint']['cpu_seconds'],"source_build_checkpoint_wall_seconds":build['checkpoint']['wall_seconds'],
                  "principal_nonoverlapping_child_cpu_seconds":build['checkpoint']['cpu_seconds']+sum(s['child_cpu_seconds'] for s in principal),
                  "principal_nonoverlapping_wall_seconds_summed":build['checkpoint']['wall_seconds']+sum(s['wall_seconds'] for s in principal),
                  "outer_and_nested_checker_costs":"Retained separately, not added twice. Tool preparation can overlap fresh and is outside these sums.","paid_cloud_spend_usd":0},
                "limitations":["No independent Rust-kernel acceptance was observed; incomplete is not logical rejection.","Comparator embeds Lean4.35; original fresh usesLean4.34.1, same implementation family.","Native fakeLandrun supplies no OS isolation; exactformal target only, no practicalSAT/SHA256d result.","Missing02 means no closed during-check unchanged/exit observation; prepared archive identity is not acceptance.","CFvalue remains private in local input/worker/raw data; public derivatives must redactvalue/retainSHA.","Source monotonic elapsed and calendar UTC gaps/manual pauses remain separate; no isolated performance orRSS claim."],
                "artifacts":list(e.rows.values()),"public_small_artifacts":[e.rows[p] for p in sorted(e.public)],
                "closure_resources":{"own_cpu_seconds":time.process_time()-cpu,"wall_seconds":time.monotonic()-start,"scope":"Hash/parsing only, no proof execution."}}
        m.write_json(out/'native-incomplete-result.json',result)
        m.write_json(out/'closure-finished.json',{"schema":SCHEMA,"status":"negative_evidence_closed","expanded_suite_passed":False,"result":e.identity(out/'native-incomplete-result.json')})
        with (out/'report.md').open('x') as f:
            f.write('Original Lean suite passed; additional independent Nano verification remains incomplete. All terminal and prior failed evidence is preserved. This is not an expanded-suite PASS or a logical rejection. See the companion JSON for exact original phases, terminal failure/timeout, unknown checker fields, provenance and costs.\n')
            f.flush();os.fsync(f.fileno())
        print(json.dumps({"status":"negative_evidence_closed","expanded_suite_passed":False,"result":e.identity(out/'native-incomplete-result.json')}));return 0
    except Exception as ex:
        m.write_json(out/'closure-finished.json',{"schema":SCHEMA,"status":"closure_validation_failed","expanded_suite_passed":False,"error":type(ex).__name__+': '+str(ex)})
        print(json.dumps({"status":"closure_validation_failed","error":str(ex)}));return 1

if __name__=='__main__':sys.exit(main())
