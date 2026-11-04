# Verification-method review handoff

Date: 2026-11-04. Reviewer label: `codex-eth-verification-plan` (same Codex team as replication lead).
This is source/tool review and trusted-fixture evidence, not an outside mathematical review or an ETH proof verdict.

The exact OpenAI minimal-workspace source set independently matched the lead's extraction: 3,091 OAI modules,
plus the original challenge. All 3,092 copied sources matched their manifest digests. Preserving original module
names, exact Lean 4.34.1, exact Mathlib revision and `autoImplicit=false` is appropriate for an explicitly scoped
isolated-workspace replication. It does not reproduce every unrelated upstream dependency or the full Linux CI.
The native official Comparator should own challenge/solution statement and definition-graph comparison. Its
development fake-Landrun shim is an isolation deviation that must remain visible in any report.

`AuditTargets.lean` provides a redundant separate-runtime target axiom inspection with imported extensions and
initializers disabled, missing/non-theorem/dependency checks, standard-axiom signature comparison to trusted Init,
and a raw type/body dependency traversal. The three trusted Init controls passed under the exact 4.34.1 compiler.
The source is not a replacement for kernel replay or Comparator, and has not been independently audited outside
this same team. `VERIFICATION_PLAN.md` records commands, initial infrastructure failures, exact scope and costs.

The ready-module scheduler's real Lean fixture passed failure/resume, unique-log, source/ledger drift and group
cleanup controls. Root subsequently added a dependency-receipt manifest hash guard before the real source build.
No reviewer changes were made after that proof build began. Root owns the experiment-log append for the full
campaign. Checkpointed reviewer control subtotal: 15.894755 CPU / 30.119071 wall seconds; read/coordination overhead
unmetered; USD 0 external compute. Retain both initial probe infrastructure failures.

## Next checks after actual proof build

Use the exact package-specific `lake env`, exact toolchain PATH and `LEAN_SYSROOT`. The absolute executable path
alone does not fix runtime `findSysroot` or child `lean --print-prefix` lookups. The OpenAI target invocation is:

```sh
lake env lean --run /absolute/project/research/eth-external-replication-20261104/verification/AuditTargets.lean OAI.Algorithms.SubexponentialSAT.Main OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat
```

Save output and exit status as a new result; do not overwrite trusted-control artifacts. Anthropic's two target
names are `MainResults.ethIsFalse` and `MainResults.mainTheorem` in module `Solution`, using its exact 4.33.1 toolchain.
Expected `Challenge.lean` placeholders must not become solution dependencies. Record full-closure same-kernel
replay, axiom audit, official statement comparison and nanoda acceptance as separate stages with exact exports.

## Material suitable for a public replication note

Keep original local raw logs immutable; prepare a separate sanitized public package if publication is authorized.
The public report should include the exact upstream source commits, toolchain and checker revisions, source and
export digests, dependency-cache provenance, executed commands, complete verdicts, resource measurements and
all isolation/configuration deviations. Distinguish source-built proof modules from downloaded Mathlib artifacts.
Use “independent execution from the proof authors” only with a clear account of our execution; our same-team
subagents do not establish a second independent research group or an independently authored proof.

Avoid copying the entire lab, shared boards or general checkpoint history into a public package: they contain
unrelated private project context. Select only the external-replication artifacts. Review the selected copies for
credentials and unrelated private material; replace local absolute username/project paths in public copies with
documented placeholders where useful, without changing verdicts or command semantics. Preserve and disclose the
hash distinction between original logs and sanitized copies. Do not claim the sanitized file has the original hash.

Name the responsible human author, affiliation and actual coauthors as supplied by the operator. Do not invent
affiliations or attribution. Credit AI assistance accurately. A blog comment or email remains a draft until the
operator explicitly authorizes transmission. Do not present pending builds/checks as successes, a failed checker
as a proof refutation without diagnosis, finite experiments as asymptotic consequences, or formal acceptance as
automatic verification of the informal ETH interpretation.
