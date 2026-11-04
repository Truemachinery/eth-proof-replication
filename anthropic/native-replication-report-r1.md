# Anthropic ETH formalization: native replication result

All required native checks passed for official commit `16a5ce41304fcdaea4e0be7c132e1c361dc26da5`, with original Lean 4.33.1 and Mathlib `0df444a360eaa60ab8c11dca51a86af692955474`. The proof source was unchanged. This record concerns `MainResults.ethIsFalse : MainResults.ETHIsFalse` and `MainResults.mainTheorem : MainResults.MainTheorem` (Solution.lean:40,44; trusted contracts MainResults.lean:122,177).

The clean project build passed all 1,050 scheduled module targets; the final unchanged upstream `lake build` passed 9,768 jobs. Official Mathlib caches were restored rather than rebuilt. Challenge contains two intentional template `sorry` warnings; Solution does not import Challenge. The trusted runtime audit found only `propext`, `Classical.choice`, and `Quot.sound` across 72,360 / 72,169 transitive constants for the two targets. Those axiom signatures matched trusted Init, with audited extension and initializer loading disabled.

The exact CI-pinned Comparator source `575674928e239f5bc452aab72d1dd7b0f1326494` accepted the exact theorem contracts and axiom policy. Its final raw log explicitly says `nanoda kernel accepts the solution`, `Lean default kernel accepts the solution`, and `Your solution is okay!`. Native driver compilation used existing Lean 4.34.1 instead of its requested 4.34.0-rc1. The upstream development fake-landrun shim was used, so this is not a verbatim Linux CI or Linux isolation reproduction. See [COMPARATOR_TOOL.md](COMPARATOR_TOOL.md).

Actual pinned Nanoda `68d5ca9db226849b41a6fff59d796ff19d0a8840` returned 0 with a complete before/after recording. Its effective policy retained exactly the three permitted axioms, hard failure for other axioms, and Nat/String extensions. Exact575 omits `num_threads`; pinned Nanoda defaults to serial checking. The matching-minor exporter tag v4.33.0 was built with original Lean 4.33.1, following the official CI patch fallback.

Nanoda actually checked a 583,355,033-byte export with SHA-256 `e5cc12cb057e47d08780ce6e807186b5be0074bcc2dcddeffea1a0b3191641e6`. The retained local gzip is 118,800,833 bytes, SHA-256 `c625a4755f8ccbf05a95760d59b8a3af42643d9f702f7bbaccb7aa682db814f3`. The large archive stays local under `checker-records/nanoda-64425-0dvr445m/`; the small 00/01/02 receipts and effective policy bind it to the actual successful invocation.

Original Lean 4.33.1 `lake env leanchecker --fresh Solution` also returned 0. This replays the full imported safe, nonpartial environment into an empty environment using the same Lean kernel; axiom declarations are admitted, with constructors and recursors postchecked. The named-target axiom audit and Comparator supply the separate axiom/statement checks. Verbose was omitted solely as an output choice. Empty stdout/stderr is expected for this successful command. A post-check rehash confirmed all 1,069 pinned tracked files, nine dependency heads/clean tracked worktrees, and five selected original Lean runtime files unchanged.

| Stage | Result | Child CPU seconds | Wall seconds |
| --- | --- | ---: | ---: |
| build-topological-r1 | PASS | 8990.073577 | 9237.617874 |
| default-build-r1 | PASS | 8.339424 | 9.199979 |
| pinned-input-identity-r1 | PASS | 0.653343 | 1.022827 |
| target-axiom-audit-r1 | PASS | 12.811796 | 36.855625 |
| upstream-print-axioms-r1 | PASS | 7.094761 | 29.894834 |
| comparator-native-r1 | PASS | 143.319858 | 193.513025 |
| leanchecker-fresh-r1 | PASS | 980.732225 | 1144.574556 |
| pinned-input-identity-post-checkers-r1 | PASS | 0.745707 | 1.132648 |

Principal stages used 10143.770691 measured child CPU seconds and 10653.811369 summed wall seconds. Nanoda's 40.131589 CPU / 40.281850 wall seconds are included in Comparator, not added again. Host: Apple M5, 10 CPU cores, 32 GB RAM, macOS arm64; shared-host interference and root's temporary OpenAI suspension prevent timing comparison. Paid cloud spend: USD 0. Acquisition, model inference, authoring and small monitoring/report overhead are not fully included.

Exact commands, environment overrides, timestamps, resources, output sizes and hashes are in `logs/*.json`; full output is in matching `logs/*.txt`. [native-replication-result-r1.json](native-replication-result-r1.json) contains structured results and exact checker argv. [native-replication-artifacts-r1.json](native-replication-artifacts-r1.json) binds the local artifacts. The full source build journal stays local as `logs/build-topological-r1.jsonl`.

Retained negatives: the unchanged upstream CI helper stopped at missing Go on the native host; a first tool build failed before compilation because `env` parsed an executable path containing `P=NP` as an assignment, and the corrected unchanged-source build succeeded; the missing-config Comparator smoke check failed as expected. No theorem rejection was discarded. Original toolchain archive hash is unavailable because elan did not retain the archive; installed selected runtime hashes are recorded.

The result establishes successful checks of the exact formal statements under the recorded axioms and tool variants. MainResults uses a finite-alphabet Mathlib FinTM2 model. The ordinary computation-model interpretation remains separate mathematical review. Practical SAT performance, usable constants, polynomial-time SAT, and SHA-256d mining advantage were not measured. The saved-evidence reviewer is another member of the same agent team; external scholarly review remains distinct.
