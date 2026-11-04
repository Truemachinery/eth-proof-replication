# Follow-up verification review: configuration r2 and tooling

2026-11-04, `codex-eth-verification-plan`. This new note preserves the earlier pinned plan and handoff.
It records a missed integration case and subsequent source review; it does not record an ETH proof verdict.

## Missed library-registration case

The first actual OpenAI scheduler attempt reported unknown internal modules before proof elaboration. The
minimal package initially declared only `OAI.Algorithms.SubexponentialSAT.Main` as an OAI library root.
The scheduler invokes `lake build +Module` for each internal imported module, so those explicit targets also
need library membership. My earlier fixture declared all three scheduled modules as roots; it exercised
dependency ordering, failure/resume and cleanup but did not cover this registration distinction. I missed
that mismatch in my initial configuration review. Its passing controls did not establish that the original
minimal configuration registered every internal proof module.

Root preserved the original prepare/scheduler/lakefile under `openai/revisions/`, left the source manifest
immutable and introduced `openai/workspace-config-r2.json`. The r2 Lakefile adds:

```lean
  globs := #[`OAI.Algorithms.SubexponentialSAT.+]
```

to the OAI library and `globs := #[`ComparatorChallenges.+]` to the challenge library. This matches syntax
used by the original upstream package and covers the independently scanned local module names. The r2
configuration retains exact Lean 4.34.1, the original Mathlib pin and `autoImplicit=false`; no proof bytes
changed. The revision refers to original source-manifest SHA-256
`bf7f36120177010243e52dd9053bd3e9f97f92fa35184abf173a8a57ef4843e1`; the new Lakefile hash is
`aea9d368f24768ab9d51d8c9216c1dd60e598a983e63c463dc8de3f605d268fb`.

I read the r2 configuration, current Lakefile and scheduler configuration/receipt/resume/final-guard sections.
The explicit `--configuration` revision guard replaces only the expected package-configuration hash list,
while source hashes and prior-ledger source hashes are still checked. The dependency receipt separately
matches the workspace dependency manifest. This is a reasonable source-preserving correction for the retry;
it is not retrospective evidence that the first attempt passed. Root reported zero successfully compiled
project proof modules in the failed initial attempt. No reviewer edits were made during either actual build.

The root also observed a `PermissionError` from process-group signaling in the actual restricted execution
context. My separate trusted fixture had observed successful cancellation and absent groups, using default
tool permission requests. Both observations must remain visible; the fixture is not a universal process-control
permission guarantee. Root separately checked its exact remaining child PID and reported it absent, then
planned a retry with the required local process-control permissions. This is infrastructure diagnosis, not a
proof failure or rejection of the external theorem.

## Independent read-only tooling provenance check

I checked each Git top-level and HEAD, tracked working-tree status and all listed tracked-file digests from
`verification-tools/tool-manifest-r1.json`: 150 tracked files across four checkouts matched current bytes,
and all four tracked working trees were clean:

| Tool source | Commit |
| --- | --- |
| Comparator | `865edc14486c3388e9225daa971da8e157488c3e` |
| lean4export 4.34.0 source | `076e8e57707e813375e8f9da8bf989799ace9680` |
| lean4export 4.33.0 source | `15f6055e299ad5b89345e533cc2192f4cc00f659` |
| nanoda | `68d5ca9db226849b41a6fff59d796ff19d0a8840` |

The tooling agent built the two exporters with the actual 4.34.1 and 4.33.1 compilers, respectively. Saved
CLI metadata reports export format 3.1.0 and the corresponding Lean versions. CLI smoke checks establish
executable startup and metadata only; no external proof was checked by those smokes or by this source review.

I inspected Comparator `Main.lean:80-185`, `Comparator/Axioms.lean` and `Comparator/Compare.lean`.
It exports the selected declarations, checks transitive allowed axioms, compares the theorem statement and
referenced definition graph across separate environments, and uses a strict three-standard-axiom nanoda
configuration with four checking threads when nanoda is enabled. Preserve the actual effective configuration
and exported bytes/digest in the proof run. The upstream fake-Landrun shell shim remains unsandboxed;
its warning and the loss of Linux Landlock isolation must remain explicit.

One identity detail needs a separate supplement: Lean 4.34.1 and 4.33.1 have identical small `bin/lean` launcher
hashes despite different runtime versions. The executable alone is therefore not a hash of the full dynamic
kernel/runtime. I requested new immutable runtime identities for the toolchain's `libleanshared*.dylib`,
`libInit_shared.dylib`, `libLake_shared.dylib` and `leanchecker` (or the complete original toolchain archive).
Do not silently reinterpret the existing launcher hashes as full compiler identities.

No additional test/build CPU was consumed by this follow-up source/metadata review; small read, hash and Git
inspection overhead was not separately metered. No paid compute, publication, wallet access or mining-network
operation occurred. The earlier checkpointed control subtotal remains 15.894755 child CPU seconds and
30.119071 wall seconds, separate from root and tooling-agent resource ledgers.
