# Linux run 41891445823: Landlock ABI preflight failure

Both jobs of [run 41891445823](https://github.com/Truemachinery/eth-proof-replication/actions/runs/41891445823), commit `6dfd0f7b6a80bb8629aaa7fc29ca59e772006df7`, stopped at `landrun-enforcement-control`. No project proof module was compiled, and leanchecker, Comparator target checks and Nanoda proof checks did not run. Both final receipts are incomplete with zero completed project modules.

The version-label correction worked. Both jobs downloaded and extracted the exact proof/tool Lean releases, checked their compiler identities, fetched pinned public sources, obtained the exact Mathlib dependency cache, and built Comparator, matching-version exporter, Nanoda and Landrun. OpenAI also verified its byte-identical lexical source workspace. These successful setup stages are not theorem verification.

| Job | Observed Landrun error (UTC) | Last stage exit |
| --- | --- | --- |
| [OpenAI](https://github.com/Truemachinery/eth-proof-replication/actions/runs/41891445823/job/126789617182) | 2026-11-04 18:58:23 | 1 |
| [Anthropic](https://github.com/Truemachinery/eth-proof-replication/actions/runs/41891445823/job/126789617650) | 2026-11-04 18:58:25 | 1 |

The logged error reports Landlock ABI 8 while the strict request requires ABI 9. Systemd successfully created the non-root control service; Landrun then rejected its requested restriction configuration before executing the write-denial probe.

Pinned [Landrun's CLI](https://github.com/zouuup/landrun/blob/811cfff51ceaf3d9843708aa6d22e9b84ccac8b4/cmd/landrun/main.go) defaults to strict mode. Its [sandbox implementation](https://github.com/zouuup/landrun/blob/811cfff51ceaf3d9843708aa6d22e9b84ccac8b4/internal/sandbox/sandbox.go) requests its known restriction domains and selects supported restrictions when `--best-effort` is explicitly supplied. Both pinned official Comparator versions already use that flag; our additional preflight did not. This mismatch is a harness compatibility failure, not a theorem rejection or evidence that a weaker sandbox was accepted. No fallback ran in this attempt.

A proposed correction must preserve path/environment restrictions, use the pinned real Landrun, require a queried ABI of at least 8 and require actual filesystem write-denial and systemd AF_UNIX-denial controls. ABI 8 must not be described as ABI 9: pathname UNIX-socket rights introduced in ABI 9 are absent, with the separate systemd rule denying `socket(AF_UNIX)` creation only. Inherited sockets, `socketpair` and `io_uring` are outside that setting's documented coverage; it is not a complete ABI 9 replacement. The next run must measure those controls before any proof work. No compatibility or proof success is inferred here.

The exact completed workflow ZIP is 111,547 bytes, SHA-256 `762a93d203807a5d3f774f8dae549a433717c3961150c4b1d55916d3ef6d67cc`. All 22 members were preserved byte-for-byte with a local SHA manifest. Aggregate and per-step files repeat some receipts; they are the same jobs and are counted once below. Raw receipts preserve compiler/download identities and all four tool binary identities for each job.

| Recorded stage totals | OpenAI | Anthropic |
| --- | ---: | ---: |
| Stages, including failed preflight | 34 | 32 |
| Summed reaped-child CPU seconds | 368.960752 | 223.341197 |
| Summed stage wall seconds | 314.976119 | 324.415475 |

CPU totals exclude systemd-managed service CPU; the two failed services separately report 6 ms and 4 ms. Wall totals include acquisition/build stages and exclude other runner/action orchestration. The jobs overlapped, so summed wall time is not elapsed workflow time. No project build artifacts entered the continuation cache, and no paid/larger runners, artifact uploads or cache allowance increases were introduced. Native proof builds remained separate and are not evaluated by this report.
