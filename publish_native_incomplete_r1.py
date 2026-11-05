#!/usr/bin/env python3
"""Separate publication route: original Lean coverage, additional Rust incomplete.

Reuses the exact reviewed publisher privately for allowlists, stable copies and
privacy. Its source and positive CLI are unchanged. Never invokes the positive
worker gate as an alternative, and never executes a checker or proof aggregator.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
CORE = "publish_package.py"
CORE_SHA = "a72ed2f73b37daaa375ee62c238897ba8e86c7549292bf5e3d6f1412fcc8675c"
GUARD = "publication/native_incomplete_guard_r1.py"
GUARD_SHA = "3c3d8696d58d90bead5a85da288b946d5c7bc995a6ede983f5c1fafd07706319"
PLAN_SCHEMA = "eth-native-incomplete-export-plan/1"
MODE = "original-lean-pass-additional-nanoda-incomplete"
VERDICT = "ORIGINAL_LEAN_SUITE_PASS_ADDITIONAL_NANODA_INCOMPLETE"
ADDED_SOURCES = {
    "publish_native_incomplete_r1.py", GUARD,
    "publication/check_incomplete_publisher_r1.py",
    "publication/check_incomplete_publisher_r2.py", "publication/check_incomplete_metadata_r1.py",
    "publication/publisher-incomplete-wrapper-provisional-023-r1.py",
    "openai/aggregate_native_incomplete_r1.py", "openai/aggregate_native_incomplete_r2.py",
}
ADDED_REPORTS = {
    "publication/native-incomplete-closure-source-review-r1.md",
    "publication/final-submission-structure-preparation-r1.md",
    "publication/native-incomplete-publication-design-r1.md",
    "openai/native-incomplete-closure-runbook-r1.md",
    "openai/native-incomplete-runbook-path-addendum-r1.md",
    "verification/nanoda-issue44-applicability-r1.md",
}
ADDED_MANIFESTS = {
    "publication/native-incomplete-closure-source-review-r1.json",
    "publication/submission-negative-path-preparation-manifest-r1.json",
    "publication/incomplete-publisher-control-result-r1.json",
    "publication/incomplete-publisher-control-result-r2.json", "publication/incomplete-metadata-control-result-r1.json",
    "openai/negative-closure-policy-controls-r1.json",
    "verification/nanoda-issue44-applicability-r1.json",
    "publication/native-publisher-integration-review-claims-r1.json",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_pinned(base, name, expected, label):
    path = base / name
    if path.is_symlink() or digest(path.read_bytes()) != expected:
        raise ValueError(label + " source is not the reviewed pin")
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def require_incomplete(selection):
    if (selection.get("publication_mode") != MODE or selection.get("verdict") != VERDICT
            or selection.get("original_lean_suite_passed") is not True
            or selection.get("all_required_native_checks_passed") is not False
            or selection.get("expanded_suite_passed") is not False
            or selection.get("independent_nanoda_acceptance_observed") is not False
            or "independent_nanoda_accepted" not in selection
            or selection.get("independent_nanoda_accepted") not in (None, False)
            or type(selection.get("independent_nanoda_accepted")) not in (type(None), bool)):
        raise ValueError("not the explicitly incomplete additional-Rust publication route")


def private_adapter(base=BASE):
    """Adapt one isolated module instance; never change the pinned source files."""
    core = load_pinned(base, CORE, CORE_SHA, "incomplete_route_reviewed_publisher")
    guard = load_pinned(base, GUARD, GUARD_SHA, "incomplete_route_reviewed_metadata_gate")
    # Only seven original successful results can enter the positive collection.
    core.NATIVE_POSITIVE_RESULTS = {n for n, phase in core.NATIVE_RESULTS.items() if phase != "extra-nanoda"}
    core.SOURCES |= ADDED_SOURCES; core.REPORTS |= ADDED_REPORTS; core.MANIFESTS |= ADDED_MANIFESTS
    def selection(artifact_base, name):
        result = guard.native_incomplete_selection(artifact_base, name, core.native_publisher_api())
        require_incomplete(result)
        return result
    # The reused slot is metadata plumbing, not a successful positive-map.
    # This private instance is never exposed through the original positive CLI.
    core.native_final_selection = selection
    return core


def validate_receipt_names(core, receipts):
    for name in receipts:
        if name.startswith("openai/native-") and name not in core.NATIVE_POSITIVE_RESULTS:
            raise ValueError("unsuccessful or unknown native check cannot be a positive receipt")


def make_plan(base, selection_name, receipts=(), with_ci=False):
    core = private_adapter(base)
    validate_receipt_names(core, receipts)
    plan = core.make_plan(base, list(receipts), with_ci=with_ci, native_final_map=selection_name)
    selection = plan["native_final"]; require_incomplete(selection)
    required = set(selection["files"]) | {CORE, GUARD, Path(__file__).name, "publication/native_worker_guard_r1.py"}
    if not required.issubset({r["path"] for r in plan["items"]}):
        raise ValueError("incomplete selection omitted required closed evidence")
    return {"schema": PLAN_SCHEMA, "publication_mode": MODE, "verdict": VERDICT,
            "expanded_suite_passed": False, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "publisher_sha256": CORE_SHA, "guard_sha256": GUARD_SHA,
            "wrapper_sha256": digest((BASE / Path(__file__).name).read_bytes()), "plan": plan,
            "scope": "Closed evidence publication only; no expanded-Rust acceptance, proof or closure execution"}


def export_plan(base, envelope, release):
    if (envelope.get("schema") != PLAN_SCHEMA or envelope.get("publication_mode") != MODE
            or envelope.get("verdict") != VERDICT or envelope.get("expanded_suite_passed") is not False
            or envelope.get("publisher_sha256") != CORE_SHA or envelope.get("guard_sha256") != GUARD_SHA
            or envelope.get("wrapper_sha256") != digest((BASE / Path(__file__).name).read_bytes())):
        raise ValueError("wrong publication route or changed reviewed source pins")
    core = private_adapter(base); plan = envelope["plan"]
    require_incomplete(plan.get("native_final", {}))
    if not {CORE, GUARD, Path(__file__).name, "publication/native_worker_guard_r1.py"}.issubset({r["path"] for r in plan.get("items", [])}):
        raise ValueError("incomplete-route plan omitted reviewed publication sources")
    validate_receipt_names(core, plan.get("receipt_paths", []))
    # Core revalidates the separate guard and all frozen inputs before mkdir.
    return core.export_plan(base, plan, release)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--incomplete-selection", required=True)
    plan.add_argument("--receipt", action="append", default=[])
    plan.add_argument("--with-ci", action="store_true")
    plan.add_argument("--output", type=Path, required=True)
    export = sub.add_parser("export")
    export.add_argument("--plan", type=Path, required=True); export.add_argument("--release", required=True)
    args = parser.parse_args()
    if args.command == "plan":
        result = make_plan(BASE, args.incomplete_selection, args.receipt, args.with_ci)
        core = private_adapter(BASE); core.save(args.output, result)
        print(json.dumps({"status": "incomplete-evidence-selection-prepared", "expanded_suite_passed": False,
                          "items": len(result["plan"]["items"]), "plan": str(args.output)}))
    else:
        print(json.dumps({**export_plan(BASE, json.loads(args.plan.read_text()), args.release),
                          "publication_mode": MODE, "expanded_suite_passed": False}))


if __name__ == "__main__": main()
