This is a prepared native resource-build protocol. No OpenAI ETH retry or R6 aggregation has been executed by its author. Root runs the retry only after the original 4.34.1 fresh phase closes successfully and peer review accepts these exact sources.

The original two-thread Nano D9 run aborted with worker stack overflow and remains failed. The proposed serial/main-stack profile was falsified by harmless OS-limit controls and was never used for ETH. The new binary is an isolated build of exact 68d5 tracked source with only `src/lib.rs`'s requested worker-stack constant changed from 16 MiB to 256 MiB. It keeps the original strict two-thread configuration and selected export. The helper records two unchanged preexec main-stack-limit snapshots and never sets those limits; it does not instrument limits or stack extent inside the running checker. The harmless Rust probe observed a 268447744-byte pthread stack for a 268435456-byte request; actual Nano worker extent is unmeasured.

Frozen sources: helper `nanoda_worker_stack_retry_r2.py` SHA59931d7b0d00ba5651322e6a3e1efb9524223334ce74ee767891dd95534557fc; aggregate `aggregate_native_result_r6.py` SHAf540073691db650da2edd16888e99cc294891b9855df0e64e044c86e2235bcd0. New binary SHA10e1a4ebdb6fa606ca8d7a60774d8af0655294ab0b19d03a838a5ba746b7c2d9. The copied recorder remains exact C34; its new manifest pins only the separate resource binary. Original D9/C34/manifest/source remain preserved.

Root's prepared retry command, from the project checkout, after successful fresh closure:

```sh
python3 -m mining_lab.checkpoint run --agent codex-eth-replication --task external-eth-proof-replication-20261104 --phase native-openai-worker-stack256-r2 --timeout 7500 --log-file research/eth-external-replication-20261104/openai/logs/native-worker-stack256-r2-checkpoint.txt -- python3 research/eth-external-replication-20261104/openai/nanoda_worker_stack_retry_r2.py \
  --record-directory <REPLICATION_ROOT>/openai/native-retry-records/worker-stack256-r2-01 \
  --export-phase <REPLICATION_ROOT>/openai/native-phase-records/r2-05-selected-export \
  --failed-phase <REPLICATION_ROOT>/openai/native-phase-records/r2-06-extra-nanoda \
  --failed-outer-receipt <REPLICATION_ROOT>/openai/logs/native-r2-extra-nanoda-checkpoint.json \
  --fresh-phase <REPLICATION_ROOT>/openai/native-phase-records/r2-07-original-fresh
```

The inner resource checker is bounded at 7200 seconds. Save the actual outer DIGEST separately without inventing wrapper fields. The helper fails closed if fresh is incomplete, any original or resource input drifts, the checked export/config/binary changes, or actual Nano does not return zero. A failed or interrupted new directory is preserved and never reused.

After the retry closes, root runs the original R2 `post-identity` phase LAST in a new `r2-08-post-identity` directory, with ordinary checkpoint/resource recording. Then root may aggregate the seven original successful phases, the retained original failed phase, and the explicit new resource retry:

```sh
python3 research/eth-external-replication-20261104/openai/aggregate_native_result_r6.py \
  --build-receipt <REPLICATION_ROOT>/openai/logs/source-build-gated-r4-receipt.json \
  --failed-nanoda-phase <REPLICATION_ROOT>/openai/native-phase-records/r2-06-extra-nanoda \
  --failed-outer-receipt <REPLICATION_ROOT>/openai/logs/native-r2-extra-nanoda-checkpoint.json \
  --nanoda-retry <REPLICATION_ROOT>/openai/native-retry-records/worker-stack256-r2-01 \
  --phase pre-identity=<REPLICATION_ROOT>/openai/native-phase-records/r2-01-pre-identity \
  --phase trace=<REPLICATION_ROOT>/openai/native-phase-records/r2-02-trace \
  --phase audit=<REPLICATION_ROOT>/openai/native-phase-records/r2-03-audit \
  --phase comparator=<REPLICATION_ROOT>/openai/native-phase-records/r2-04-comparator \
  --phase selected-export=<REPLICATION_ROOT>/openai/native-phase-records/r2-05-selected-export \
  --phase original-fresh=<REPLICATION_ROOT>/openai/native-phase-records/r2-07-original-fresh \
  --phase post-identity=<REPLICATION_ROOT>/openai/native-phase-records/r2-08-post-identity \
  --output-directory <REPLICATION_ROOT>/openai/native-aggregate-records/worker-stack256-r6-01
```

R6 hashes and decompresses the actual accepted archive, binds all closed input/output/stage/recording receipts, enforces failure→fresh→retry→post-identity ordering and nonoverlap, and keeps `original_r2_protocol_passed=false`. Optional successful outer wrappers are an all-seven set; omitting them does not omit the required actual stage receipts. Preparation/build/probe/control costs are recorded separately because their intervals may overlap fresh, and are excluded from the principal nonoverlapping proof-stage wall sums.

Comparator's internal kernel uses linked Lean 4.35; original-version fresh uses Lean 4.34.1. These share the Lean implementation. Rust Nano supplies the separate checker implementation. The official fake Landrun shim provides no native OS isolation. Large NDJSON and gzip exports stay local; only metadata and hashes are suitable for the small public package. Exact formal-target replication does not establish practical SAT or mining advantage.
