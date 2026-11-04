# Replication plan and acceptance criteria

Date: 2026-11-04. Operator: Nathaniel Jose. Root agent label: `codex-eth-replication`.

## Hypothesis and falsifiers

The exact named ETH/counting theorem contracts can be reproduced from pinned upstream sources using their pinned Lean and Mathlib versions. A source-build failure, missing target, unexpected transitive axiom, target-type mismatch, or fresh kernel-replay failure prevents a positive verdict for that stage. Preserve every failed attempt and distinguish an infrastructure failure from a failed proof check.

## Required stages

1. Pin upstream Git commit, clean checkout, toolchain, dependency manifest, target declarations, permitted axioms, source hashes and exact configuration.
2. Acquire pinned public dependencies. Record that dependency `.olean` files may come from the official Mathlib cache; do not claim those dependencies were independently re-elaborated from source.
3. Build the proof's project-owned source import closure from source. Preserve upstream source bytes and compiler options. Document any package-configuration change.
4. Establish that each named target exists, compare its type to the separately supplied challenge contract, and inspect the transitive axiom closure. The permitted standard axioms are `propext`, `Quot.sound`, `Classical.choice`; specification placeholders must not contaminate the solution target.
5. Run `leanchecker --fresh` on the solution's full imported constant closure. Record that this reuses Lean's kernel implementation and that axiom/statement checks are separate obligations.
6. If feasible, execute the upstream comparator and independent nanoda checking. Record Linux isolation and tool availability accurately. Missing optional stages must not be described as having passed.
7. Independently review the provenance, commands, stage receipts and claims. Save a scoped report, an agent handoff and a project experiment-log entry. Prepare a sanitized public repository and submission drafts.

The local historical `mining_lab.lean_verifier` wrapper is not sufficient to certify these external proofs. Prior adversarial findings about that wrapper are in `research/lean-audit-notes-claude-20261102.md`.

## Resources and limits

- Host: native macOS arm64, Apple M5, 10 cores, 32 GiB RAM. Hardware identifiers are excluded.
- Isolated Lean toolchains: OpenAI `4.34.1`, Anthropic `4.33.1`; no change to the shared project's default `4.35.0` toolchain or shared Lake library.
- Initial maximum wall time: eight hours per proof, measured per stage with bounded timeouts. Combined reserved CPU budget: 115,200 CPU seconds. Stop or reassess when a stage cap is reached; a cap is not proof failure.
- At most two ready project source modules per proof at once, with two Lean runtime threads per compiler invocation; do not claim Lake has a `-j` process limit. Each implementation must document its actual scheduling mechanism.
- Public upstream downloads only. Paid cloud cost: USD 0. No mining-pool, node, wallet or transaction operations.
- These are correctness/reproduction runs on a shared host, not controlled performance comparisons. Report wall/child CPU and available peak-memory measurements with their accounting limits.
- Logs are append-only/exclusive; retain failed attempts. Long runs must checkpoint completed modules and never restart an already completed source build merely because chat context compacts.

## Submission boundaries

The operator requested a new public GitHub repository. Publish only the explicit clean replication package after review. Draft blog comments and the repository-link email are prepared locally; sending those messages is a distinct action that has not been requested yet.

## Recorded scheduling revisions

The limits above describe the initial plan. Subsequent setup and scheduling findings are retained in the logs rather than treated as proof failures:

- OpenAI's minimal package needed explicit library globs for individual imported-module targets. `workspace-config-r2.json` records this correction; original configuration and scripts remain under `openai/revisions/`. Upstream proof bytes, toolchain, Mathlib pin and `autoImplicit=false` did not change.
- Two simultaneous Lake invocations contend for an exclusive package-configuration lock. The serial retry completed ten source modules, but repeated Lake setup added approximately 10–12 seconds per target, beyond substantial Lean import/elaboration work. That retry was intentionally stopped to change scheduling. Its cleanup signal-zero probe failed with `PermissionError`; a separately recorded `ps` process-group inventory established that the exact stopped groups had no remaining members.
- The current OpenAI build uses one ordinary Lake invocation and a task-local C admission gate, initially **three Lean frontends with four runtime threads per invocation**. Two- and four-slot real-Lean controls, inherited-lock/argument checks, an ordinary-Lake fixture and original-prefix trace reuse passed before adoption; a second Codex agent reviewed the source. This is a resource-control deviation from the initial two-module/two-thread estimate. It does not change proof inputs or the real compiler. The gate bounds Lean frontends, not C/link jobs. Final theorem/checker stages must use the original ungated toolchains, and post-build source/configuration/dependency hashes must be checked.
- A second Linux route is being prepared for the requested new public repository: two manually dispatched standard `ubuntu-24.04` jobs, each capped below GitHub's six-hour hosted-job limit. Standard public runner compute and workflow logs are free under the [current GitHub billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions). Only this effort's own project build outputs may use a bounded cache, at most 2 GiB per proof / 4 GiB retained total, below the repository's included 10 GiB allowance. No paid/larger runners, Actions artifact uploads, custom images, or cache-limit increases are planned. CI has not been dispatched at the time of this revision; actual outcomes and resource use require their own receipts.

The Linux route may still reach its resource cap. A timeout is an incomplete run, not a proof rejection. Continuations must validate retained source/compiler/configuration identities and existing build traces, preserve earlier logs, and avoid recomputing completed work without a reason.

## Recorded Linux compatibility revision

The earlier scheduling paragraph records the pre-dispatch plan. The initial public run `41888029999` stopped on dotted stage labels; corrected run `41891445823` built the checking tools but stopped before proof compilation because the hosted kernel supplies Landlock ABI 8 and pinned Landrun defaults to ABI 9. Both failures and their workflow outputs remain retained; neither is a theorem verdict.

The next revision explicitly requires measured ABI >=8 and requests Landrun `--best-effort`, matching both pinned official Comparator drivers. On ABI 8 this drops only ABI 9's `RESOLVE_UNIX` pathname-socket permission. Available earlier filesystem, TCP, IPC-scoping and thread-synchronization protections remain requested. Pinned Landrun and actual write-denial/socket-creation-denial preflights run before proof acquisition; a failed control stops the run. The native development shim is never substituted on Linux. This changes the disclosed isolation coverage, not proof sources or mathematical acceptance checks.

The systemd `RestrictAddressFamilies` test covers `socket(AF_UNIX)` creation. It does not certify inherited sockets, `socketpair` or `io_uring`, and is not a complete replacement for the missing ABI 9 pathname-socket permission. No full ABI 9 enforcement claim is made for an ABI 8 runner. Actual syscall/enforcement results require the next run's receipts; source review and local harness controls cannot supply them.
