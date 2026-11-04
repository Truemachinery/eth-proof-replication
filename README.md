# Independent execution of existing ETH proofs

Prepared by Nathaniel Jose with OpenAI Codex assistance, 2026-11-04. No additional human coauthors are asserted. This is a reproducibility record of the published proofs, not a new proof or a first-replication claim.

**Proof verification is in progress. No positive external-proof verdict is asserted by this draft.** A completed download, dependency-cache check or control fixture is not a completed ETH proof check. Failed attempts remain part of the evidence; missing stages remain unverified.

The public repository is [Truemachinery/eth-proof-replication](https://github.com/Truemachinery/eth-proof-replication). [Initial commit f340decb](https://github.com/Truemachinery/eth-proof-replication/tree/f340decb2b354bf154b4290e59cc8e260fdd867a) contains the first reviewed 91-file package; `PUBLICATION_RECEIPT-r1.json` records independent byte-by-byte verification of that publication.

The [first public Linux run](https://github.com/Truemachinery/eth-proof-replication/actions/runs/41888029999) failed in both jobs before downloading Lean because our recorder rejected dots in version labels. See `ci/runs/41888029999/DIAGNOSIS-R1.md` for the exact failure, correction and retained-log hashes. Neither job reached a theorem check. The original failed commit and run remain visible. Passing a harness regression or a green `continue-on-error` step does not establish proof acceptance.

The [second Linux run](https://github.com/Truemachinery/eth-proof-replication/actions/runs/41891445823) at [6dfd0f7](https://github.com/Truemachinery/eth-proof-replication/tree/6dfd0f7b6a80bb8629aaa7fc29ca59e772006df7) acquired dependencies and built the four checking tools, then stopped before project-source compilation because Landrun requested ABI 9 while the hosted kernel supplies ABI 8. See `ci/runs/41891445823/DIAGNOSIS-R3.md`. This remains an incomplete setup result, not a proof verdict.

The Linux pipeline has two manually dispatched Ubuntu 24.04 jobs, at most 350 minutes each, using public standard runners. The resource plan retains owned build caches of at most 2 GiB per proof and 4 GiB total, within this repository's 10 GB included cache allowance, so later manual runs can continue unfinished work. GitHub documents free standard runners for public repositories and a separate 10 GB cache allowance. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) There are no Actions artifact uploads or paid runners. These are configured limits, not a completed build or independent billing audit. Inspect actual run logs, summaries and cache accounting before recording a Linux verdict.

| Development | Pinned public source | Proof toolchain | Named target |
| --- | --- | --- | --- |
| OpenAI | [openai/math, 4eaee875](https://github.com/openai/math/tree/4eaee87548250b2682affda7d05d947c05554bae/lean) | Lean 4.34.1 | `OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat` |
| Anthropic | [formal-math, 16a5ce41](https://github.com/anthropics/formal-math/tree/16a5ce41304fcdaea4e0be7c132e1c361dc26da5/eth) | Lean 4.33.1 | `MainResults.ethIsFalse`, `MainResults.mainTheorem` |

The public package contains only explicitly selected replication reports, source/tool hash manifests, original harness/probe/gate code or labelled portable derivatives, and completed stage evidence. It excludes upstream checkouts, downloaded caches, installed binaries, private project material, correspondence drafts and live logs. Licensed upstream sources are linked rather than republished here.

Read `PLAN.md`, `STATEMENT_REVIEW.md`, `VERIFICATION_PLAN.md` and `SHA256D_RELEVANCE.md` for the intended checks and mathematical scope. Some locally referenced artifacts may be deliberately unavailable in this package; `PUBLIC_MANIFEST.json` states what was actually included. It does not promote narrative claims or fixture results into a proof verdict.

## What the evidence can establish

Source re-elaboration, named-target/transitive-axiom inspection, trusted-statement comparison, Lean `leanchecker --fresh`, and Nanoda are separate stages. Acceptance by Lean and an independent implementation is stronger evidence than a build alone; neither machine decides whether the formal contract expresses the intended informal theorem. Our source and checker versions, effective configurations, failures and resource accounting must remain explicit.

Dependencies may use the official Mathlib binary cache. Such dependencies were not thereby independently rebuilt from source. The OpenAI project uses a documented minimal Lake configuration while preserving pinned proof-source bytes and dependency revisions. Native Comparator execution uses the official development `fake-landrun.sh`, which supplies **no operating-system sandbox**; this does not reproduce Linux Landrun/systemd isolation.

The current native OpenAI launcher uses one ordinary Lake invocation with a task-local compiler admission gate. Its default is three Lean frontends with four Lean runtime threads each; the actual invocation and receipt control. This bounds Lean frontends, not separate C/link jobs. Earlier two-slot control fixtures do not establish a two-slot limit for this later campaign. Gate and launcher source/manifests are provided as preparation evidence, not a completed proof check.

Linux CI uses real pinned Landrun with the separately reviewed systemd restrictions. The revised policy requires measured Landlock ABI >=8 and explicitly requests `--best-effort`, which both pinned official Comparator versions already use. On ABI 8 this omits ABI 9's `RESOLVE_UNIX` pathname-socket permission while retaining the earlier filesystem, TCP, scope and thread-synchronization rights. It is narrower than full ABI 9 enforcement. Actual filesystem write-denial and `socket(AF_UNIX)` creation-denial controls must pass before proof acquisition/build; the development shim is never substituted.

The systemd address-family restriction and our socket test concern **socket creation**. They do not establish denial through inherited sockets, `socketpair`, or `io_uring`, and are not claimed as a complete replacement for ABI 9 pathname-socket protection. Source review is distinct from an executed enforcement result. Fresh leanchecker runs under read-only Landrun. The ordinary original-prefix Lake trace check evaluates trusted package configuration outside Landrun. Native and Linux results have different isolation and execution coverage and remain separate.

Tool versions differ by run. The OpenAI tooling includes Comparator `865edc14486c3388e9225daa971da8e157488c3e` built under Lean 4.35.0. The native Anthropic tooling additionally records its CI Comparator source pin `575674928e239f5bc452aab72d1dd7b0f1326494`, built under Lean 4.34.1 rather than that tool's pinned 4.34.0-rc1; Linux uses the latter exact tool version. Only actual completed receipts establish which binary and configuration a check used; no stage is claimed here merely because a tool exists. Exporters are built with each proof's exact compiler; Nanoda is pinned to `68d5ca9db226849b41a6fff59d796ff19d0a8840`.

## Original evidence and public derivatives

`PUBLIC_MANIFEST.json` records each original local SHA-256/size and the exported copy's separate SHA-256/size. A `byte_identical` entry is unchanged. A `sanitized_derivative` has ordered redaction rules with exact byte spans and intermediate hashes; removed private values are not repeated in the public record. Source manifests and command receipts may still refer to **original** hashes, which should not be compared to redacted bytes as if they were identical.

Python sources requiring local-path changes have an explicitly labelled portable derivative and a redacted source view. The manifest binds both to the original executed source. These derived copies were syntax-checked during packaging, not rerun as proof experiments. Default relative layouts are preserved; set `ETH_REPLICATION_ROOT` for another artifact root. `ETH_PROJECT_ROOT` is needed only by captured utilities that reference the private project ledger. Such ledger helpers are provenance material, not a promise that the private coordination package is available publicly. Core proof build commands should use the separately documented public dependencies and standalone harnesses.

Large exported proof environments remain local unless separately released as assets. Their completed-recorder receipts provide reported sizes and hashes; the package manifest states availability and whether the packager rehashed them. A missing export asset is not silently supplied or treated as a fresh independent recheck.

## Contribution and limits

Earlier public replication reports include [Totó Busnello](https://github.com/totobusnello/eth-subexp-note) and [Carlos Toledo](https://carlostoledo.co/eth/). This effort contributes another execution record and specific reproducibility lessons, with Codex assistance disclosed. It claims no new ETH theorem, polynomial-time SAT algorithm, or practical full SHA-256d mining advantage.

The [Lean Replications thread](https://ethdiscussion.blog/2026/10/30/lean-replications/) is the appropriate announcement venue for a completed replication report. The operator authorized publication of this sanitized repository. No blog comment or email has been sent. Any final proof verdict requires review of completed stage evidence.
