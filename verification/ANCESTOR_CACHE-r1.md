# Exact predecessor cache review

This is an Ant-only implementation candidate awaiting final review and the separate OpenAI terminal receipt. It is not evidence that real cache bytes have restored successfully.

The measured r4 failure occurred after source build, fresh replay and the original Anthropic Comparator/Nanoda checks accepted. Our additional export omitted `LEAN_SYSROOT`. The one-line export correction changes the harness identity, so an ordinary cache from the previous harness must remain rejected unless the narrowly reviewed exception applies.

`ci/ancestor-cache-compatibility.json` contains the **23 actual public producer rows** from the closed run receipt, not the 24 private export inputs. The workflow template maps to `.github/workflows/replicate.yml` and is outside public `ci/`. The ledger separately pins the reviewed current workflow and the exact current CI file set and hashes, excluding only the ledger itself. Ordinary current cache fingerprints include the ledger.

The additional restore path requires the single observed full Actions key, its exact actual matched-key output, the exact old manifest SHA before parsing it, and the current source/config/proof-runtime context SHA. It recomputes the old Python fingerprint from the pinned 23 producer basename/SHA pairs plus that **current** context. An old fingerprint is never replaced with a current fingerprint. Future unreviewed driver, gate, pin, helper, file-set or workflow changes reject this exception.

The existing ownership, suffix, duplicate-path, regular-file, symlink/hardlink, per-file SHA/size, payload/total-cap, unmanifested-file and no-overwrite checks remain. Normal Lake trace checking and proof checks remain required. Before the final snapshot replaces cache staging, exact original manifest bytes are copied under runner `work/records` and an acceptance receipt identifies the old key, old fingerprint, context and manifest. These files are ephemeral unless separately retained; their hashes and receipt are displayed in workflow logs. New snapshots obtain the normal current fingerprint through `snapshot`, rather than relabeling the old manifest.

The workflow adds only an exact-key predecessor restore, with no predecessor `restore-keys` prefix. It also rejects a non-exact `cache-matched-key`. Trusted `ETH_RESTORED_CACHE_KEY` metadata is supplied to the harness parent and is excluded from `clean_environment` used for proof processes. Existing current-harness prefix selection and the 2 GiB/proof, 4 GiB total limits remain unchanged.

`ancestor_cache_control_r1.py` records 19 passing protocol checks: closed producer metadata binding, accepted exact predecessor plus immutable-manifest preservation, normal current fingerprint acceptance, source/config/runtime/proof/key/manifest/payload/path/duplicate/producer/workflow drift rejection, no overwrite, metadata exclusion, and execution of the actual YAML exact-key guard on exact versus suffix-matched keys. The test payload is explicitly synthetic and is never passed to Lean. Two deeper path controls deliberately repin a synthetic test manifest to exercise ownership checks independently of the outer manifest hash. The production ledger is unchanged by the controls.

Command:

```sh
/opt/homebrew/bin/python3.12 research/eth-external-replication-20261104/verification/ancestor_cache_control_r1.py
```

The recorded invocation used `mining_lab.checkpoint run` with a 60-second timeout; outputs are exclusive and require new names for a replay. Wrapper cost was 0.557901 CPU / 0.949852 wall seconds; no real Actions restore, Linux execution, trace/kernel check or external proof run occurred. Result SHA: `c63bbb1a7b72c17f74a3890c6895b9192a421584f52e9b47fa3b10863ed2a24e`. Script SHA: `70e14ed028189eb9c67a77c26d5c8610915ec8e013c270da14626b3c461e0cc8`.

The separate `export_sysroot_control_r1.py` ran both pinned native exporters on trusted `Init/Nat.add_zero`: an empty PATH without SYSROOT fails, while the exact SYSROOT produces bytes identical to its successful baseline. Wrapper cost was 2.782466 CPU / 4.943681 wall seconds. Result SHA: `78294fd4de5afe05d40c4a10af897eb094945d245c90437d7cb4724b359556de`. This isolates the environment lookup mechanism and does not test Linux Landrun or ETH.

No workflow dispatch, cache download, cache deletion, publication or new paid compute was performed by these controls. Actual predecessor payload validity remains unmeasured until the reviewed Actions restore executes. OpenAI compatibility must be populated only from its own closed cache receipt and separately reviewed before export.
