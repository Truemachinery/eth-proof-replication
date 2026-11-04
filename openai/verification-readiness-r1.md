# OpenAI native verification readiness — read-only review

Reviewed 2026-11-04 by `codex-eth-anthropic-replication`, at the parent's request.
No proof, compiler, exporter, Comparator or Nanoda execution was performed.
The active source build was not edited or interrupted. This report is readiness
guidance; every actual OpenAI checker verdict remains pending.

## Exact contract and source boundary

Official source commit is `4eaee87548250b2682affda7d05d947c05554bae`.
Original Lean is 4.34.1; Mathlib is
`d13f23b723b8a846827a245b89c10fc7d3f11612`.
The original configuration is
`source/lean/ComparatorChallenges/SubexponentialSAT.json`, outside the minimal
workspace. Its sole named theorem is
`OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat`.
The solution module is `OAI.Algorithms.SubexponentialSAT.Main`; the trusted
template module is `ComparatorChallenges.SubexponentialSAT`.

The source manifest graph gives 3,091 project modules in Main's closure; the
Challenge template is absent. The union built by the native runner has 3,092
modules. Challenge's intentional `sorry` must remain confined to the template;
audit the solution module alone. Main's documentation also names another theorem,
but that additional name is not a target of this original Comparator JSON.

The selected theorem (SqrtLogSpace/Final.lean:74) quantifies over each fixed
`k >= 2`, then provides a finite primitive machine and positive constants. It
exactly counts and decides every width-at-most-k input, meets the stated
square-root-logarithmic time bound, and bounds visited tape space at every prefix.
The primitive model in Challenge reads one selected tape head and performs one
cell move/write or halts. Interpretation and practical constants remain separate
from the checker execution.

| Reviewed input | SHA-256 |
| --- | --- |
| Original Comparator JSON | `debbfdc9c01104d2369be80da5180978275106df8b685f693fba7ce7da7c5b19` |
| Main.lean | `cbd4cebf71f1d3239c21241f946d05e8de802dbb9c138713f8e7182d868b2d1c` |
| SqrtLogSpace/Final.lean | `040360a8465957622d934e5f1bb4f2cce8dab950e78f52033fbf70da493184f5` |
| Challenge source | `4183b2057cff350d66848215ff7167196dfc20e1891b598fdddea59077a76685` |
| Native source-manifest.json | `bf7f36120177010243e52dd9053bd3e9f97f92fa35184abf173a8a57ef4843e1` |
| workspace-config-r2.json | `a56c999ec870742bee9c51be2bb3199d358d77876d5e7d49492f5ad880938413` |
| workspace/lakefile.lean | `aea9d368f24768ab9d51d8c9216c1dd60e598a983e63c463dc8de3f605d268fb` |
| in_workspace.py | `b4e80df9ed1f1c71e7a202feccd94f189113610679d4a28ac3728d8708e7d04a` |
| Trusted AuditTargets.lean | `a78f30e0439e85d3a9ae51828e0e42c248c027a7fcfeb4c4fb16cb776fae0b05` |

The minimal Lake package and compiler-admission prefix are disclosed deviations
from upstream packaging. Proof files, original toolchain, autoImplicit setting
and dependency pins must remain as recorded. Preserve the earlier failed setup
and transition receipts when describing the final build.

## Tool identities and runtime

Use shared Comparator source `865edc14486c3388e9225daa971da8e157488c3e`, built
with its requested Lean 4.35.0, rather than the Anthropic 575 driver. Current
binary SHA is `bdf09ee3e725f1480792db7b5befcbf6e4f77db90d9f1f4986bda5a1e6315f4c`.
Read-only `otool -L` reports only libc++ and libSystem dependencies for this
executable, with the Lean implementation linked into it. Original audit/fresh
checks still require the separate real 4.34.1 runtime.

The 4.34.1 exporter binary SHA is
`e6217f95bf55c5e165a62f12ec6ce1fb3c25a815cff0f9cb6f6dfcf4c8e55e25`;
its source commit is `076e8e57707e813375e8f9da8bf989799ace9680`.
Pinned Nanoda source is `68d5ca9db226849b41a6fff59d796ff19d0a8840`, binary
SHA `d9a1fc5371b84c9eb0687a7630eb724fa88886d9f5d665f09f9f926730573b80`.
These current binary hashes match the existing shared tool manifest. The reviewed
recorder SHA is `c34f36d630d182708937a5280b6eda8d0723fa0ffdd85caf8fc54af17b332f48`.

The upstream development fake-landrun shim provides native command execution,
without Linux isolation. Do not infer Linux containment from this native path.
Original 4.34.1 Replay.lean:176-194 skips unsafe/partial constants, admits axiom
declarations and postchecks constructors/recursors. Describe fresh replay as the
full imported safe, nonpartial environment, alongside separate target axiom and
statement checks.

## Proposed commands after the existing build closes

Do not execute these while build 11317 is active. First require a normal closed
source-build result and recheck all manifest source/config/dependency identities.
Use exclusive stage names and full resource/output receipts. The zsh/bash array
below clears gate and inherited Lean-library overrides before the existing
workspace helper selects the real 4.34.1 prefix. It defines proposed commands;
none was executed in this review.

```sh
REPL_ROOT='<REPLICATION_ROOT>'
REPL_OAI="$REPL_ROOT/openai"
REPL_TOOLS="$REPL_ROOT/verification-tools"
REPL_MODULE='OAI.Algorithms.SubexponentialSAT.Main'
REPL_THEOREM='OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat'
REPL_CONFIG="$REPL_OAI/source/lean/ComparatorChallenges/SubexponentialSAT.json"
REPL_REAL=(env -u LAKE_OVERRIDE_LEAN -u LEAN_SYSROOT -u LEAN_PATH \
  -u LEAN_SRC_PATH -u LEAN_PLUGIN_PATH -u DYLD_LIBRARY_PATH \
  -u DYLD_FALLBACK_LIBRARY_PATH -u LD_LIBRARY_PATH \
  python3 "$REPL_OAI/in_workspace.py")

"${REPL_REAL[@]}" lake --no-build build "+$REPL_MODULE" +ComparatorChallenges.SubexponentialSAT
"${REPL_REAL[@]}" lake env lean --run "$REPL_ROOT/verification/AuditTargets.lean" \
  "$REPL_MODULE" "$REPL_THEOREM"
"${REPL_REAL[@]}" lake env leanchecker --fresh "$REPL_MODULE"

env COMPARATOR_LANDRUN="$REPL_TOOLS/comparator-source/scripts/fake-landrun.sh" \
  COMPARATOR_LEAN4EXPORT="$REPL_TOOLS/lean4export-434-source/.lake/build/bin/lean4export" \
  "${REPL_REAL[@]}" lake env "$REPL_TOOLS/comparator-source/.lake/build/bin/comparator" "$REPL_CONFIG"
```

The real-prefix `--no-build` trace check should precede normal Comparator builds.
If it fails, diagnose the exact trace/configuration difference before allowing
normal Lake to start uncontrolled recompilation. The target audit must report a
complete event with the named theorem as a theorem declaration, only the three
standard axioms, matching trusted Init signatures, and no unsafe/partial target
dependencies. Its 4.34.1 compilation is itself still pending. The Comparator
requires exit 0 and the explicit final `Your solution is okay!` sentinel.

## Additional independent Nanoda stage

The original JSON explicitly sets `enable_nanoda: false`. Preserve it unchanged.
Setting COMPARATOR_NANODA alone does not enable an absent kernel registration.
Therefore the original Comparator pass supplies its Lean kernel and contract
checks, while the independent Nanoda result must come from a separate export.
The selected-target export's logical argv is:

```sh
"${REPL_REAL[@]}" lake env \
  "$REPL_TOOLS/lean4export-434-source/.lake/build/bin/lean4export" \
  "$REPL_MODULE" -- "$REPL_THEOREM"
```

Capture stdout into an exclusive raw `.ndjson` file, without checkpoint headers
or display prefixes; retain stderr and normal exit/resource receipts separately.
Fsync and bind the exact export size/SHA before checking it. For example, the CI
Recorder supports `stdout_file`; a normal combined textual checkpoint log is not
an export file.

Create an exclusive additional config with an absolute path to that file,
`use_stdin=false`, `permitted_axioms=[propext,Quot.sound,Classical.choice]`,
`unpermitted_axiom_hard_error=true`, `nat_extension=true`,
`string_extension=true`, and an explicitly recorded bounded `num_threads=2`.
This is an additional policy, not the original disabled Nanoda configuration.
The recorded invocation can then use:

```sh
env COMPARATOR_LANDRUN="$REPL_TOOLS/comparator-source/scripts/fake-landrun.sh" \
  NANODA_REAL_BINARY="$REPL_TOOLS/nanoda-source/target/release/nanoda_bin" \
  REPLICATION_CHECKER_RECORD_DIR="$REPL_OAI/checker-records-extra" \
  "${REPL_REAL[@]}" python3 "$REPL_TOOLS/record_nanoda.py" \
  "$REPL_OAI/additional-nanoda-config-r1.json"
```

Require actual checker exit 0, completed 02-finished metadata, unchanged
binary/config/export identities and retained exact config/archive. Label this
as Nanoda on a separately retained selected-target export, not Nanoda invoked by
the unchanged original Comparator. Finally recheck original source/config/runtime
identities and preserve all failure receipts. No current checker verdict is
implied by this readiness report.
