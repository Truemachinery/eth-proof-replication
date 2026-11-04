# Linux run 41888029999: harness setup failure

The [first public Linux run](https://github.com/Truemachinery/eth-proof-replication/actions/runs/41888029999) at commit `f340decb2b354bf154b4290e59cc8e260fdd867a` failed in both jobs before downloading Lean. It provides no theorem acceptance or rejection evidence.

| Job | Observed failure time (UTC) | Last completed stages | Failure |
| --- | --- | --- | --- |
| [OpenAI](https://github.com/Truemachinery/eth-proof-replication/actions/runs/41888029999/job/126777676667) | 2026-11-04 18:34:11 | Disposable SDK cleanup; host inventory | `ValueError('invalid stage name')` before `lean-4.34.1-download` |
| [Anthropic](https://github.com/Truemachinery/eth-proof-replication/actions/runs/41888029999/job/126777677087) | 2026-11-04 18:36:59 | Disposable SDK cleanup; host inventory | Same exception before `lean-4.33.1-download` |

`Recorder.run` allowed alphanumeric characters, underscores and hyphens, but the driver generated version labels containing dots. Validation failed before starting the download subprocess. Both run receipts explicitly record `status: incomplete`; neither reached a proof build, leanchecker, Comparator or Nanoda. Both cache saves were skipped.

GitHub's step summary marks the build/check step successful because it uses `continue-on-error`. The later preservation step correctly fails the job on the step's original unsuccessful outcome. That green step summary is not proof-check acceptance.

The bounded correction admits a single ASCII path component beginning with an alphanumeric character and containing only alphanumeric characters, dots, underscores or hyphens (maximum 120 characters). Separators, traversal components and other invalid labels remain rejected. The driver preflights all version-derived stage labels before SDK cleanup or acquisition.

The new local regression validates all 52 concrete literal/expanded stage labels, rejects 12 invalid path components, and runs eight tiny recorder subprocesses covering download/extraction labels for Lean 4.33.1, 4.34.0-rc1, 4.34.1 and 4.35.0. It used 0.537034 CPU seconds and 0.995451 wall seconds. A separate same-team root run under Python 3.9 also passed (0.507425 CPU seconds, 0.773453 wall seconds). These are harness controls, not Linux proof verification.

Corrected execution-source identities:

- `ci/record.py`: `8186ee7b3aea0f67f84ece3c03a8f70036ef39da9380699a959495ee1e33d197`
- `ci/replicate.py`: `0cadbd0ced012a80d9a7f843d99c53daf0956247ce72b8e6c3e729631994dde0`
- `ci/check_stage_name_control.py`: `749d1fb3f109f7c3878cf2b4dd3c543db3c173828af17b54756fed07413f2571`
- `ci/control-result-stage-names-r3.json`: `b476322adfed7729b2b799e0044f042b0825678a40b685c2679d831af4dd60c3`

The original completed workflow-log ZIP was downloaded through GitHub's read-only API: 41,289 bytes, SHA-256 `6b035375aaa5c9e2e983f225a82fe94693bdf9e25348c70e1a4cbb2ee02d9146`. Its 22 members were extracted byte-for-byte into a new local directory and hash-manifested. GitHub supplies both aggregate and per-step logs; repeated receipts in those files describe the same two jobs and must not be double-counted.

Each runner reported four vCPUs, 16,760,344,576 bytes of memory and approximately 111.3 GB free disk after cleanup. SDK cleanup took 135.019 seconds for OpenAI and 295.187 seconds for Anthropic; host inventories took 4.575 and 12.886 seconds. The four completed stage receipts total 22.223624 child CPU seconds and 447.667211 summed wall seconds across overlapping jobs. This excludes runner/action setup and is not elapsed workflow time. No proof computation was performed. The jobs used standard public hosted runners; no larger runners, artifact uploads or cache allowance increases were introduced.

Native proof builds continued separately. This report does not infer their outcomes. A later corrected Linux run requires its own completed receipts and actual proof checks.
