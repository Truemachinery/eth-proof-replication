"""Bounded real-tool recorder probe using trusted Init only, never ETH modules."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import subprocess
import time

BASE = Path(__file__).resolve().parent


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, value):
    with p.open("x") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    folder = BASE / "recorder-probe-r1"
    folder.mkdir()
    result = {"scope": "Real Nanoda recorder probe on trusted Init.Nat.add_zero and malformed text; no ETH checks",
              "started": time.time(), "status": "running", "cases": []}
    try:
        wrapper = BASE / "record_nanoda.py"
        wrapper.chmod(0o755)
        real = BASE / "nanoda-source/target/release/nanoda_bin"
        prefix = BASE.parent / "openai/elan/toolchains/leanprover--lean4---v4.34.1"
        exporter = BASE / "lean4export-434-source/.lake/build/bin/lean4export"
        export = folder / "init-nat-add-zero.ndjson"
        command = [str(prefix / "bin/lake"), "--dir", str(BASE / "lean4export-434-source"),
                   "env", str(exporter), "Init", "--", "Nat.add_zero"]
        env = dict(os.environ, LEAN_SYSROOT=str(prefix), LEAN_NUM_THREADS="2",
                   COMPARATOR_LANDRUN=str(BASE / "comparator-source/scripts/fake-landrun.sh"),
                   REPLICATION_CHECKER_RECORD_DIR=str(folder / "records"), NANODA_REAL_BINARY=str(real))
        with export.open("xb") as f:
            p = subprocess.run(command, stdout=f, stderr=subprocess.PIPE, env=env, timeout=45)
            f.flush()
            os.fsync(f.fileno())
        result["export_command"] = command
        result["export_exit_code"] = p.returncode
        result["export_stderr"] = p.stderr.decode()
        if p.returncode:
            raise RuntimeError("trusted core export failed")
        result["export_sha256"] = digest(export)
        malformed = folder / "malformed.ndjson"
        with malformed.open("xb") as f:
            f.write(b"not valid ndjson\n")
            f.flush()
            os.fsync(f.fileno())
        for name, source in [("trusted_core", export), ("malformed", malformed)]:
            config = {"use_stdin": False, "export_file_path": str(source),
                      "permitted_axioms": ["propext", "Quot.sound", "Classical.choice"],
                      "unpermitted_axiom_hard_error": True, "num_threads": 2,
                      "nat_extension": True, "string_extension": True}
            path = folder / (name + "-config.json")
            save(path, config)
            before = set((folder / "records").glob("*")) if (folder / "records").exists() else set()
            wrapped = subprocess.run([str(wrapper), str(path)], capture_output=True, env=env,
                                     text=True, timeout=45)
            new = set((folder / "records").glob("*")) - before
            if len(new) != 1:
                raise AssertionError("expected one exclusive recorder directory")
            record = new.pop()
            receipt = json.loads((record / "02-finished.json").read_text())
            assert receipt["recording_complete"] and receipt["inputs_unchanged"]
            assert receipt["checker_exit_code"] == wrapped.returncode == receipt["wrapper_exit_code"]
            assert receipt["checker_argv"] == [str(real), str(path)]
            assert (record / "effective-config.json").read_bytes() == path.read_bytes()
            assert gzip.decompress((record / "export.ndjson.gz").read_bytes()) == source.read_bytes()
            assert receipt["export_archive"]["uncompressed_sha256"] == digest(source)
            assert receipt["export_archive"]["gzip"]["sha256"] == digest(record / "export.ndjson.gz")
            assert receipt["binary_before"]["sha256"] == digest(real)
            item = {"name": name, "wrapped_exit_code": wrapped.returncode,
                    "stdout": wrapped.stdout, "stderr": wrapped.stderr,
                    "receipt": str(record / "02-finished.json"),
                    "receipt_sha256": digest(record / "02-finished.json"),
                    "config_sha256": digest(path), "export_sha256": digest(source)}
            if name == "trusted_core":
                assert wrapped.returncode == 0
            else:
                direct = subprocess.run([str(real), str(path)], capture_output=True, text=True,
                                        env=env, timeout=30)
                assert direct.returncode != 0 and wrapped.returncode == direct.returncode
                item.update({"direct_exit_code": direct.returncode,
                             "direct_stdout": direct.stdout, "direct_stderr": direct.stderr})
            result["cases"].append(item)
        result.update({"status": "pass", "wrapper_sha256": digest(wrapper),
                       "elapsed_seconds": time.time() - result["started"]})
    except BaseException as error:
        result.update({"status": "failed", "error": type(error).__name__ + ": " + str(error),
                       "elapsed_seconds": time.time() - result["started"]})
        raise
    finally:
        save(folder / "probe-results.json", result)
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]),
                      "elapsed_seconds": result["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
