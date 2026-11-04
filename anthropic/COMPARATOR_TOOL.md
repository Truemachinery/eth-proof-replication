# Anthropic CI-pinned Comparator source, native build

This is verification-tool preparation, not an ETH proof-check result. The exact
Anthropic CI driver source was acquired at
`575674928e239f5bc452aab72d1dd7b0f1326494` from
<https://github.com/leanprover/comparator>. Its unchanged manifest pins its parser
dependency, lean4export, at `b18d673bd29b476466a51a3be1012df2ed322b10`.

The driver requests Lean `v4.34.0-rc1`. It was successfully built without source
or manifest changes using the already available isolated Lean `v4.34.1`, commit
`5045d0056413266e57c625dcd7c365b10e377c52`. This compiler change is a disclosed
deviation from the upstream CI environment. A recorded version command and the
actual compiler invocation in `Main.trace` establish the compiler used. The
separate proof source continues to use its exact required Lean `v4.33.1`.

The native executable is:

```text
tools/comparator-ci-source/.lake/build/bin/comparator
```

Its SHA-256 is
`8401e6d3e3d435daa3f41af613972fcd90432e98d3b29bdc107773f715c1f7a7`.
[comparator-ci-tool-manifest-r1.json](comparator-ci-tool-manifest-r1.json) records
every tracked driver/dependency source file, binary and runtime-library hashes,
clean Git states, command records, full-output hashes and the negative CLI smoke.

The successful build completed all 16 jobs in 37.229074 wall / 23.349228 child CPU
seconds, maximum individual child RSS 1,389,641,728 bytes. The missing-config
smoke correctly exits 1 with `Expected config file path as first argument.`;
that establishes basic invocation only. An initial launcher failed before any
compilation because `env` treated the workspace executable path containing `=`
as an assignment. The corrected command uses `/usr/bin/arch -arm64` before that
executable path. The failed invocation remains in `logs/comparator-ci-build-r1.*`.

This driver's official `scripts/fake-landrun.sh` is byte-identical to the already
reviewed shared development shim (SHA-256
`167507c89d8b3c7667ad78b50df7b19f89883751a01efd1457404fa34a994e8b`). It discards
Landrun flags and executes without Linux operating-system isolation. We do not
claim a verbatim reproduction of the Linux CI environment.

Unlike shared Comparator `865edc`, this CI-pinned driver **does not write a
`num_threads` key** into Nanoda's effective configuration. Pinned Nanoda
`68d5ca9` defaults that usize to 0, which selects its serial checking branch.
The three permitted axioms, strict unpermitted-axiom failure and Nat/String
extension settings remain supplied by the unchanged driver. Any later checker
run must preserve and record this actual effective configuration. No external
proof was passed through this driver during tool preparation.

All work is local; USD 0 purchased compute. Source acquisition, metadata reads,
model inference and energy were not separately metered. Source/binary identity
does not establish checker correctness or mathematical faithfulness of a theorem.
