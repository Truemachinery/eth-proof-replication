#!/usr/bin/env python3
"""Run one explicitly selected native verification phase after source build closure.

No automatic phase ordering, skipping, aggregation or resume. Root owns execution.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

sys.dont_write_bytecode = True

BASE = Path(__file__).resolve().parent
TREE = BASE.parent
WORKSPACE = BASE / "workspace"
REAL = BASE / "elan/toolchains/leanprover--lean4---v4.34.1"
RECORD_ROOT = BASE / "native-phase-records"
MODULE = "OAI.Algorithms.SubexponentialSAT.Main"
CHALLENGE = "ComparatorChallenges.SubexponentialSAT"
TARGET = "OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat"
AXIOMS = ["propext", "Quot.sound", "Classical.choice"]
CONFIG = BASE / "source/lean/ComparatorChallenges/SubexponentialSAT.json"
TOOLS = TREE / "verification-tools"
COMPARATOR = TOOLS / "comparator-source/.lake/build/bin/comparator"
EXPORTER = TOOLS / "lean4export-434-source/.lake/build/bin/lean4export"
NANODA = TOOLS / "nanoda-source/target/release/nanoda_bin"
SHIM = TOOLS / "comparator-source/scripts/fake-landrun.sh"
NANODA_RECORDER = TOOLS / "record_nanoda.py"
CAPTURE = BASE / "native_export_capture_r2.py"
TIMEOUTS = {"pre-identity": 300, "trace": 600, "audit": 1800, "comparator": 7200,
            "selected-export": 1800, "extra-nanoda": 7200, "original-fresh": 7200,
            "post-identity": 300}
PINS = {
    "native-recorder-r1/record.py": "1a7c9f9d8bbf7de0458e83ea0385a280c05db970b2e87493f3e85a6c06c361c0",
    "in_workspace.py": "b4e80df9ed1f1c71e7a202feccd94f189113610679d4a28ac3728d8708e7d04a",
    "verify_source_identity_r3.py": "52cb3de32ef89c5fbb460032601693a9d2e740cda296b8dd44f9ab6fd1fa9174",
    "identity_expectations_r1.json": "e39147fee63287baea89a046c85c462090f1c443f15b53d809e613631f0cce47",
    "source-manifest.json": "bf7f36120177010243e52dd9053bd3e9f97f92fa35184abf173a8a57ef4843e1",
    "workspace-config-r2.json": "a56c999ec870742bee9c51be2bb3199d358d77876d5e7d49492f5ad880938413",
    "workspace/lake-manifest.json": "4aa8b01a11ed34de463651ed6396d9da61f365cccfd158e82e96bbd17bcb14bc",
    "source/lean/ComparatorChallenges/SubexponentialSAT.json": "debbfdc9c01104d2369be80da5180978275106df8b685f693fba7ce7da7c5b19",
    "../verification/AuditTargets.lean": "a78f30e0439e85d3a9ae51828e0e42c248c027a7fcfeb4c4fb16cb776fae0b05",
    "../verification-tools/comparator-source/.lake/build/bin/comparator": "bdf09ee3e725f1480792db7b5befcbf6e4f77db90d9f1f4986bda5a1e6315f4c",
    "../verification-tools/lean4export-434-source/.lake/build/bin/lean4export": "e6217f95bf55c5e165a62f12ec6ce1fb3c25a815cff0f9cb6f6dfcf4c8e55e25",
    "../verification-tools/nanoda-source/target/release/nanoda_bin": "d9a1fc5371b84c9eb0687a7630eb724fa88886d9f5d665f09f9f926730573b80",
    "../verification-tools/comparator-source/scripts/fake-landrun.sh": "167507c89d8b3c7667ad78b50df7b19f89883751a01efd1457404fa34a994e8b",
    "../verification-tools/record_nanoda.py": "c34f36d630d182708937a5280b6eda8d0723fa0ffdd85caf8fc54af17b332f48",
    "native_export_capture_r2.py": "4755ba1dd43d18509cd1472bca98c269c79e3dc5a3c99f41faff5b2e6d78be74",
}
NATIVE_CPU_SCOPE = ("Native execution, no systemd-managed service. Recorder child_cpu_seconds covers "
                    "reaped child processes/descendants, including capture and checker wrappers. "
                    "Do not add nested Nanoda CPU a second time. No RSS measurement is claimed.")
INTERRUPTED = None


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def identity(path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("not a regular pinned file: " + str(path))
    before = path.stat()
    digest = sha(path)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise RuntimeError("file changed while hashing: " + str(path))
    return {"path": str(path), "sha256": digest, "size_bytes": after.st_size}


def write_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def command(*args):
    return [sys.executable, str(BASE / "in_workspace.py"), *map(str, args)]


def export_command():
    return [str(EXPORTER), MODULE, "--", TARGET]


def capture_command(folder):
    # Lake supplies LEAN_PATH before capture starts; capture directly owns the SDK.
    return command("lake", "env", sys.executable, CAPTURE,
                   "--output", folder / "selected-solution.ndjson",
                   "--receipt", folder / "export-capture.json", "--", *export_command())


def selected_inputs():
    files = {}
    for name, wanted in PINS.items():
        path = Path(os.path.abspath(BASE / name))
        if path.resolve() != path:
            raise RuntimeError("pinned input resolves through a symlink: " + name)
        row = identity(path)
        if row["sha256"] != wanted:
            raise RuntimeError("pinned input mismatch: " + name)
        files[name] = row
    configuration = json.loads((BASE / "workspace-config-r2.json").read_text())
    for row in configuration["workspace_config"]:
        actual = identity(WORKSPACE / row["path"])
        if actual["sha256"] != row["sha256"]:
            raise RuntimeError("workspace configuration drift: " + row["path"])
        files["workspace/" + row["path"]] = actual
    expectations = json.loads((BASE / "identity_expectations_r1.json").read_text())
    if REAL.is_symlink() or REAL.resolve() != REAL.absolute():
        raise RuntimeError("original runtime prefix resolves through an override")
    for row in expectations["expected_runtime_files"]:
        actual = identity(REAL / row["path"])
        if actual["sha256"] != row["sha256"] or actual["size_bytes"] != row["size_bytes"]:
            raise RuntimeError("original runtime drift: " + row["path"])
        files["real4341/" + row["path"]] = actual
    config = json.loads(CONFIG.read_text())
    if (config["challenge_module"] != CHALLENGE or config["solution_module"] != MODULE
            or config["theorem_names"] != [TARGET] or config["definition_names"] != []
            or config["permitted_axioms"] != AXIOMS or config["enable_nanoda"] is not False
            or config.get("external_kernels")):
        raise RuntimeError("original Comparator contract/configuration differs")
    content = {"files": files, "launcher": identity(Path(__file__).resolve()),
               "module": MODULE, "challenge": CHALLENGE, "theorems": [TARGET],
               "original_comparator_nanoda_enabled": False}
    fingerprint = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return content, fingerprint


def owned_folder(value):
    path = Path(value).absolute()
    if RECORD_ROOT.resolve() != RECORD_ROOT.absolute() or path.resolve() != path:
        raise RuntimeError("record directory must not resolve through symlinks")
    relative = path.relative_to(RECORD_ROOT)
    if not relative.parts:
        raise RuntimeError("choose an exclusive child record directory")
    return path


def environment(folder):
    (folder / "home").mkdir()
    (folder / "tmp").mkdir()
    paths = [REAL / "bin", Path(sys.executable).resolve().parent,
             Path("/usr/bin"), Path("/bin"), Path("/usr/sbin"), Path("/sbin"), Path("/opt/homebrew/bin")]
    return {"PATH": os.pathsep.join(map(str, dict.fromkeys(paths))),
            "HOME": str(folder / "home"), "TMPDIR": str(folder / "tmp"),
            "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1", "ELAN_HOME": str(BASE / "elan"),
            "XDG_CACHE_HOME": str(BASE / "cache"), "MATHLIB_CACHE_DIR": str(BASE / "cache/mathlib"),
            "LEAN_SYSROOT": str(REAL), "LEAN_NUM_THREADS": "2", "LEAN_ABORT_ON_PANIC": "1",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1"}


def closed_export(folder, fingerprint):
    folder = owned_folder(folder)
    result = json.loads((folder / "phase-result.json").read_text())
    if (result.get("schema") != "openai-native-phase/1" or result.get("phase") != "selected-export"
            or result.get("status") != "passed" or result.get("input_fingerprint") != fingerprint
            or result.get("record_directory") != str(folder)):
        raise RuntimeError("supply a closed successful selected-export phase with identical pinned inputs")
    if sha(folder / "phase-inputs.json") != result["phase_inputs"]["sha256"]:
        raise RuntimeError("export phase inputs changed")
    inputs = json.loads((folder / "phase-inputs.json").read_text())
    if inputs["phase"] != "selected-export" or inputs["input_fingerprint"] != fingerprint:
        raise RuntimeError("export phase input binding differs")
    finished = folder / "stages/selected-export/finished.json"
    if sha(finished) != result["stage_finished"]["sha256"]:
        raise RuntimeError("export stage receipt changed")
    receipt = json.loads(finished.read_text())
    if receipt["exit_code"] != 0 or receipt["reason"] is not None or receipt["argv"] != capture_command(folder):
        raise RuntimeError("export stage was not the exact successful capture command")
    if sha(folder / "stages/selected-export/raw.log") != receipt["raw_log_sha256"]:
        raise RuntimeError("export stage raw log changed")
    actual = identity(folder / "selected-solution.ndjson")
    if sha(folder / "export-capture.json") != result["capture_receipt"]["sha256"]:
        raise RuntimeError("export capture receipt changed")
    capture = json.loads((folder / "export-capture.json").read_text())
    if (not capture["complete"] or capture["child_exit_code"] != 0 or capture["argv"] != export_command()
            or capture["export"] != actual or result["export"] != actual or actual["size_bytes"] == 0):
        raise RuntimeError("closed export bytes/capture binding differ")
    return actual


def audit_result(raw):
    rows = [json.loads(line) for line in raw.read_text().splitlines() if line.strip()]
    env = [x for x in rows if x.get("event") == "environment"]
    targets = [x for x in rows if x.get("event") == "target"]
    done = [x for x in rows if x.get("event") == "complete"]
    if (len(rows) != 3 or len(env) != 1 or len(targets) != 1 or len(done) != 1
            or any(x.get("schema") != "eth-target-axiom-audit/1" or x.get("module") != MODULE for x in rows)
            or env[0]["module"] != MODULE or env[0]["initializer_execution_enabled"]
            or env[0]["load_extensions"] or env[0]["load_level"] != "private"
            or set(env[0]["permitted_axioms"]) != set(AXIOMS)
            or not env[0]["standard_axiom_signature_check"]
            or targets[0]["target"] != TARGET or not targets[0]["passed"]
            or targets[0]["disallowed_axioms"] or not set(targets[0]["axioms"]) <= set(AXIOMS)
            or not done[0]["passed"] or done[0]["targets_checked"] != 1):
        raise RuntimeError("named-target audit did not supply the expected complete acceptance")
    return rows


def nanoda_result(folder, config, export):
    directories = sorted((folder / "nanoda-records").glob("nanoda-*"))
    if len(directories) != 1:
        raise RuntimeError("expected exactly one newly recorded Nanoda invocation")
    parent = directories[0]
    prepared = json.loads((parent / "00-prepared.json").read_text())
    launched = json.loads((parent / "01-started.json").read_text())
    result = json.loads((parent / "02-finished.json").read_text())
    if (not result["recording_complete"] or not result["inputs_unchanged"]
            or result["checker_exit_code"] != 0 or result["wrapper_exit_code"] != 0
            or result["policy_changes_by_recorder"] or result["effective_policy"] != config
            or result["checker_argv"] != [str(NANODA), str(folder / "additional-nanoda-config.json")]
            or result["export_before"]["sha256"] != export["sha256"]
            or result["export_archive"]["uncompressed_sha256"] != export["sha256"]):
        raise RuntimeError("Nanoda did not close with the exact strict policy and export")
    if prepared["effective_policy"] != config or launched["checker_argv"] != result["checker_argv"]:
        raise RuntimeError("Nanoda prepared/start/finish lineage differs")
    if sha(parent / "effective-config.json") != result["config_archive"]["sha256"]:
        raise RuntimeError("recorded effective Nanoda configuration changed")
    archive = identity(parent / "export.ndjson.gz")
    if archive["sha256"] != result["export_archive"]["gzip"]["sha256"]:
        raise RuntimeError("recorded checked export archive changed")
    return {"finished_receipt": identity(parent / "02-finished.json"), "gzip": archive,
            "small_records": [identity(parent / name) for name in
                              ["00-prepared.json", "01-started.json", "02-finished.json", "effective-config.json"]],
            "meaning": "Additional pinned Nanoda on separately selected export; original Comparator disables Nanoda."}


def interrupted(signum, frame):
    global INTERRUPTED
    INTERRUPTED = signum
    # Raising through Recorder.run invokes its process-group kill/wait and closes its receipt.
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    raise KeyboardInterrupt("native phase interrupted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=list(TIMEOUTS))
    parser.add_argument("--record-directory", required=True)
    parser.add_argument("--export-phase", help="closed selected-export record directory; extra-nanoda only")
    args = parser.parse_args()
    if (args.phase == "extra-nanoda") != bool(args.export_phase):
        parser.error("only extra-nanoda requires --export-phase")
    folder = owned_folder(args.record_directory)
    folder.mkdir(parents=True, exist_ok=False)
    result = {"schema": "openai-native-phase/1", "phase": args.phase, "status": "failed",
              "record_directory": str(folder), "started_utc": utc(),
              "accounting": NATIVE_CPU_SCOPE,
              "scope": "One explicit phase only; root aggregates all required closed results. Native mode has no Linux isolation."}
    write_json(folder / "phase-prepared.json", result)
    code = 125
    recorder = None
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        content, fingerprint = selected_inputs()
        result["input_fingerprint"] = fingerprint
        env = environment(folder)
        argv = None
        required = None
        config = None
        export = None
        if args.phase in {"pre-identity", "post-identity"}:
            argv = command(sys.executable, BASE / "verify_source_identity_r3.py")
        elif args.phase == "trace":
            argv = command("lake", "--no-build", "build", "+" + MODULE, "+" + CHALLENGE)
        elif args.phase == "audit":
            argv = command("lake", "env", "lean", "--run", TREE / "verification/AuditTargets.lean", MODULE, TARGET)
        elif args.phase == "comparator":
            env.update(COMPARATOR_LANDRUN=str(SHIM), COMPARATOR_LEAN4EXPORT=str(EXPORTER))
            argv = command("lake", "env", COMPARATOR, CONFIG)
            required = "Your solution is okay!"
        elif args.phase == "selected-export":
            argv = capture_command(folder)
        elif args.phase == "extra-nanoda":
            export = closed_export(args.export_phase, fingerprint)
            config = {"use_stdin": False, "export_file_path": export["path"], "permitted_axioms": AXIOMS,
                      "unpermitted_axiom_hard_error": True, "num_threads": 2,
                      "nat_extension": True, "string_extension": True}
            write_json(folder / "additional-nanoda-config.json", config)
            env.update(COMPARATOR_LANDRUN=str(SHIM), NANODA_REAL_BINARY=str(NANODA),
                       REPLICATION_CHECKER_RECORD_DIR=str(folder / "nanoda-records"))
            argv = command(sys.executable, NANODA_RECORDER, folder / "additional-nanoda-config.json")
        elif args.phase == "original-fresh":
            argv = command("lake", "env", REAL / "bin/leanchecker", "--fresh", MODULE)
        write_json(folder / "phase-inputs.json", {"phase": args.phase, "input_fingerprint": fingerprint,
                   "selected_inputs": content, "argv": argv, "cwd": str(WORKSPACE),
                   "environment_keys": sorted(env), "environment": env,
                   "timeout_seconds": TIMEOUTS[args.phase], "export_input": export,
                   "native_accounting": NATIVE_CPU_SCOPE})
        spec = importlib.util.spec_from_file_location("native_phase_recorder", BASE / "native-recorder-r1/record.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        recorder = module.Recorder(folder / "stages")
        receipt = recorder.run(args.phase, argv, WORKSPACE, env, timeout=TIMEOUTS[args.phase], required_text=required)
        raw = folder / "stages" / args.phase / "raw.log"
        if args.phase in {"pre-identity", "post-identity"}:
            identity_result = json.loads(raw.read_text())
            if (identity_result.get("schema") != "openai-native-input-identity/1"
                    or not identity_result["all_pinned_input_checks_passed"] or identity_result["failures"]):
                raise RuntimeError("identity phase did not report complete acceptance")
            result["identity_metadata"] = identity_result
        elif args.phase == "audit":
            result["audit_events"] = audit_result(raw)
        elif args.phase == "selected-export":
            capture = json.loads((folder / "export-capture.json").read_text())
            exported = identity(folder / "selected-solution.ndjson")
            if not capture["complete"] or capture["child_exit_code"] != 0 or capture["export"] != exported or exported["size_bytes"] == 0:
                raise RuntimeError("direct-FD export capture did not close successfully")
            result["export"] = exported
            result["capture_receipt"] = identity(folder / "export-capture.json")
            result["export_mode"] = "Direct child stdout FD, periodic/final fsync; unchanged Recorder handles stderr/control receipt and timeout group."
        elif args.phase == "extra-nanoda":
            result["nanoda"] = nanoda_result(folder, config, export)
        elif args.phase == "original-fresh":
            result["fresh_scope"] = "Original4.34.1 same-kernel safe/nonpartial imported-environment replay; axiom declarations admitted, constructors/recursors postchecked. Separate axiom/statement/Nanoda phases remain required."
        result["stage_finished"] = identity(folder / "stages" / args.phase / "finished.json")
        result["phase_inputs"] = identity(folder / "phase-inputs.json")
        result["status"] = "passed"
        code = 0
    except BaseException as error:
        result["error"] = type(error).__name__ + ": " + str(error)
        if isinstance(error, subprocess.CalledProcessError):
            code = error.returncode if 0 < error.returncode < 256 else 125
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        result.update(finished_utc=utc(), interrupt_signal=INTERRUPTED,
                      stage_receipts=recorder.receipts if recorder is not None else [])
        if INTERRUPTED is not None:
            result["status"] = "failed"
            code = 128 + INTERRUPTED
        write_json(folder / "phase-result.json", result)
        print(json.dumps(result, sort_keys=True), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
