# Native OpenAI phase launcher

Prepared 2026-11-04 by `codex-eth-anthropic-replication`. This is a launcher handoff, not an OpenAI proof result. No phase of this launcher has been executed during preparation. Root owns execution, review of receipts and final aggregation.


R2 changes only the launcher recorder pin key and import path to an owned immutable copy of frozen public R6 `ci/record.py` (SHA `1a7c9f9d…`). This prevents later live CI recorder updates from changing native verification behavior. R1 and its original saved peer review remain intact. `native-recorder-decoupling-r1.json` records the exact two-line delta, old/new/copy hashes and original peer-review linkage. No R2 phase or new control was run: this path-only change has AST validation and independent source review; all original control evidence retains its original version scope.

## Preconditions and scope

Wait for the existing native source builder to close successfully; preserve its source, topological ledger and default/trace build evidence. Root must enforce phase order and check every closed receipt before proceeding. The launcher intentionally runs exactly one named phase per invocation; it does not infer completion, resume, skip or start other phases. Each record directory must be new. A missing or failed phase leaves verification incomplete.

The unchanged proof is upstream OpenAI commit `4eaee87548250b2682affda7d05d947c05554bae`, copied into the recorded minimal workspace. Its sole exact target is `OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat` in `OAI.Algorithms.SubexponentialSAT.Main`; the challenge is `ComparatorChallenges.SubexponentialSAT`. Original Lean is 4.34.1. `verify_source_identity_r3.py` checks the original 3,092 module copies, separate recorded workspace configuration, nine pinned dependency Git states, and eight previously pinned original runtime files. Its expected revisions come from the original manifest and Mathlib's pinned Git blob, not the current dependency state.

The exact original Comparator JSON is passed unchanged. It disables Nanoda. Exact Comparator source `865edc14486c3388e9225daa971da8e157488c3e` was built with its own requested 4.35.0; its exporter and proof environment use the original 4.34.1. Native mode uses the official fake Landrun shim and has no Linux isolation. The additional Nanoda phase is separate from that original Comparator run.

## Invocation

Run from `<PRIVATE_PROJECT_ROOT>`, wrapping each individual command below in root's existing `python3 -m mining_lab.checkpoint run --agent ... --task ... --phase ... -- ...` so the outer launcher stream and resource receipt are also saved. The launcher itself uses the byte-identical frozen `native-recorder-r1/record.py` copy of the pinned `ci/record.py` Recorder for the actual child stage. Do not paste these commands into an automatic loop.

```sh
python3 research/eth-external-replication-20261104/openai/verify_native_phase_r2.py pre-identity --record-directory '<REPLICATION_ROOT>/openai/native-phase-records/r2-01-pre-identity'
python3 research/eth-external-replication-20261104/openai/verify_native_phase_r2.py trace --record-directory '<REPLICATION_ROOT>/openai/native-phase-records/r2-02-trace'
python3 research/eth-external-replication-20261104/openai/verify_native_phase_r2.py audit --record-directory '<REPLICATION_ROOT>/openai/native-phase-records/r2-03-audit'
python3 research/eth-external-replication-20261104/openai/verify_native_phase_r2.py comparator --record-directory '<REPLICATION_ROOT>/openai/native-phase-records/r2-04-comparator'
python3 research/eth-external-replication-20261104/openai/verify_native_phase_r2.py selected-export --record-directory '<REPLICATION_ROOT>/openai/native-phase-records/r2-05-selected-export'
python3 research/eth-external-replication-20261104/openai/verify_native_phase_r2.py extra-nanoda --record-directory '<REPLICATION_ROOT>/openai/native-phase-records/r2-06-extra-nanoda' --export-phase '<REPLICATION_ROOT>/openai/native-phase-records/r2-05-selected-export'
python3 research/eth-external-replication-20261104/openai/verify_native_phase_r2.py original-fresh --record-directory '<REPLICATION_ROOT>/openai/native-phase-records/r2-07-original-fresh'
python3 research/eth-external-replication-20261104/openai/verify_native_phase_r2.py post-identity --record-directory '<REPLICATION_ROOT>/openai/native-phase-records/r2-08-post-identity'
```

The phase commands use unchanged `in_workspace.py`, which invokes the real original toolchain and clears compiler/gate/loader overrides. The launcher constructs an environment rather than copying parent variables: original prefix and two Lean threads, owned HOME/TMPDIR, owned existing cache/elan locations, locale and bounded offline Git settings. It records actual environment keys/values, selected hashes and exact argv before launching. No credential variable is inherited.

| Phase | Exact child operation | Wall cap |
|---|---|---:|
| pre/post identity | Python `verify_source_identity_r3.py` | 300 s each |
| trace | `lake --no-build build +OAI.Algorithms.SubexponentialSAT.Main +ComparatorChallenges.SubexponentialSAT` | 600 s |
| audit | original `lake env lean --run AuditTargets.lean MODULE TARGET` | 1,800 s |
| comparator | original workspace `lake env` with exact 865 Comparator and original JSON; exact final success line required | 7,200 s |
| selected export | original `lake env` starts capture R2, which directly starts pinned 4.34.1 exporter `MODULE -- TARGET` | 1,800 s |
| extra Nanoda | recorded pinned native Nanoda on that closed export; strict three standard axioms, hard errors, Nat/String, two threads | 7,200 s |
| original fresh | absolute original 4.34.1 `leanchecker --fresh MODULE` through original Lake environment | 7,200 s |

The target audit imports with extensions and initializer execution disabled, checks standard axiom signatures, and traverses target types/values. Its JSON is checked for exactly the expected environment, target and completion events. Fresh replay covers the imported safe/nonpartial environment in the same original kernel; it admits axiom declarations and postchecks constructors/recursors. Separate target axiom and Comparator statement checks remain required.

## Output and failure behavior

Each invocation exclusively creates `phase-prepared.json`, `phase-inputs.json`, Recorder `stages/PHASE/{prepared.json,raw.log,finished.json}`, and `phase-result.json`. A preflight error retains a failed result; a started stage retains raw output and its actual exit/resource receipt. Interruption is forwarded through Recorder's exception cleanup. The launcher does not accept a phase merely because a file is present.

The selected export is written through a direct exclusive file descriptor, periodically and finally fsynced, then hashed. Its payload does not pass through Recorder's per-line log pump. Lake env is outside capture, so capture owns the actual exporter as its direct child. Capture and exporter inherit Recorder's process group for outer timeout termination. Capture R2 explicitly terminates/waits its own Popen child after an exception, then kills/waits that child if needed. It does not signal a caller group. This is direct-child exception cleanup, not a generic descendant supervisor.

The additional Nanoda phase accepts only a successful selected-export phase with identical launcher/input fingerprint and unchanged stage, raw log, capture receipt and payload hashes. It preserves the actual strict config and invokes `record_nanoda.py` with pinned real binary and official shim. Acceptance also checks one closed 00/01/02 recording lineage, exact argv/policy and checked-input archive binding. The large export and gzip are local artifacts; publication is a separate root decision.

Recorder's native child CPU measures reaped subprocesses/descendants. There is no systemd service in these native commands. Do not sum the nested Nanoda CPU twice. No RSS measurement or isolated performance comparison is claimed. Outer checkpoint CPU includes the launcher and its child stage; inner control/stage CPU must not be added again.

## Preparation validation and limits

AST syntax checks passed for the launcher and both R2 control/capture files; no launcher import or phase execution was used. The preserved R1 capture controls passed exact stdout/stderr handling for exit 0 and exit 7, plus isolated timeout child-group termination. Peer review found that R1 lacked explicit child cleanup on file sync exceptions; R1 bytes/results remain unchanged.

Capture R2's new Python-only fault control injects one periodic fsync error after a live harmless direct child closes inherited stdout/stderr. The stage fails normally with exit 1, not timeout or pipe-drain fallback, and the child is absent on return. The 17-byte partial export remains and no successful capture receipt exists. This verifies that specific cleanup branch; it does not run Lean, Lake, any real proof tool or a launcher phase. The three R1 controls are history for R1; they are not presented as executions of R2.

Preparation checkpoint commands consumed 1.071 CPU / 1.902 wall seconds for R1 controls and 0.479151 CPU / 1.417514 wall seconds for the R2 fault control. Actual commands, full raw logs and hashes are in `native-phase-launcher-handoff-r1.json`. Costs are USD 0 incremental; no cloud was used. All mathematical proof verdicts for this launcher remain pending.
