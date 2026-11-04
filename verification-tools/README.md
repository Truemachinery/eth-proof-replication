# Native verification tools prepared on 2026-11-04

These are official upstream tools built for the separate ETH proof-replication runs. **This tooling task has not checked either external ETH proof.** The source/binary inventory, complete build attempts and five small CLI checks are in [tool-manifest-r1.json](tool-manifest-r1.json). Compiler executable hashes and effective build environment are in [compiler-identities.json](compiler-identities.json). Lean's small launchers do not identify the entire kernel/runtime: [runtime-identities.json](runtime-identities.json) separately pins five shared libraries and `leanchecker` for each of the three Lean toolchains (18 files). Different patch toolchains can have identical launcher bytes.

## Sources and executables

| Tool | Pinned official input | Compiler | Executable below this directory |
| --- | --- | --- | --- |
| Comparator | [leanprover/comparator](https://github.com/leanprover/comparator/tree/865edc14486c3388e9225daa971da8e157488c3e), `865edc14486c3388e9225daa971da8e157488c3e` | Lean 4.35.0 | `comparator-source/.lake/build/bin/comparator` |
| Comparator's export parser | Manifest dependency [lean4export](https://github.com/leanprover/lean4export/tree/5a9a355dc6c5fd82b69058d433e2ae2e8dfbf8fe), `5a9a355dc6c5fd82b69058d433e2ae2e8dfbf8fe` | Lean 4.35.0 | Compiled into Comparator |
| OpenAI-compatible exporter | [lean4export v4.34.0](https://github.com/leanprover/lean4export/tree/076e8e57707e813375e8f9da8bf989799ace9680), `076e8e57707e813375e8f9da8bf989799ace9680` | Exact proof Lean 4.34.1 | `lean4export-434-source/.lake/build/bin/lean4export` |
| Anthropic-compatible exporter | [lean4export v4.33.0](https://github.com/leanprover/lean4export/tree/15f6055e299ad5b89345e533cc2192f4cc00f659), `15f6055e299ad5b89345e533cc2192f4cc00f659` | Exact proof Lean 4.33.1 | `lean4export-433-source/.lake/build/bin/lean4export` |
| Nanoda | [robsimmons/nanoda_lib](https://github.com/robsimmons/nanoda_lib/tree/68d5ca9db226849b41a6fff59d796ff19d0a8840), `68d5ca9db226849b41a6fff59d796ff19d0a8840` | Rust 1.99.1, native aarch64-apple-darwin | `nanoda-source/target/release/nanoda_bin` |

The Nanoda fork/pin is the one used by the inspected Anthropic CI script. Its [release page](https://github.com/robsimmons/nanoda_lib/releases) showed no releases; an older parent-repository release would not establish the identity of this pinned checker. We built from source. The same CI script explicitly permits a patch `.1` Lean compiler with its matching `.0` exporter source tag. No upstream tracked tool sources or manifests were edited; the manifest confirms all four source checkouts remain clean.

Both exporters' emitted metadata reports the intended proof compiler (4.34.1 or 4.33.1) and format 3.1.0. The pinned Nanoda parser accepts format versions from 3.1.0 inclusive to 3.2.0 exclusive. That is a format-compatibility check, not evidence that either proof passes.

## Isolation and checker coverage

The [Comparator development instructions](https://github.com/leanprover/comparator/blob/865edc14486c3388e9225daa971da8e157488c3e/README.md#development) provide `scripts/fake-landrun.sh` for non-Linux development. We retained that exact upstream file, SHA-256 `167507c89d8b3c7667ad78b50df7b19f89883751a01efd1457404fa34a994e8b`. It discards Landrun access flags, prints a warning and runs the child **without an operating-system sandbox**. This native mode does not reproduce the Linux Landrun/systemd isolation protocol. There is no custom replacement shim in this task.

The configured Comparator stages still compare trusted challenge/solution declarations, inspect permitted axioms, and replay the exported environment in its Lean 4.35.0 kernel. Whether they actually complete must be recorded by the proof owner. OpenAI's original configuration disables Nanoda; Anthropic's enables it. Any additional OpenAI two-kernel configuration must be saved and labelled separately from the official configuration. Preserve all emitted shim warnings.

The pinned Comparator's `Main.lean` creates temporary Nanoda configurations with only `propext`, `Quot.sound`, and `Classical.choice`, hard rejection of unpermitted axioms, Nat/String extensions enabled, and **four checker threads**. It removes its temporary configuration and export afterwards. The proof owner should preserve the effective configuration and export identity through a separately reviewed recording mechanism. Thread count is a runtime-budget choice to resolve before execution. This tooling task did not alter the upstream setting or run an external proof check. Do not add `Lean.trustCompiler` or a permit-all policy from the older Nanoda README example.

## Build commands and environment

Every download/build is wrapped by `mining_lab.checkpoint run`; the [logs](logs/) contain the exact child argv, output, failures and timestamps. Their checkpoint receipts in the manifest contain exit codes, measured CPU/wall time and log hashes. Set the following task-specific paths when reproducing commands (use absolute paths for this checkout):

```sh
VERIFICATION_TOOLS="$PWD/research/eth-external-replication-20261104/verification-tools"
OAI_LEAN="$PWD/research/eth-external-replication-20261104/openai/elan/toolchains/leanprover--lean4---v4.34.1"
ANTHROPIC_LEAN="$PWD/research/eth-external-replication-20261104/anthropic/elan/toolchains/leanprover--lean4---v4.33.1"
LEAN_435="<HOME>/.elan/toolchains/leanprover--lean4---v4.35.0"

LEAN_NUM_THREADS=2 "$LEAN_435/bin/lake" --dir "$VERIFICATION_TOOLS/comparator-source" build comparator
LEAN_NUM_THREADS=2 "$OAI_LEAN/bin/lake" --dir "$VERIFICATION_TOOLS/lean4export-434-source" build lean4export
LEAN_NUM_THREADS=2 "$ANTHROPIC_LEAN/bin/lake" --dir "$VERIFICATION_TOOLS/lean4export-433-source" build lean4export
```

The official Rust shell installer was downloaded and inspected rather than piped into a shell. We then downloaded archived [rustup-init 1.29.3](https://static.rust-lang.org/rustup/archive/1.29.3/aarch64-apple-darwin/rustup-init) and its [official SHA-256](https://static.rust-lang.org/rustup/archive/1.29.3/aarch64-apple-darwin/rustup-init.sha256), and matched `63752a1919a3a4793173ec70f8f212621a7ce38ba6a246095984482f4de20f9f` before executing it. The official stable-channel metadata identified Rust 1.99.1, which we selected explicitly. Shell-profile/PATH modifications were disabled by the installation command; no global Rust installation or Homebrew command was used.

```sh
RUSTUP_HOME="$VERIFICATION_TOOLS/rustup" CARGO_HOME="$VERIFICATION_TOOLS/cargo" \
  "$VERIFICATION_TOOLS/rustup-init" --yes --default-host aarch64-apple-darwin \
  --default-toolchain 1.99.1 --profile minimal --no-modify-path --no-update-default-toolchain

RUSTUP_HOME="$VERIFICATION_TOOLS/rustup" CARGO_HOME="$VERIFICATION_TOOLS/cargo" \
RUSTC="$VERIFICATION_TOOLS/rustup/toolchains/1.99.1-aarch64-apple-darwin/bin/rustc" \
CARGO_BUILD_JOBS=2 \
  "$VERIFICATION_TOOLS/rustup/toolchains/1.99.1-aarch64-apple-darwin/bin/cargo" \
  build --release --locked --jobs 2 --manifest-path "$VERIFICATION_TOOLS/nanoda-source/Cargo.toml"
```

The Cargo lockfile was retained unchanged. Source checkouts, isolated Rust/Cargo caches and the installer binary are excluded by this directory's [.gitignore](.gitignore); their identities remain in the manifest. Public release should use the parent's explicit export allowlist rather than copying these installations.

## Results, failures and costs

Successful source builds: Comparator 16 jobs, 12.593234 CPU / 17.874118 wall seconds; OpenAI exporter 6 jobs, 8.896153 / 13.151267; Anthropic exporter 6 jobs, 10.628250 / 14.795523; Nanoda 28.989273 / 22.666822. Rust installation added 6.256877 / 11.300313. The CLI audit added 1.487352 / 8.303531.

Across the first 17 checkpoint-wrapped stages, including downloads and the failed attempts, recorded child CPU sums to **70.016692 seconds** and stage wall times sum to **97.228107 seconds**. The subsequent runtime inventory and recorder probe bring the 19-stage totals to **71.827453 CPU seconds / 99.894305 summed wall seconds**. Some stages overlapped, so the wall sum is not elapsed duration. Source review, metadata reads, document preparation, energy and peak memory were not metered. Local Mac only, USD 0 purchased compute, no cloud, mining network, wallet or publication actions. The parent CPU lease #10067 covers these correctness builds; the 30-minute tooling cap was not approached.

Three failed first launches are retained: Comparator ran from the checkpoint wrapper's project-root cwd without `--dir`; the exporter command passed a workspace path containing `=` directly after `env`, which interpreted it as an assignment; Nanoda's first Cargo command could not locate `rustc` until an explicit task-local `RUSTC` was supplied. These failed before compilation and do not indicate proof failures. The successful Lean links warn about an absent `/usr/local/lib`; Nanoda's build reports a nonfatal debug-stripping warning because Rust's `rust-objcopy` could not load `libLLVM.dylib`. The built binaries subsequently execute the recorded CLI checks.

The five checks cover Comparator's missing-config diagnostic, each exporter's empty-environment metadata/version, and Nanoda's missing-config diagnostic/help. No hostile upstream test fixtures or external ETH modules were executed in this task. These checks establish executable identity and basic invocation/format readiness, not checker correctness or acceptance of either ETH development.

## Durable native Nanoda recording

[record_nanoda.py](record_nanoda.py) is an explicitly **Codex-authored recording wrapper**, not upstream Nanoda or a replacement proof checker. It works only with the exact reviewed native fake-landrun shim and the Nanoda binary pinned by `tool-manifest-r1.json`. The original one-element config argument is forwarded unchanged; no theorem, axiom list, export, thread setting or other checker policy is rewritten.

For a later parent-authorized native Comparator invocation, set:

```sh
COMPARATOR_LANDRUN="$VERIFICATION_TOOLS/comparator-source/scripts/fake-landrun.sh"
COMPARATOR_LEAN4EXPORT="$VERIFICATION_TOOLS/lean4export-434-source/.lake/build/bin/lean4export"
COMPARATOR_NANODA="$VERIFICATION_TOOLS/record_nanoda.py"
NANODA_REAL_BINARY="$VERIFICATION_TOOLS/nanoda-source/target/release/nanoda_bin"
REPLICATION_CHECKER_RECORD_DIR="/absolute/path/to/this/replication/run-records"
export COMPARATOR_LANDRUN COMPARATOR_LEAN4EXPORT COMPARATOR_NANODA NANODA_REAL_BINARY REPLICATION_CHECKER_RECORD_DIR
```

The record directory must be inside this replication artifact tree; each invocation gets a new exclusive child directory. Choose the 4.33.1 exporter instead for Anthropic. OpenAI's original config does not request Nanoda, so merely setting `COMPARATOR_NANODA` does not add a second kernel; save an explicitly labelled additional configuration if that check is requested.

Before executing Nanoda, the wrapper fsyncs the exact effective configuration, a streaming gzip copy of the exported bytes, and a prepared receipt with raw/compressed SHA-256 and sizes, binary/source identities, actual argv and policy. It records the child PID and later writes a finished receipt containing the real checker exit, CPU/wall time and before/after byte-identity checks. Normal exits and terminating signals are propagated; wrapper/archive/drift failures have distinct exit 125 and error receipts. The original temporary input files are never edited. A finished recording is not proof acceptance unless its actual checker exit is zero and the parent Comparator also completes its other checks.

The bounded [probe](recorder-probe-r1/probe-results.json) exports only trusted `Init`'s `Nat.add_zero` with Lean 4.34.1, then invokes real Nanoda through the recorder. It verifies successful checking, exact original argv/config, gzip/raw-byte equality, all hashes and unchanged inputs. A malformed-NDJSON control is rejected with the same real checker exit as a direct invocation. Both cases pass; cost 1.164564 CPU / 1.911097 wall seconds, within the requested 60-CPU/120-wall probe cap. The probe uses two checker threads; the upstream Comparator's actual temporary setting remains four and will be recorded as supplied. A separate Codex reviewer inspected the wrapper and found no acceptance-policy weakening; this is not independent human review.

Operational limits: the parent must terminate and drain the entire checker process group on interruption, since direct SIGTERM of the Python wrapper alone is not handled by its exception path. Missing final receipts/incomplete archives must not count as completion. The copied config still names Comparator's original temporary export path; replay requires a separately saved config pointing to the retained export, with its own new hash. Full-proof copying, compression and hashing can add substantial I/O/CPU; charge recorder overhead separately using the recorded wrapper/checker timings. Before/after hashes are not protection against an adversary modifying and restoring inputs during execution. This remains the disclosed native development mode without Landrun isolation.
