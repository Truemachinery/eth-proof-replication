#!/usr/bin/env python3
"""Small data-only privacy controls. Never print or save the SDK value."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import time
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publisher_privacy", BASE / "publish_package.py")
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


def main():
    start, cpu = time.monotonic(), time.process_time(); checks = []
    value = os.environ.get(pub.PRIVATE_SDK_KEY)
    assert value is not None and hashlib.sha256(value.encode()).hexdigest() == pub.PRIVATE_SDK_VALUE_SHA256
    def verify(raw, private, label, is_json=True):
        public, steps = pub.transform(raw, BASE, data_derivative=True)
        assert private not in public and pub.PRIVATE_SDK_VALUE_SHA256.encode() in public
        if is_json: json.loads(public)
        pub.check_public(public, data_derivative=True)
        current = raw
        for step in steps:
            assert pub.sha(current) == step["input_sha256"]
            parts = []; cursor = 0
            for span in step["replacements"]:
                parts += [current[cursor:span["input_byte_start"]], span["replacement"].encode()]
                cursor = span["input_byte_end"]
            current = b"".join(parts) + current[cursor:]
            assert pub.sha(current) == step["output_sha256"]
        assert current == public
        checks.append(label)
    raw = json.dumps({pub.PRIVATE_SDK_KEY: value, "value_sha256": pub.PRIVATE_SDK_VALUE_SHA256}).encode()
    for level in range(6):
        verify(raw, value.encode(), "actual SDK ordinary/nested JSON level " + str(level))
        raw = json.dumps({"outer": raw.decode()}).encode()
    verify(json.dumps({"unstructured_dump": value, "value_sha256": pub.PRIVATE_SDK_VALUE_SHA256}).encode(),
           value.encode(), "validated actual value redacted even outside named field")
    source = ('CF_KEY = "__CF_USER_TEXT_ENCODING"\nCF_VALUE_SHA256 = "' + pub.PRIVATE_SDK_VALUE_SHA256 + '"\n').encode()
    assert pub.transform(source, BASE, data_derivative=False) == (source, [])
    checks.append("source key/hash references remain byte-identical")
    fake = "0xABC:0xDEF:0x123"
    with patch.dict(os.environ):
        os.environ.pop(pub.PRIVATE_SDK_KEY, None)
        raw = json.dumps({pub.PRIVATE_SDK_KEY: fake, "value_sha256": pub.PRIVATE_SDK_VALUE_SHA256}).encode()
        for level in range(6):
            verify(raw, fake.encode(), "key-context fallback without parent SDK level " + str(level))
            raw = json.dumps({"outer": raw.decode()}).encode()
        for form in ["'__CF_USER_TEXT_ENCODING': '" + fake + "'", '__CF_USER_TEXT_ENCODING="' + fake + '"']:
            verify((form + "\nvalue_sha256=" + pub.PRIVATE_SDK_VALUE_SHA256 + "\n").encode(),
                   fake.encode(), "repr/assignment SDK data form", False)
        unrelated = json.dumps({"unrelated": fake, "value_sha256": pub.PRIVATE_SDK_VALUE_SHA256}).encode()
        assert pub.transform(unrelated, BASE, data_derivative=True) == (unrelated, [])
        checks.append("unrelated hex triples preserved")
        try: pub.check_public(json.dumps({pub.PRIVATE_SDK_KEY: fake}).encode(), data_derivative=True)
        except ValueError: checks.append("unredacted named SDK field refused")
        else: raise AssertionError("raw SDK field accepted")
    ci = pub.CI_ALL | pub.STAGING_INPUTS
    for name in ci:
        raw = (BASE / name).read_bytes()
        assert pub.transform(raw, BASE, data_derivative=name not in pub.SOURCES)[0] == raw
    checks.append("all50 original/candidate CI files remain byte-identical")
    report = {"schema": "eth-private-sdk-redaction-controls/1", "status": "passed", "checks": checks,
              "sdk_value_sha256_only": pub.PRIVATE_SDK_VALUE_SHA256,
              "sdk_value_printed_or_persisted": False, "publisher_sha256": pub.sha((BASE / "publish_package.py").read_bytes()),
              "source_sha256": pub.sha(Path(__file__).read_bytes()), "cpu_seconds": time.process_time() - cpu,
              "wall_seconds": time.monotonic() - start, "no_proof_network_or_export": True}
    pub.save(BASE / "publication/sdk-redaction-control-result-r2.json", report)
    print(json.dumps({"status": report["status"], "checks": len(checks), "publisher_sha256": report["publisher_sha256"],
                      "report_sha256": pub.sha((BASE / "publication/sdk-redaction-control-result-r2.json").read_bytes()),
                      "cpu_seconds": report["cpu_seconds"], "wall_seconds": report["wall_seconds"]}))


if __name__ == "__main__":
    main()
