Prepared negative/incomplete closure only. No actual R3 terminal result, postidentity result or fallback aggregate was read or generated during preparation. This utility is separate from the positive R7 path and cannot produce an expanded-suite PASS.

Frozen utility `aggregate_native_incomplete_r2.py` SHA97d65f2fcc779f4e8ea5473716c7da21cb6dea98c9ca81a76e9a80658fff8940. It imports only the pinned R7 metadata validators (be05...) and the separately pinned R3 metadata helper (9f4...). It does not run a proof tool or checker. The first prepared R1f2e remains preserved; peer review found its premature-success-seal ordering, corrected in R2. The final successful seal is written after report fsync and artifact manifest, and binds all three outputs.

Root's prerequisites:

1. The actual worker-stack256 R3 attempt closes with a failed helper result and a closed nonzero stage, plus the actual plain checkpoint DIGEST/raw. Wait for actual termination and perform the root-owned process cleanup observation; this utility does not inspect or control live PIDs.
2. Preserve the actual failed folder and all records. A stage timeout requires actual stage exit124 with exact reason `stage timeout` and elapsed cap. A125 with another reason remains a generic stage failure; no missing timeout cause is invented.
3. Run the original R2 postidentity LAST after the terminal retry. All seven original R2 phases, original source build and unchanged input identities must validate.
4. Root may then explicitly invoke this utility in a new output directory. Do not invoke it against the active attempt or use it as an automatic OR branch of positive R7 verification.

Example prepared command, from the project checkout. The terminal-DIGEST filename below is the proposed save name only; use it only after root has saved the actual terminal stdout there, otherwise substitute the actual closed JSON path under openai/logs. The utility accepts the actual plain DIGEST schema rather than inventing wrapper fields.

```sh
python3 -m mining_lab.checkpoint run --agent codex-eth-replication --task external-eth-proof-replication-20261104 --phase native-openai-incomplete-closure-r2 --timeout 600 --tail-lines 2 -- python3 research/eth-external-replication-20261104/openai/aggregate_native_incomplete_r2.py \
  --build-receipt <REPLICATION_ROOT>/openai/logs/source-build-gated-r4-receipt.json \
  --failed-original-outer <REPLICATION_ROOT>/openai/logs/native-r2-extra-nanoda-checkpoint.json \
  --terminal-outer-receipt <REPLICATION_ROOT>/openai/logs/native-worker-stack256-r3-checkpoint.json \
  --phase pre-identity=<REPLICATION_ROOT>/openai/native-phase-records/r2-01-pre-identity \
  --phase trace=<REPLICATION_ROOT>/openai/native-phase-records/r2-02-trace \
  --phase audit=<REPLICATION_ROOT>/openai/native-phase-records/r2-03-audit \
  --phase comparator=<REPLICATION_ROOT>/openai/native-phase-records/r2-04-comparator \
  --phase selected-export=<REPLICATION_ROOT>/openai/native-phase-records/r2-05-selected-export \
  --phase original-fresh=<REPLICATION_ROOT>/openai/native-phase-records/r2-07-original-fresh \
  --phase post-identity=<REPLICATION_ROOT>/openai/native-phase-records/r2-08-post-identity \
  --output-directory <REPLICATION_ROOT>/openai/native-incomplete-records/worker-stack256-r3-terminal-r1
```

This is hashing/parsing work, not another proof run. It rehashes the selected original inputs and large export/retained archive files through the shared validators. Run only after all relevant stages close; allow bounded local I/O time. It never publishes those large assets.

Successful report creation exits0 with `closure-finished.json.status=negative_evidence_closed`; this means evidence closure only. The distinct `openai-native-incomplete-result/1` report says:

- `verdict=ORIGINAL_LEAN_SUITE_PASS_ADDITIONAL_NANODA_INCOMPLETE`
- `original_lean_suite_passed=true`
- `expanded_suite_passed=false`, `all_required_native_checks_passed=false`, `original_r2_protocol_passed=false`
- `additional_nanoda_verification=INCOMPLETE`, `independent_nanoda_acceptance_observed=false`
- With no actual terminal checker receipt: `checker_exit_code=null`, `independent_nanoda_accepted=null`, `recording_complete=false`, `inputs_unchanged_during_check=null`.
- With an actual nonzero closed02: retain actual exit and observed unchanged status; it remains nonaccepted. Actual nonzero exit reported in99 is retained with incomplete recording. Any recorded checker0 or conflicting02+99 is refused by this path.

The archived export is labelled `prepared_for_attempt`, never checked-and-accepted. A timeout or wrapper failure is not a logical rejection. Terminal stage, actual outer and nested checker costs remain separate; nested and outer costs are not added twice. Original D9 stack overflow, preexec CF failure, failed main-stack controls, original worker-resource provenance and manual source-build scheduling receipts remain preserved.

No Linux OS isolation is provided by native fake Landrun. Comparator internal replay uses linked Lean4.35; original fresh uses4.34.1, sharing the Lean implementation family. An incomplete Rust check does not establish independent kernel acceptance. Exact formal-target replication does not establish practical SAT or SHA256d performance.

Local input/worker/raw records may contain the private CF metadata value. Any separate public negative-evidence mode must redact its value, retain the value hash and original local identities, and remain disjoint from the positive publisher guard. Publication, final maps, README/EXPERIMENTS updates and any outreach remain root-owned.
