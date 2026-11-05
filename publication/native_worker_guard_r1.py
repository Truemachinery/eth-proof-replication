"""Metadata-only publication gate for the reviewed worker-stack256/CF R3 campaign.

No checker, aggregator, proof source, binary, NDJSON or gzip is executed/read here.
Large-asset and source-tree identities are statements in the pinned closed R7
aggregate and reviewed provenance; this gate rechecks the small supporting bytes.
The caller supplies its normal stable reader/binder and original phase validator.
"""
import json
from pathlib import Path, PurePosixPath
import re

PROTOCOL = "openai-native-r2-nanoda-worker-stack256-cfenv-r3"
FP = "c84c8907998f23cc282a29ae7fef4a37cbaff735327096e748afe546af8c4f52"
AGGREGATOR = "openai/aggregate_native_result_r7.py"
AGGREGATOR_SHA = "be05f1310f22170cbc4564b9e35ad4fcb07b2515608aefeb88243e4d918c15d9"
HELPER = "openai/nanoda_worker_stack_retry_r3.py"
HELPER_SHA = "9f4fe4e87a568f8bd89d39df61ed03fc155e120e2194aa82dce038918c1f34f3"
RETRY = "openai/native-retry-records/worker-stack256-r3-02"
PREEXEC = "openai/native-retry-records/worker-stack256-r2-01"
FAILED = "openai/native-phase-records/r2-06-extra-nanoda"
TOOLS = "verification-tools-worker-stack256"
BINARY = TOOLS + "/target/release/nanoda_bin"
BINARY_SHA = "10e1a4ebdb6fa606ca8d7a60774d8af0655294ab0b19d03a838a5ba746b7c2d9"
OLD_BINARY = "verification-tools/nanoda-source/target/release/nanoda_bin"
OLD_BINARY_SHA = "d9a1fc5371b84c9eb0687a7630eb724fa88886d9f5d665f09f9f926730573b80"
RECORDER_SHA = "c34f36d630d182708937a5280b6eda8d0723fa0ffdd85caf8fc54af17b332f48"
EXPORT_NAME = "openai/native-phase-records/r2-05-selected-export/selected-solution.ndjson"
EXPORT_SHA = "bdbc9afe336fea99b01bc4eced6e4232153afdefe13a1095cdc5ca9499e3f573"
EXPORT_SIZE = 2355666449
CONFIG_SHA = "acd37052945a7ef7364cf4c30177c6f0d2e7355f2d5a86c1f242986ad361acf4"
CF_KEY = "__CF_USER_TEXT_ENCODING"
CF_SHA = "bfea86ae0b123713ac5b1af20b2dd4ead4f0bb81822ed654e80347e6fa420f3b"
PINS = {
    "tool-manifest-r1.json": "f90219aaeedd7bbff3746eff8167c99b8d075d1045ae5c4363bc8ebb425bc30d",
    "source-provenance-r1.json": "b73658a2cec0410e1df0a90c446c5f15c0cf3a28875131027972ddece9c71dc7",
    "build-result-r1.json": "9746cc46746f11d88d5d0f3f5ad1458e05a57627abb90fd6d60c6f42ebef325e",
    "resource-only.patch": "8772472e7acd9c5900d01db457b7e7ba6d5e2273c57e3f939fa5d2485412659f",
    "worker-probe-result-r1.json": "c2d1e9442e256121dff3f627d3a6db0deb184ec5ca6d9c498dd9910a272c65cd",
    "tiny-controls-r1/control-result-r1.json": "c539e45b86bf71fbfb4b69d61a2cf3654681baf3a159ed9a2ffd6a4c7b6ccd8b",
    "record_nanoda.py": RECORDER_SHA,
}
POLICY = {"nanoda_num_threads": 2, "compiled_requested_worker_stack_bytes": 268435456,
          "original_compiled_requested_worker_stack_bytes": 16777216,
          "checker_binary_changed": True, "checker_logic_patch": False,
          "main_stack_limits_changed": False, "actual_nanoda_worker_extent_measured": False,
          "export_changed": False, "axiom_policy_changed": False, "config_changed": False}
PHASES = ("pre-identity", "trace", "audit", "comparator", "selected-export", "extra-nanoda", "original-fresh", "post-identity")
ORIGINAL = tuple(p for p in PHASES if p != "extra-nanoda")
AGG_FILES = {"aggregation-prepared.json", "native-replication-result.json", "native-replication-artifacts.json", "report.md", "aggregation-finished.json"}
REVIEWS = {"openai/" + n for n in (
    "native-saved-evidence-review-part1-r1.json", "native-saved-evidence-review-part1-r1.md",
    "native-saved-evidence-review-part2-r1.json", "native-saved-evidence-review-part2-r1.md",
    "native-saved-evidence-review-r1.json", "native-saved-evidence-review-r1.md", "native-replication-report-r1.md")}
REQUIRED_REVIEWS = {"openai/native-saved-evidence-review-r1.json",
                    "openai/native-saved-evidence-review-r1.md",
                    "openai/native-replication-report-r1.md"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def integer(value, expected):
    return type(value) is int and value == expected


def same_identity(a, b):
    return all(a.get(k) == b.get(k) for k in ("path", "sha256", "size_bytes"))


class Gate:
    def __init__(self, base, publisher):
        self.base, self.p = Path(base).resolve(), publisher
        self.files, self.logs = {}, {}

    def path(self, name):
        require(isinstance(name, str) and str(PurePosixPath(name)) == name
                and not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts,
                "noncanonical native evidence name")
        return str(self.base / name)

    def read(self, name, kind="manifest"):
        self.path(name)
        require(not name.endswith((".ndjson", ".gz")) and "/source/" not in name
                and "/target/" not in name, "large/source/binary evidence must remain metadata-only")
        data = self.p.read_stable(self.base, name)
        self.files[name] = kind
        return data

    def obj(self, name, kind="manifest"):
        def unique(rows):
            out = {}
            for k, v in rows:
                require(k not in out, "duplicate native JSON key")
                out[k] = v
            return out
        return json.loads(self.read(name, kind), object_pairs_hook=unique)

    def bind(self, row, name, kind="manifest"):
        data = self.read(name, kind)
        require(isinstance(row, dict) and row.get("path") == self.path(name)
                and row.get("sha256") == self.p.sha(data)
                and integer(row.get("size_bytes"), len(data)), "native small reference differs: " + name)
        return data

    def reference(self, row, name, digest=None, size=None):
        require(isinstance(row, dict) and row.get("path") == self.path(name)
                and re.fullmatch(r"[0-9a-f]{64}", row.get("sha256", ""))
                and type(row.get("size_bytes")) is int and row["size_bytes"] > 0
                and (digest is None or row["sha256"] == digest)
                and (size is None or row["size_bytes"] == size), "reported asset identity differs: " + name)

    def stage(self, folder, stage, result, inputs, code):
        name = folder + "/stages/" + stage
        done = self.obj(name + "/finished.json")
        start = self.obj(name + "/prepared.json")
        raw = self.read(name + "/raw.log", "completed_log")
        require(done.get("schema") == "eth-ci-stage/1" and done.get("name") == stage
                and integer(done.get("exit_code"), code) and done.get("reason") is None
                and done.get("timed_out", False) is False and done.get("stdout_is_export") is False
                and all(done.get(k) == v for k, v in start.items())
                and done.get("argv") == inputs.get("argv") and done.get("cwd") == inputs.get("cwd")
                and done.get("timeout_seconds") == inputs.get("timeout_seconds")
                and done.get("raw_log_sha256") == self.p.sha(raw)
                and integer(done.get("raw_log_bytes"), len(raw)) and result.get("stage_receipts") == [done],
                "native worker stage is incomplete or raw differs")
        self.logs[name + "/raw.log"] = {"receipt": folder + "/retry-result.json" if folder != FAILED else folder + "/phase-result.json",
                                        "exit_code": code, "timed_out": False,
                                        "raw_log_sha256": self.p.sha(raw), "raw_log_bytes": len(raw)}
        return done, raw


def config(g, folder, export):
    wanted = {"use_stdin": False, "export_file_path": export["path"],
              "permitted_axioms": ["propext", "Quot.sound", "Classical.choice"],
              "unpermitted_axiom_hard_error": True, "num_threads": 2,
              "nat_extension": True, "string_extension": True}
    name = folder + "/additional-nanoda-config.json"
    actual = g.obj(name)
    require(actual == wanted and integer(actual.get("num_threads"), 2)
            and all(actual.get(k) is v for k, v in wanted.items() if type(v) is bool), "strict Nano config differs")
    # Its absolute export path makes the config hash specific to this owned tree.
    require(g.p.sha(g.read(name)) == CONFIG_SHA, "actual strict config bytes differ")
    return wanted


def nano(g, folder, summary, export, code, binary, binary_sha, recorder):
    ref = summary["finished_receipt"]
    prefix = folder + "/nanoda-records/"
    require(isinstance(ref.get("path"), str) and ref["path"].startswith(g.path(folder + "/nanoda-records") + "/"), "Nano record root differs")
    name = str(Path(ref["path"]).relative_to(g.base))
    require(re.fullmatch(re.escape(prefix) + r"nanoda-[A-Za-z0-9_-]+/02-finished\.json", name), "Nano record name differs")
    two = json.loads(g.bind(ref, name)); record = str(PurePosixPath(name).parent)
    require(not (g.base / record / "99-error.json").exists()
            and sorted(str(p.relative_to(g.base)) for p in (g.base / folder / "nanoda-records").glob("nanoda-*")) == [record],
            "Nano error/extra invocation exists")
    names = [record + "/" + s for s in ("00-prepared.json", "01-started.json", "02-finished.json", "effective-config.json")]
    require(len(summary.get("small_records", [])) == 4, "Nano four small records missing")
    for n, row in zip(names, summary["small_records"]):
        g.bind(row, n)
    zero, one, effective = g.obj(names[0]), g.obj(names[1]), g.obj(names[3])
    wanted = config(g, folder, export)
    argv = [g.path(binary), g.path(folder + "/additional-nanoda-config.json")]
    require(two.get("recording_complete") is True and two.get("inputs_unchanged") is True
            and two.get("policy_changes_by_recorder") is False
            and integer(two.get("checker_exit_code"), code) and integer(two.get("wrapper_exit_code"), code)
            and two.get("effective_policy") == effective == wanted
            and all(two.get(k) == v for k, v in zero.items())
            and one.get("checker_argv") == two.get("checker_argv") == argv
            and two.get("wrapper_argv") == [g.path(recorder), argv[1]]
            and two.get("mode") == "native_fake_landrun_unsandboxed"
            and g.p.closed_times(two.get("started_at"), two.get("finished_at")), "actual Nano result/policy/argv differs")
    for field in ("binary_before", "binary_after"):
        g.reference(two[field], binary, binary_sha, 1260088)
    for field in ("export_before", "export_after"):
        require(same_identity(two[field], export), "actual checked export differs")
    config_name = folder + "/additional-nanoda-config.json"
    for field in ("config_before", "config_after"):
        g.bind(two[field], config_name)
    g.bind(two["config_archive"], names[3])
    require(g.read(config_name) == g.read(names[3]), "forwarded config and archive bytes differ")
    g.reference(two["wrapper_source"], recorder, RECORDER_SHA, 8494)
    archive = two["export_archive"]
    require(archive.get("uncompressed_sha256") == export["sha256"]
            and integer(archive.get("uncompressed_size_bytes"), export["size_bytes"])
            and same_identity(summary.get("gzip", {}), archive.get("gzip", {}))
            and integer(summary.get("checker_exit_code"), code), "actual checked gzip summary differs")
    g.reference(archive["gzip"], record + "/export.ndjson.gz")
    return two, record, {"receipt": name, "raw_sha256": export["sha256"], "raw_size_bytes": export["size_bytes"],
                         "gzip_sha256": archive["gzip"]["sha256"], "gzip_size_bytes": archive["gzip"]["size_bytes"],
                         "recording_complete": True, "checker_exit_code": code,
                         "recorded_checker_accepted": code == 0,
                         "availability": "Actual checked archive retained locally, not published",
                         "identity_source": "Closed reviewed aggregate and actual checker receipts; packager does not rehash large assets"}


def tool_metadata(g):
    for name, digest in PINS.items():
        require(g.p.sha(g.read(TOOLS + "/" + name, "source" if name.endswith(".py") else "manifest")) == digest,
                "reviewed resource metadata/source changed: " + name)
    provenance = g.obj(TOOLS + "/source-provenance-r1.json")
    require(provenance.get("base_commit") == "68d5ca9db226849b41a6fff59d796ff19d0a8840"
            and integer(provenance.get("tracked_files"), 29) and provenance.get("source_input_set_exact") is True
            and provenance.get("hardlinks_used") is False and provenance.get("only_changed") == ["src/lib.rs"]
            and provenance.get("tc_rs_unchanged") is True and provenance.get("Cargo_lock_unchanged") is True
            and integer(provenance.get("resource_constant_before"), 16777216)
            and integer(provenance.get("resource_constant_after"), 268435456), "source derivation metadata differs")
    before = provenance["original_before"]; after = provenance["copy_after"]
    require(len(before) == len(after) == 29 and len({r["relative_path"] for r in before}) == 29
            and {r["relative_path"] for r in before} == {r["relative_path"] for r in after}, "exact29 provenance row set differs")
    g.reference(provenance["preserved"]["original_binary"], OLD_BINARY, OLD_BINARY_SHA, 1260088)
    manifest, build = g.obj(TOOLS + "/tool-manifest-r1.json"), g.obj(TOOLS + "/build-result-r1.json")
    for row in (manifest["binaries"]["nanoda"], build["new_binary"]):
        g.reference(row, BINARY, BINARY_SHA, 1260088)
    require(manifest.get("source_constant_delta") == {"file": "src/lib.rs", "constant": "STACK_SIZE", "before": 16777216, "after": 268435456}
            and manifest.get("checker_logic_patch") is False and build.get("status") == "passed"
            and integer(build.get("exit_code"), 0) and build.get("original_source_binary_recorder_manifest_unchanged") is True,
            "resource-only build did not close")
    raw_name = TOOLS + "/build-r1.raw.log"
    raw = g.bind(build["raw"], raw_name, "completed_log")
    g.logs[raw_name] = {"receipt": TOOLS + "/build-result-r1.json", "exit_code": 0,
                        "timed_out": False, "raw_log_sha256": g.p.sha(raw), "raw_log_bytes": len(raw),
                        "scope": "Closed resource-tool build output, including warnings; not a proof checker verdict"}
    return manifest, build


def retry_bundle(g, export):
    folder = RETRY
    result = g.obj(folder + "/retry-result.json", "completed_receipt")
    prepared = g.obj(folder + "/retry-prepared.json")
    inputs = json.loads(g.bind(result["retry_inputs"], folder + "/retry-inputs.json"))
    require(result.get("schema") == "openai-native-resource-retry/1" and result.get("status") == "passed"
            and result.get("protocol_variant") == PROTOCOL and result.get("logical_check") == "extra-nanoda"
            and result.get("original_r2_attempt_passed") is False and result.get("interrupt_signal") is None
            and result.get("record_directory") == g.path(folder) and result.get("base_r2_input_fingerprint") == FP
            and result.get("resource_policy") == POLICY and inputs.get("resource_policy") == POLICY
            and inputs.get("schema") == "openai-native-resource-retry-inputs/1"
            and inputs.get("protocol_variant") == PROTOCOL and inputs.get("base_r2_input_fingerprint") == FP
            and inputs.get("export_input") == export and inputs.get("config_delta") == {}
            and prepared.get("started_utc") == result.get("started_utc") and prepared.get("protocol_variant") == PROTOCOL
            and g.p.closed_times(result.get("started_utc"), result.get("finished_utc")), "worker retry is not explicitly closed")
    g.bind(inputs["retry_source"], HELPER, "source")
    require(inputs["retry_source"]["sha256"] == HELPER_SHA, "retry helper differs")
    worker = json.loads(g.bind(result["worker_resource"], folder + "/worker-resource.json"))
    stage, raw = g.stage(folder, "worker-stack256-nanoda", result, inputs, 0)
    g.bind(result["stage_finished"], folder + "/stages/worker-stack256-nanoda/finished.json")
    env = inputs["environment"]
    require(worker.get("schema") == "native-nanoda-worker-resource/2" and worker.get("protocol_variant") == PROTOCOL
            and worker.get("resource_policy") == POLICY and worker.get("resource_inputs") == inputs.get("resource_inputs")
            and worker.get("environment") == env and worker.get("environment_keys") == inputs.get("environment_keys") == sorted(env)
            and worker.get("retry_source") == inputs["retry_source"]
            and worker.get("main_stack_limits_before") == worker.get("main_stack_limits_after")
            and isinstance(worker.get("main_stack_limits_before"), list) and len(worker["main_stack_limits_before"]) == 2
            and all(type(v) is int for v in worker["main_stack_limits_before"])
            and worker.get("main_stack_limits_changed") is False and worker.get("actual_nanoda_worker_extent_measured") is False
            and type(worker.get("pid")) is int and worker["pid"] == worker.get("pgid")
            and g.p.sha(env.get(CF_KEY, "").encode()) == CF_SHA
            and env.get("NANODA_REAL_BINARY") == g.path(BINARY), "actual resource event/environment differs")
    events = [json.loads(line[len(b"WORKER_RESOURCE "):]) for line in raw.splitlines() if line.startswith(b"WORKER_RESOURCE ")]
    require(events == [worker], "actual worker raw event differs")
    python = inputs["argv"][0]
    require(inputs["argv"] == [python, g.path(HELPER), "--child", g.path(folder)]
            and inputs.get("cwd") == worker.get("cwd") == g.path("openai/workspace")
            and integer(inputs.get("timeout_seconds"), 7200)
            and worker.get("exec_argv") == [python, g.path(TOOLS + "/record_nanoda.py"), g.path(folder + "/additional-nanoda-config.json")],
            "resource child command differs")
    for short, digest in {**PINS, "target/release/nanoda_bin": BINARY_SHA}.items():
        row = inputs["resource_inputs"][short]
        g.reference(row, TOOLS + "/" + short, digest)
    two, record, asset = nano(g, folder, result["nanoda"], export, 0, BINARY, BINARY_SHA, TOOLS + "/record_nanoda.py")
    require(Path(record).name.startswith("nanoda-" + str(worker["pid"]) + "-"), "checker PID lineage differs")
    return {"result": result, "inputs": inputs, "stage": stage, "worker": worker, "two": two, "asset": asset}


def outer_failure(g, summary, receipt_name, raw_name, revision, code, digest, result):
    outer = json.loads(g.bind(summary["outer_receipt"], receipt_name))
    raw = g.read(raw_name, "completed_log")
    require(integer(outer.get("revision_event_id"), revision) and integer(outer.get("exit_code"), code)
            and outer.get("timed_out") is False and outer.get("log_sha256") == g.p.sha(raw) == digest
            and integer(outer.get("log_size"), len(raw)), "retained negative outer receipt differs")
    last = next((line for line in reversed(raw.splitlines()) if line.startswith(b'{"')), None)
    require(last is not None and json.loads(last) == result, "retained negative outer result differs")
    g.logs[raw_name] = {"receipt": receipt_name, "exit_code": code, "timed_out": False,
                        "raw_log_sha256": digest, "raw_log_bytes": len(raw)}


def mainstack_negatives(g):
    name = "publication/main-stack-negative-evidence-r1.json"
    require(g.p.sha(g.read(name)) == "2f73ad24b712336207a470162e4cf22c23653fb7e7e16ede19e0a811ccbe95f9",
            "fixed mainstack-negative copy receipt differs")
    receipt = g.obj(name)
    wanted = [(4023, 1, "publication/negative-evidence/main-stack-control-4023.txt", "98d16afaeeb99fbc1825464e49c478f4ea50fd8045e65b8846a779f4ff63ee1f", 642),
              (4025, 0, "publication/negative-evidence/main-stack-diagnostic-4025.txt", "2ca6a373b0aace5df3335b598d4a02484a68a560796979a8c980ff5e4b903f6d", 5772)]
    require(receipt.get("schema") == "eth-closed-mainstack-negative-copies/1" and len(receipt.get("records", [])) == 2,
            "mainstack-negative copy set differs")
    for row, (revision, code, path, digest, size) in zip(receipt["records"], wanted):
        raw = g.read(path, "completed_log")
        require(integer(row.get("checkpoint_revision"), revision) and integer(row.get("checkpoint_exit_code"), code)
                and row.get("copy_path") == path and row.get("copied_byte_identical") is True
                and row.get("source_sha256") == row.get("copy_sha256") == g.p.sha(raw) == digest
                and integer(row.get("source_size_bytes"), size) and integer(row.get("copy_size_bytes"), size)
                and len(raw) == size, "closed mainstack negative bytes differ")
        g.logs[path] = {"receipt": name, "exit_code": code, "timed_out": False,
                        "raw_log_sha256": digest, "raw_log_bytes": size,
                        "scope": "Harmless main-stack diagnostic/control; no Nanoda proof execution or positive kernel verdict"}


def native_retry_bundle(base, name, publisher):
    require(name == RETRY + "/retry-result.json", "only actual R3 worker retry is admitted")
    g = Gate(base, publisher)
    export = {"path": g.path(EXPORT_NAME), "sha256": EXPORT_SHA, "size_bytes": EXPORT_SIZE}
    bundle = retry_bundle(g, export)
    return {**bundle, "files": g.files, "closed_log_bindings": g.logs}


def native_final_selection(base, map_name, publisher):
    g = Gate(base, publisher)
    require(re.fullmatch(r"publication/native-final-selection-r[1-9][0-9]*\.json", map_name), "native map root differs")
    selection = g.obj(map_name)
    aggregate = selection.get("aggregate_directory", "")
    require(selection.get("schema") == "eth-native-final-selection/2"
            and aggregate == "openai/native-aggregate-records/worker-stack256-r7-01"
            and set(selection.get("aggregate_files", {})) == AGG_FILES, "worker aggregate map differs")
    for short, row in selection["aggregate_files"].items():
        g.bind(row, aggregate + "/" + short, "report" if short.endswith(".md") else "manifest")
    closing, prepared = g.obj(aggregate + "/aggregation-finished.json"), g.obj(aggregate + "/aggregation-prepared.json")
    result_name = aggregate + "/native-replication-result.json"
    result = json.loads(g.bind(closing["result"], result_name))
    g.bind(prepared["aggregator"], AGGREGATOR, "source")
    require(closing.get("schema") == prepared.get("schema") == "openai-native-aggregation/1"
            and closing.get("status") == "passed" and prepared.get("proof_execution") is False
            and prepared["aggregator"]["sha256"] == AGGREGATOR_SHA, "reviewed worker aggregate has no closing seal")
    artifacts = g.obj(aggregate + "/native-replication-artifacts.json")
    require(result.get("format") == "openai-eth-native-replication-result-v2" and result.get("protocol_variant") == PROTOCOL
            and result.get("all_required_native_checks_passed") is True and result.get("original_r2_protocol_passed") is False
            and result.get("verbatim_upstream_linux_ci_reproduction") is False
            and result.get("selected_input_fingerprint") == FP
            and artifacts.get("artifacts") == result.get("artifacts")
            and artifacts.get("public_small_artifacts") == result.get("public_small_artifacts"), "worker aggregate verdict/artifacts differ")
    require([r.get("name") for r in result.get("phases", [])] == list(PHASES), "seven original plus retry phases missing")
    phase_rows = {r["name"]: r for r in result["phases"]}
    for phase in ORIGINAL:
        i = PHASES.index(phase) + 1
        folder = "openai/native-phase-records/r2-" + str(i).zfill(2) + "-" + phase
        name = folder + "/phase-result.json"; row = phase_rows[phase]
        require(row.get("directory") == g.path(folder) and row.get("protocol") == "original-r2", "original phase location/protocol differs")
        g.bind(row["result"], name, "completed_receipt")
        bundle = publisher.native_phase_bundle(g.base, name)
        require(bundle["result"]["input_fingerprint"] == FP and bundle["inputs"]["selected_inputs"] == result["selected_inputs"]
                and row.get("stage") == bundle["result"]["stage_receipts"][0], "original phase aggregate lineage differs")
        for item in bundle["files"]:
            g.read(item, "completed_log" if item.endswith("raw.log") else "completed_receipt" if item == name else "manifest")
        raw_name, digest, size = bundle["raw"]
        g.logs[raw_name] = {"receipt": name, "exit_code": 0, "timed_out": False, "raw_log_sha256": digest, "raw_log_bytes": size}
    export_phase = g.obj("openai/native-phase-records/r2-05-selected-export/phase-result.json")
    export = export_phase["export"]; g.reference(export, EXPORT_NAME, EXPORT_SHA, EXPORT_SIZE)
    capture = json.loads(g.bind(export_phase["capture_receipt"], "openai/native-phase-records/r2-05-selected-export/export-capture.json"))
    require(capture.get("schema") == "native-direct-fd-export/2" and capture.get("complete") is True
            and integer(capture.get("child_exit_code"), 0) and capture.get("export") == export, "selected export not closed")
    tool_metadata(g)
    retry = retry_bundle(g, export)
    row = phase_rows["extra-nanoda"]
    require(row.get("protocol") == "explicit-resource-retry" and row.get("directory") == g.path(RETRY)
            and row.get("stage") == retry["stage"], "aggregate worker retry differs")
    g.bind(row["result"], RETRY + "/retry-result.json", "completed_receipt")
    g.bind(result["retry_source"], HELPER, "source")
    extra = result["additional_nanoda"]
    require(extra.get("resource_policy") == POLICY and extra.get("actual_worker_resource_event") == retry["worker"]
            and extra.get("resource_build_inputs") == retry["inputs"]["resource_inputs"]
            and extra.get("actual_export") == export and same_identity(extra.get("retained_gzip", {}), retry["two"]["export_archive"]["gzip"]),
            "aggregate independent checker lineage differs")
    # Retain both real negative attempts. They cannot be relabeled as successes.
    failure = result["retained_original_nanoda_failure"]
    require(failure.get("directory") == g.path(FAILED), "original failure directory differs")
    failed_result = json.loads(g.bind(failure["phase_result"], FAILED + "/phase-result.json", "completed_receipt"))
    failed_inputs = g.obj(FAILED + "/phase-inputs.json")
    g.obj(FAILED + "/phase-prepared.json")
    require(failed_result.get("status") == "failed" and failed_result.get("phase") == "extra-nanoda"
            and failed_result.get("input_fingerprint") == failed_inputs.get("input_fingerprint") == FP,
            "original failure no longer retained")
    failed_stage, failed_raw = g.stage(FAILED, "extra-nanoda", failed_result, failed_inputs, -6)
    require(publisher.sha(failed_raw) == "590ccc60513da51ab0aad98c32b68c0f485d0fda4958c7255feb5175c55bc4e2"
            and len(failed_raw) == 101 and b"stack overflow" in failed_raw and failure.get("stage") == failed_stage,
            "original overflow evidence differs")
    _, _, old_asset = nano(g, FAILED, failure["nanoda"], export, -6, OLD_BINARY, OLD_BINARY_SHA, "verification-tools/record_nanoda.py")
    require(old_asset["gzip_sha256"] == "c9408fc5dedf81e411e1a259c160804b10f8ae8ccce6b2abefff2170c0cbb789"
            and old_asset["gzip_size_bytes"] == 453732564, "original failed archive identity differs")
    outer_failure(g, failure, "openai/logs/native-r2-extra-nanoda-checkpoint.json", "openai/logs/native-r2-extra-nanoda-checkpoint.txt",
                  4013, 125, "0599976a37cdc35a45d160484af270befd31eeae4f440c90af69bd4381cc8ca4", failed_result)
    negative = result["retained_resource_preexec_environment_failure"]
    require(negative.get("directory") == g.path(PREEXEC) and negative.get("nano_launched") is False, "preexec failure missing")
    pre_result = json.loads(g.bind(negative["result"], PREEXEC + "/retry-result.json", "completed_receipt"))
    pre_inputs = json.loads(g.bind(negative["inputs"], PREEXEC + "/retry-inputs.json"))
    g.obj(PREEXEC + "/retry-prepared.json"); config(g, PREEXEC, export)
    require(pre_result.get("status") == "failed" and pre_result.get("protocol_variant") == "openai-native-r2-nanoda-worker-stack256-r2"
            and pre_result.get("original_r2_attempt_passed") is False, "preexec attempt relabeled")
    pre_stage, pre_raw = g.stage(PREEXEC, "worker-stack256-nanoda", pre_result, pre_inputs, 1)
    require(publisher.sha(pre_raw) == "f384b5c2c40e0e661b81aa604ae8672a24e6613b536aecba804ea25821090503"
            and len(pre_raw) == 848 and b"WORKER_RESOURCE " not in pre_raw and negative.get("stage") == pre_stage
            and not (g.base / PREEXEC / "worker-resource.json").exists()
            and not list((g.base / PREEXEC / "nanoda-records").glob("nanoda-*")), "preexec failure unexpectedly launched checker")
    require(publisher.sha(g.read("openai/nanoda_worker_stack_retry_r2.py", "source")) == "59931d7b0d00ba5651322e6a3e1efb9524223334ce74ee767891dd95534557fc"
            and publisher.sha(g.read(PREEXEC + "/retry-result.json")) == "d6b716803c4d9d36b02052bcd04b7cc40d38195973939c59ec2b25f628db627d",
            "preserved preexec source/result differs")
    outer_failure(g, negative, "openai/logs/native-worker-stack256-r2-checkpoint.json", "openai/logs/native-worker-stack256-r2-checkpoint.txt",
                  4044, 1, "694e0b7dc13d25a56f1d66996bae5d5820cc42704d3c71705549f6401f3ec72e", pre_result)
    mainstack_negatives(g)
    build = result["source_build"]
    build_name = str(Path(build["receipt"]["path"]).relative_to(g.base))
    require(build_name == "openai/logs/source-build-gated-r4-receipt.json", "source receipt root differs")
    wrapper = json.loads(g.bind(build["receipt"], build_name)); cp = wrapper["checkpoint_run_result"]
    build_raw = "openai/logs/source-build-gated-r4.txt"; raw = g.bind(build["raw"], build_raw, "completed_log")
    require(integer(wrapper.get("final_exec_exit_code"), 0) and integer(wrapper.get("exec_session_id"), 11317)
            and integer(cp.get("exit_code"), 0) and cp.get("timed_out") is False
            and cp.get("log_sha256") == publisher.sha(raw) and integer(cp.get("log_size"), len(raw))
            and re.search(rb"(?m)^Build completed successfully \([0-9]+ jobs\)\.$", raw), "source build closure differs")
    g.logs[build_raw] = {"receipt": build_name, "exit_code": 0, "timed_out": False, "raw_log_sha256": publisher.sha(raw), "raw_log_bytes": len(raw)}
    reviews = selection.get("reviews", [])
    require(len({r["path"] for r in reviews}) == len(reviews), "duplicate review")
    require(REQUIRED_REVIEWS <= {r["path"] for r in reviews}, "final combined review/report selection missing")
    for review in reviews:
        name = review["path"]; require(name in REVIEWS, "review is not explicitly named")
        g.bind({**review, "path": g.path(name)}, name, "report" if name.endswith(".md") else "manifest")
    return {"map": map_name, "map_sha256": publisher.sha(g.read(map_name)), "files": g.files,
            "omitted_large_assets": [retry["asset"], old_asset], "closed_log_bindings": g.logs,
            "scope": "Metadata-only publication validation; large assets/source trees/binaries not rehashed, proof or aggregation not rerun"}
