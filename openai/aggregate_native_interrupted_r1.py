#!/usr/bin/env python3
"""Seal original Lean success plus the exact recovered signal15 interruption.

Disjoint metadata/hashing closure, not a timeout or checker result. Missing
finished receipts, empty outer capture and unknown final costs stay explicit.
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
OUTPUT = BASE / "native-interrupted-records"
RESERVED = OUTPUT / "worker-stack256-r1-01"
RECOVERY = BASE / "logs/interruption-recovery-observation-r1.json"
RECOVERY_SHA = "89be8382a7c68dc549f31799154532a58819aba47c1b2b9e5dcfa7b6c70e6939"
INTERRUPTED_RESULT_SHA = "e0662f9de6c8699328549233d19c9438c1029951ac0ab3c55361824c78d848b0"
SCHEMA = "openai-native-interrupted-result/1"
VERDICT = "ORIGINAL_LEAN_SUITE_PASS_ADDITIONAL_NANODA_INTERRUPTED"


def metadata():
    if hashlib.sha256(R7.read_bytes()).hexdigest() != R7_SHA:
        raise ValueError("frozen positive R7 validator changed")
    spec = importlib.util.spec_from_file_location("negative_closure_reviewed_r7", R7)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def require_interrupted_header(result):
    if not (result.get("schema") == "openai-native-resource-retry/1"
            and result.get("status") == "failed" and type(result.get("interrupt_signal")) is int
            and result["interrupt_signal"] == 15 and result.get("stage_receipts") == []
            and result.get("error") == "PermissionError: [Errno 1] Operation not permitted"
            and result.get("original_r2_attempt_passed") is False):
        raise ValueError("exact recovered signal15 interruption header required")


def interrupted_retry(m, e, h, content, fp, export, fresh, failure, preexec):
    folder=m.canonical(TERMINAL)
    result=e.json(folder/'retry-result.json',True);require_interrupted_header(result)
    m.require(e.identity(folder/'retry-result.json')['sha256']==INTERRUPTED_RESULT_SHA
              and result['protocol_variant']==h.PROTOCOL and result['logical_check']=='extra-nanoda'
              and result['record_directory']==str(folder) and result['resource_policy']==h.RESOURCE_POLICY,
              'actual interrupted result identity/protocol differs')
    recovery=e.json(RECOVERY,True)
    m.require(e.identity(RECOVERY)['sha256']==RECOVERY_SHA and recovery['schema']=='eth-proof-interruption-recovery/1'
              and recovery['known_checker_pid']==38877 and recovery['known_recorder_pid']==38848 and recovery['known_pgid']==38848
              and recovery['process_observation']['argv']==['ps','-axo','pid=,ppid=,pgid=,stat=,lstart=,comm=']
              and recovery['process_observation']['exit_code']==0 and recovery['process_observation']['matching_known_pid_or_group_rows']==[]
              and recovery['checker_exit_code'] is None and recovery['independent_nanoda_accepted'] is None
              and recovery['independent_nanoda_acceptance_observed'] is False and recovery['final_child_cpu_seconds'] is None
              and recovery['timeout_observed'] is False,'root recovery observation differs')
    expected_record=folder/'nanoda-records/nanoda-38848-vymihcgo'
    sd=folder/'stages'/h.STAGE
    outer_capture=BASE/'logs/native-worker-stack256-cf-r3-checkpoint.json'
    outer_raw=BASE/'logs/native-worker-stack256-cf-r3-checkpoint.txt'
    expected_paths=[outer_capture,outer_raw,folder/'retry-result.json',folder/'retry-prepared.json',folder/'retry-inputs.json',
                    folder/'worker-resource.json',sd/'prepared.json',sd/'raw.log',sd/'finished.json',
                    expected_record/'00-prepared.json',expected_record/'01-started.json',expected_record/'02-finished.json',expected_record/'99-error.json']
    manifest=recovery['artifacts'];m.require(len(manifest)==13 and {row['path'] for row in manifest}=={str(p.relative_to(m.TREE)) for p in expected_paths},'exact recovery artifact set differs')
    missing=[]
    for row in manifest:
        path=m.canonical(m.TREE/row['path'])
        if row['exists'] is True:
            ident=e.identity(path,True)
            m.require(ident['sha256']==row['sha256'] and ident['size_bytes']==row['size_bytes'],'recovered bytes drifted')
        else:
            m.require(row['exists'] is False and not path.exists() and not path.is_symlink(),'missing terminal record unexpectedly exists')
            missing.append(str(path))
    m.require(set(missing)=={str(sd/'finished.json'),str(expected_record/'02-finished.json'),str(expected_record/'99-error.json')},'unexpected recovery missing record set')
    m.require(e.identity(outer_capture)['size_bytes']==0 and e.identity(outer_capture)['sha256']=='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
              and e.identity(outer_raw)['size_bytes']==7726 and e.identity(outer_raw)['sha256']=='4c4411725b55d0a8958f3cefb1d8a71869c1d01ded2aa7c9aecba7ca69d78f27',
              'actual empty outer capture/raw fragment differs')
    prepared=e.json(folder/'retry-prepared.json',True);inputs=e.json(folder/'retry-inputs.json',True)
    m.require(prepared['started_utc']==result['started_utc'] and prepared['protocol_variant']==h.PROTOCOL
              and inputs['schema']=='openai-native-resource-retry-inputs/1' and inputs['protocol_variant']==h.PROTOCOL
              and inputs['base_r2_input_fingerprint']==fp and inputs['selected_inputs']==content
              and inputs['resource_policy']==h.RESOURCE_POLICY and inputs['resource_inputs']==h.resource_inputs(e)
              and inputs['export_input']==export and inputs['config_delta']=={} and inputs['failed_attempt']==failure
              and inputs['fresh_directory']==fresh['directory'],'interrupted attempt original/resource lineage differs')
    e.bind(inputs['retry_source'],m.RETRY_SOURCE);e.bind(inputs['fresh_phase_result'],Path(fresh['directory'])/'phase-result.json')
    config=folder/'additional-nanoda-config.json'
    m.require(h.strict_policy_matches(e.json(config,True),export,2)
              and e.identity(config)['sha256']==e.identity(Path(failure['directory'])/config.name)['sha256'],'strict original config bytes differ')
    python=inputs['argv'][0]
    m.require(inputs['argv']==[python,str(m.RETRY_SOURCE),'--child',str(folder)]
              and inputs['environment']==h.retry_environment(folder,python) and inputs['environment_keys']==sorted(inputs['environment'])
              and inputs['cwd']==str(m.WORKSPACE) and inputs['timeout_seconds']==7200,'exact prepared argv/environment/cap differs')
    stage=e.json(sd/'prepared.json',True);raw=e.identity(sd/'raw.log',True)
    m.require(stage['schema']=='eth-ci-stage/1' and stage['name']==h.STAGE and stage['argv']==inputs['argv']
              and stage['cwd']==str(m.WORKSPACE) and stage['timeout_seconds']==7200 and stage['stdout_is_export'] is False,
              'actual prepared stage differs; no finished stage is substituted')
    begun=m.number(stage['started_utc_epoch']);failed_finish=m.utc(result['finished_utc'])
    observed_begin=m.utc(recovery['observed_start_utc']);observed_end=m.utc(recovery['observed_end_utc'])
    m.require(preexec['end']<=begun and fresh['end']<=begun and m.utc(result['started_utc'])<=begun
              and begun<=failed_finish<=observed_begin<=observed_end,'recorded interruption/recovery chronology differs')
    worker=e.json(folder/'worker-resource.json',True)
    m.require(worker['schema']=='native-nanoda-worker-resource/2' and worker['protocol_variant']==h.PROTOCOL
              and worker['retry_source']==inputs['retry_source'] and worker['resource_policy']==h.RESOURCE_POLICY
              and worker['resource_inputs']==inputs['resource_inputs'] and worker['environment']==inputs['environment']
              and worker['environment_keys']==inputs['environment_keys'] and worker['cwd']==str(m.WORKSPACE)
              and worker['exec_argv']==[python,str(h.RESOURCE_RECORDER),str(config)]
              and type(worker['pid']) is int and worker['pid']==worker['pgid']==recovery['known_recorder_pid']
              and type(worker['main_stack_limits_before']) is list and len(worker['main_stack_limits_before'])==2
              and all(type(v) is int for v in worker['main_stack_limits_before'])
              and worker['main_stack_limits_before']==worker['main_stack_limits_after']
              and worker['main_stack_limits_changed'] is False and worker['actual_nanoda_worker_extent_measured'] is False
              and begun-1<=m.utc(worker['observed_utc'])<=failed_finish,'actual preexec resource event differs')
    events=[json.loads(line[len('WORKER_RESOURCE '):]) for line in (sd/'raw.log').read_text().splitlines() if line.startswith('WORKER_RESOURCE ')]
    m.require(events==[worker],'actual saved worker event differs')
    records=list((folder/'nanoda-records').glob('nanoda-*'));m.require(records==[expected_record],'exact actual launched record directory differs')
    zero=e.json(expected_record/'00-prepared.json',True);one=e.json(expected_record/'01-started.json',True)
    m.require(one['pid']==recovery['known_checker_pid'] and type(one['pid']) is int
              and one['checker_argv']==zero['checker_argv']==[str(h.RESOURCE_BINARY),str(config)]
              and zero['wrapper_argv']==[str(h.RESOURCE_RECORDER),str(config)] and zero['cwd']==str(m.WORKSPACE)
              and zero['mode']=='native_fake_landrun_unsandboxed' and zero['policy_changes_by_recorder'] is False
              and zero['effective_policy']==h.policy(export,2)
              and begun-1<=m.utc(zero['started_at'])<=m.utc(one['started_at'])<=failed_finish,'actual prepared/start Nano lineage differs')
    for key,path in [('binary_before',h.RESOURCE_BINARY),('config_before',config),('wrapper_source',h.RESOURCE_RECORDER),('shim',m.SHIM)]:e.bind(zero[key],path)
    m.require(all(zero['export_before'][k]==export[k] for k in ['path','sha256','size_bytes']),'prepared payload differs')
    e.bind(zero['config_archive'],expected_record/'effective-config.json',True)
    m.require(e.identity(config)['sha256']==e.identity(expected_record/'effective-config.json')['sha256'],'prepared effective config bytes differ')
    archive=zero['export_archive'];m.require(archive['uncompressed_sha256']==export['sha256'] and archive['uncompressed_size_bytes']==export['size_bytes'],'prepared archive metadata differs')
    gz=e.bind(archive['gzip'],expected_record/'export.ndjson.gz')
    return {'name':'interrupted-additional-nanoda','directory':str(folder),'result':e.identity(folder/'retry-result.json'),
            'prepared_stage':stage,'prepared_stage_receipt':e.identity(sd/'prepared.json'),'raw':raw,
            'start':begun,'end':observed_end,'chronology_bound':'Recovery observation UTC, not a completed checker/stage finish',
            'classification':'INTERRUPTED_SIGNAL_15_NO_TERMINAL_CHECKER_RECORD','interrupt_signal':15,
            'checker_exit_code':None,'independent_nanoda_accepted':None,'acceptance_observed':False,
            'recording_complete':False,'inputs_unchanged_during_check':None,'timeout_observed':False,
            'final_child_cpu_seconds':None,'final_wall_seconds':None,
            'actual_launch_records':[e.identity(expected_record/n) for n in ['00-prepared.json','01-started.json','effective-config.json']],
            'observed_terminal_checker_records':[],'archive':gz,'archive_role':'prepared_for_attempt; never described as checked-and-accepted',
            'worker_event':e.identity(folder/'worker-resource.json'),'recovery_observation':e.identity(RECOVERY),
            'outer_capture':e.identity(outer_capture),'outer_raw_fragment':e.identity(outer_raw),
            'outer_capture_role':'Empty capture and raw fragment are not a completed checkpoint DIGEST',
            'missing_artifacts':missing,'recorded_interruption_finish_utc':result['finished_utc'],
            'recovery_observed_end_utc':recovery['observed_end_utc'],
            'meaning':'Exact recorded signal15 interruption and later PID/group absence observation. Trigger attribution and checker exit/final CPU are unknown; no timeout or logical rejection is inferred.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-receipt",type=Path,required=True)
    parser.add_argument("--phase",action="append",default=[],metavar="NAME=DIRECTORY")
    parser.add_argument("--failed-original-outer",type=Path,required=True)
    parser.add_argument("--output-directory",type=Path,required=True)
    args=parser.parse_args();m=metadata();out=m.canonical(args.output_directory)
    m.require(out==RESERVED,"choose exact reserved interrupted-result directory")
    out.mkdir(parents=True,exist_ok=False);e=m.Evidence();start=time.monotonic();cpu=time.process_time()
    m.write_json(out/"closure-prepared.json",{"schema":SCHEMA,"status":"preparing_interrupted_closure","source":e.identity(Path(__file__)),"proof_execution":False})
    try:
        terminal=e.json(TERMINAL/"retry-result.json",True)
        require_interrupted_header(terminal)
        folders=m.mappings(args.phase,True,m.ORIGINAL_PHASES);content,fp,expected=m.pinned_inputs(e);h=m.retry_metadata(e)
        build=m.source_build(e,args.build_receipt)
        phases={n:m.closed_phase(e,n,folders[n],content,fp) for n in m.ORIGINAL_PHASES}
        identities={n:m.identity_phase(phases[n],expected) for n in ['pre-identity','post-identity']};audit=m.audit_phase(phases['audit'])
        lines=phases['comparator']['raw_path'].read_bytes().splitlines()
        m.require(b'Your solution is okay!' in lines and b'Lean default kernel accepts the solution' in lines,'original Comparator sentinels missing')
        export=m.export_phase(e,phases['selected-export'])
        failure=h.failed_attempt(e,m.RECORD_ROOT/'r2-06-extra-nanoda',args.failed_original_outer,content,export)
        preexec=m.preexec_environment_failure(e,h,content,fp,export,phases['original-fresh'])
        additional=interrupted_retry(m,e,h,content,fp,export,phases['original-fresh'],failure,preexec)
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
        scheduling_hashes={"temporary-suspension-r1.json":"73584dc6355248c7899afe15e527281af1a0ac5641071d78ff321a655b2341ef",
          "temporary-resumption-r1.json":"7765cec437c7dd350ff481edf35dd76d4df8e87f04b223240860bda90c12689f",
          "memory-pressure-suspension-r2.json":"34d3b7d059439eea0b9d5a41df8470fad59b22b524403b62b1ea58e1a018ca95",
          "memory-pressure-resumption-r3.json":"de271acadc3b41a6556f614aafcd9595bf7f9ff762821b72ddc9947c88b095db",
          "memory-pressure-resumption-r4.json":"810e07a6d0b5c63f77ec064f91f998f4ab5b0fee948d72b8f210670a2451f9d5"}
        for name,digest in scheduling_hashes.items():
            m.require(e.identity(BASE/'logs'/name,True)['sha256']==digest,'recorded manual scheduling evidence drift')
        build['scheduling_receipts']=[e.identity(BASE/'logs'/name) for name in scheduling_hashes]
        e.stable();principal=[p['stage'] for p in phases.values()]+[failure['stage'],preexec['stage']]
        result={"schema":SCHEMA,"verdict":VERDICT,"original_lean_suite_passed":True,"all_required_native_checks_passed":False,
                "expanded_suite_passed":False,"original_r2_protocol_passed":False,"additional_nanoda_verification":"INTERRUPTED",
                "independent_nanoda_acceptance_observed":False,"independent_nanoda_accepted":additional['independent_nanoda_accepted'],
                "checker_exit_code":additional['checker_exit_code'],"input_fingerprint":fp,"source_build":build,
                "source_and_tool_inputs":content,"original_seven_phase_results":[{"name":n,"result":e.identity(Path(phases[n]['directory'])/'phase-result.json'),"stage":phases[n]['stage']} for n in m.ORIGINAL_PHASES],
                "identity_pre_post":identities,"target_axiom_audit":audit,"additional_interrupted_attempt":additional,
                "retained_original_nanoda_failure":failure,"retained_preexec_environment_failure":preexec,
                "retained_mainstack_negative_artifacts":negatives,"resource_profile_inputs":h.resource_inputs(e),
                "resource_use":{"source_build_checkpoint_cpu_seconds":build['checkpoint']['cpu_seconds'],"source_build_checkpoint_wall_seconds":build['checkpoint']['wall_seconds'],
                  "known_nonoverlapping_child_cpu_seconds":build['checkpoint']['cpu_seconds']+sum(s['child_cpu_seconds'] for s in principal),
                  "known_nonoverlapping_wall_seconds_summed":build['checkpoint']['wall_seconds']+sum(s['wall_seconds'] for s in principal),
                  "interrupted_attempt_final_child_cpu_seconds":None,"interrupted_attempt_final_wall_seconds":None,"total_campaign_final_child_cpu_seconds":None,"total_campaign_final_wall_seconds":None,
                  "outer_and_nested_checker_costs":"Known completed-stage costs only; interrupted attempt and campaign final totals unknown. Empty outer capture is not a DIGEST. Prior nested/outer costs not added twice; overlapping preparation excluded.","paid_cloud_spend_usd":0},
                "limitations":["No independent Rust-kernel acceptance was observed; incomplete is not logical rejection.","Comparator embeds Lean4.35; original fresh usesLean4.34.1, same implementation family.","Native fakeLandrun supplies no OS isolation; exactformal target only, no practicalSAT/SHA256d result.","Missing02 means no closed during-check unchanged/exit observation; prepared archive identity is not acceptance.","CFvalue remains private in local input/worker/raw data; public derivatives must redactvalue/retainSHA.","Exact recovered signal15 interruption; not deadline timeout or checker logical rejection. Trigger attribution unknown.","Recovery UTC bounds chronology only, not checker wall/CPU. Source monotonic elapsed and calendar UTC gaps/manual pauses remain separate; no isolated performance orRSS claim."],
                "artifacts":list(e.rows.values()),"public_small_artifacts":[e.rows[p] for p in sorted(e.public)],
                "closure_resources":{"own_cpu_seconds":time.process_time()-cpu,"wall_seconds":time.monotonic()-start,"scope":"Hash/parsing only, no proof execution."}}
        m.write_json(out/'native-interrupted-result.json',result)
        with (out/'report.md').open('x') as f:
            f.write('Original Lean suite passed; additional independent Nano verification was interrupted. Signal15 and PermissionError are recorded, with no finished stage/checker receipt and an empty outer capture. No timeout, checker acceptance or rejection, final checker cost or interruption trigger is invented. Prior failures remain preserved. See the companion JSON for exact original phases, recovery observation, nullable checker fields and known-cost limits.\n')
            f.flush();os.fsync(f.fileno())
        m.write_json(out/'native-interrupted-artifacts.json',{'artifacts':result['artifacts'],
                     'public_small_artifacts':result['public_small_artifacts'],'large_exports':'Local metadata/hashes only; no publication by closure utility.'})
        m.write_json(out/'closure-finished.json',{"schema":SCHEMA,"status":"interrupted_evidence_closed","expanded_suite_passed":False,
                     "result":e.identity(out/'native-interrupted-result.json'),"report":e.identity(out/'report.md'),
                     "artifacts_manifest":e.identity(out/'native-interrupted-artifacts.json')})
        print(json.dumps({"status":"interrupted_evidence_closed","expanded_suite_passed":False,"result":e.identity(out/'native-interrupted-result.json')}));return 0
    except Exception as ex:
        m.write_json(out/'closure-finished.json',{"schema":SCHEMA,"status":"closure_validation_failed","expanded_suite_passed":False,"error":type(ex).__name__+': '+str(ex)})
        print(json.dumps({"status":"closure_validation_failed","error":str(ex)}));return 1

if __name__=='__main__':sys.exit(main())
