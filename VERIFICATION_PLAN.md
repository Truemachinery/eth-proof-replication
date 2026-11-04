# External ETH proof replication: verification plan

Prepared 2026-11-04 by Codex agent `codex-eth-verification-plan`, under root task
`external-eth-proof-replication-20261104` (discussion plan #10063).

This is a pre-execution methods and environment review. It records no acceptance of either external proof.
Build, kernel, axiom, statement-comparison and semantic-review outcomes must receive separate result fields.
The operator authorized local replication; no external publication, paid cloud, VM startup or global tool
installation was performed by this reviewer.

## Native host preflight

Read-only preflight at approximately 16:58–17:01 UTC found:

| Component | Observation |
| --- | --- |
| Host | macOS/Darwin 27.0.0, arm64 |
| Python on default PATH | 3.9.6 |
| Existing user Lean | 4.35.0, commit `eb6cafb7290e8bd5f2937522d8d804f58f02bafc`, arm64 Darwin |
| Existing user Lake | 5.0.0-src+eb6cafb |
| Existing user Elan toolchains | Only `leanprover/lean4:v4.35.0` before this campaign's separate local downloads |
| Existing 4.35 binaries | `lean`, `lake`, `leanchecker`, `lean4lean`, `leanexport`, `leanchecker-paranoid` |
| Missing on PATH | `cargo`, `rustc`, `go`, `landrun`, `nanoda_bin`, `lean4export` |
| Docker | Client 29.5.3; selected context `colima`; server connection inaccessible in this sandbox |
| Colima | `colima status` reported not running; no instance was started |
| Lima | Default `limactl list --json` reported no instance; this does not inventory Colima's separate internal instance directory |

The existing 4.35 checker binaries are not evidence of compatibility with 4.34.1 or 4.33.1 `.olean` files.
Use each proof's exact pinned toolchain. Keep new toolchains, caches, source and logs inside this campaign's
directories, without modifying the project's shared Lean library or user-global installation.

One preflight mistake is retained: `leanchecker --help` was attempted with a 10-second subprocess timeout and
timed out without a verdict. Its parser does not implement a help option; flags other than its recognized
ones are ignored. Do not repeat this command or interpret it as a proof check. Preflight commands were not
separately resource-metered; no cost estimate is inferred from their wall duration. External compute cost: USD 0.

Read-only commands used were `uname -a`, `python3 --version`, executable discovery, `lean --version`,
`lake --version`, `elan toolchain list`, `docker context ls`, `docker version --format '{{json .}}'`,
`colima status`, `limactl list --json`, and limited directory/file/source inspection. `lean` and `lake` through
the default Elan shim warned that a latest-release query failed and used existing 4.35.0. No successful proof
run is claimed by any of these preflight results.

## Required verification layers

1. **Source identity and unchanged statements.** Record exact source commit, origin, `git --show-toplevel`,
   toolchain string, manifest dependency revisions, configuration and SHA-256 hashes of the statement files,
   solution files and all checking scripts. Require the Git top-level to equal the intended external checkout:
   while a clone is incomplete, `git -C intended/path rev-parse HEAD` can silently resolve the enclosing lab
   repository. Record archive and executable hashes and the provenance of dependency caches.
2. **Fresh proof build.** Compile the intended solution target under its pinned compiler. A downloaded Mathlib
   cache is acceptable as a disclosed dependency cache; it is not a source rebuild of all Mathlib. Ensure the
   external proof's own solution artifacts were absent before its fresh build. Save complete output, exit
   code, command/environment, source identity before/after, measured wall/CPU and memory when available. Do not
   silently change the Lean version or source to obtain a pass. Root's initial budget is at most eight wall
   hours per proof and two configured build workers; verify the pinned Lake's actual concurrency mechanism.
   The inspected 4.35 Lake CLI has no `-j`/`--jobs` flag, so do not invent that option. A thread environment setting
   by itself should be reported as configured, not as a measured maximum number of child processes.
3. **Full-closure same-kernel replay.** After the solution builds, use the matching toolchain in its package:

   ```sh
   lake env leanchecker --fresh --verbose Solution
   ```

   Replace `Solution` only with the exact module that contains the declared OpenAI target if its configuration
   uses another name. Lean 4.34.1's source implements `--fresh` by loading the named module and replaying its
   imported constants into an empty kernel environment. This checks the solution's imported closure, unlike
   ordinary prefix-module replay. It is the same Lean kernel, not an independently written kernel. It skips
   unsafe/partial constants and admits axiom declarations, so success alone establishes neither an axiom
   allowlist nor statement identity. Capture an actual exit status and the named replay line.
4. **Target dependency and axiom audit.** Inspect the exact configured target theorems from a separate probe
   elaborated before loading the target module, loading without extensions/initializers where supported.
   Walk theorem types and proof bodies transitively through definitions, opaque bodies, constructors and
   recursors. Fail on a missing target or missing traversed constant. Accept only dependencies on the three
   configured standard axioms: `propext`, `Quot.sound`, `Classical.choice`. Record every discovered axiom and
   the exact target names. Printed `#print axioms` from a source-importing script is a useful cross-check,
   not the sole certificate; imported syntax and metaprograms can affect that script. Do not use our
   historical regex/printed-output `mining_lab.lean_verifier` as certification for this campaign.
5. **Challenge/solution identity.** Run the pinned official Comparator when feasible, preserving its exact
   named-theorem configuration. This compares the challenge statement and all relevant definitions against
   the solution environment, audits allowed axioms and replays the exported proof. A separate Lean build or
   matching pretty-printed type strings does not replace the dependency comparison. Where Comparator is not
   run, label this layer unexecuted and state exactly what manual statement review covers.
6. **Additional kernel.** Run a pinned, compatible exporter and `nanoda` if feasible. Save the export hash,
   checker source/binary hashes, effective configuration, exit status and logs. Do not enable
   `unsafe_permit_all_axioms`. If unused declarations such as `sorryAx` occur in the exported environment,
   distinguish their presence from target dependency: nanoda can skip unpermitted unused axioms with
   `unpermitted_axiom_hard_error: false`, and must then reject any theorem that tries to use one. Record the
   effective setting rather than implying every declaration in the environment was an allowed axiom.

Even all these machine checks establish formal proof acceptance for the exact statements, not the mathematical
meaning of those statements or their equality to textbook ETH. Encoding, computational model, quantifier order,
cost bounds, paper/formalization differences and the bridge to standard complexity definitions require a
separate, scoped statement review. No layer implies P=NP or a practical SHA-256d advantage.

## Expected challenge placeholders

The inspected Anthropic checkout is commit `16a5ce41304fcdaea4e0be7c132e1c361dc26da5`.
Its `eth/comparator.json` names `Challenge`, `Solution`, `MainResults.ethIsFalse` and
`MainResults.mainTheorem`, with the three standard permitted axioms and `enable_nanoda: true`.
`eth/lean-toolchain` pins 4.33.1. `Challenge.lean` deliberately contains two `sorry` proof placeholders;
it imports only the statement definitions. `Solution.lean` provides actual proofs and does not import
`Challenge`. The two expected challenge warnings are not a failed solution proof. Conversely, allow no
`sorryAx` dependency of either solution theorem. Preserve per-module warning locations rather than accepting
or rejecting a build by a global count or source grep alone.

The supplied `eth/scripts/PrintAxioms.lean` explicitly describes itself as a convenience for trusted code,
not an adversarial check. Its requested output is a cross-check of the two actual solution targets.

The pinned Anthropic CI script separately builds Comparator with its own toolchain, then builds lean4export
using the proof's toolchain. Its pins are Comparator `575674928e239f5bc452aab72d1dd7b0f1326494`,
nanoda `68d5ca9db226849b41a6fff59d796ff19d0a8840`, and Landrun
`811cfff51ceaf3d9843708aa6d22e9b84ccac8b4`. The exporter is selected at the matching release tag; for a
stable patch release lacking its own tag, the `.0` exporter source may be rebuilt with the proof's exact
compiler. Resolve and save the tag's commit rather than relying on a floating tag. This CI script is an
inspected upstream recipe, not an executed campaign result.

## Native macOS alternatives and honest labels

Landrun depends on Linux Landlock; it does not run natively on this macOS host. Comparator's repository
ships `scripts/fake-landrun.sh` specifically for non-Linux development. A native run using that shim can
exercise statement/axiom/kernel checks, but the shim provides no Landlock isolation. Report it as native
Comparator with an unsandboxed development shim, not as the full Linux CI isolation protocol. Retain source
identity and checking inputs before any solution execution. Do not start a VM or change shared Docker/Colima
state as an unrecorded workaround.

Nanoda's primary documentation describes a portable Cargo build. A local Cargo/nanoda/exporter installation
could therefore make an additional-kernel native stage feasible, but those tools were absent at preflight;
their installation, compatibility and execution remain unverified here. The existing `lean4lean` is an
additional implementation candidate, but its authors say it is derived from the C++ kernel and may share
bugs. Its presence does not justify the stronger phrase “independent second kernel,” nor has compatibility
with these proof versions been demonstrated.

Comparator's current README says that from Lean 4.35 its functionality moved into `lake comparator`/`lake check`.
That does not authorize silently upgrading the 4.34.1 or 4.33.1 proof. Pin the checker implementation and
compiler separately and disclose all version boundaries.

## OpenAI isolated-workspace recommendation

The completed OpenAI source checkout resolves to its own expected Git top-level at
`openai/source`, commit `4eaee87548250b2682affda7d05d947c05554bae`. Its configuration is
`lean/ComparatorChallenges/SubexponentialSAT.json`: challenge module
`ComparatorChallenges.SubexponentialSAT`, solution module `OAI.Algorithms.SubexponentialSAT.Main`,
target `OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat`, three standard axioms,
and `enable_nanoda: false`. Its toolchain is 4.34.1. Running a second kernel would be an additional stage,
not an already enabled upstream requirement for this configuration.

The inspected `lean/lakefile.lean:1-190` requests many unrelated mathematics projects. The relevant
package option is `autoImplicit := false`, and Mathlib is pinned to
`d13f23b723b8a846827a245b89c10fc7d3f11612`. I recommend an isolated Lake workspace containing
byte-identical proof source modules and the original challenge/configuration, preserving original module
names, that option, exact Lean version and exact Mathlib dependency closure. This avoids resolving unrelated
dependencies. It is a recorded build-configuration deviation: report replication of the exact named theorem
in that workspace, not replication of the entire upstream repository or its complete CI.

An independent lexical import scan from `OAI.Algorithms.SubexponentialSAT.Main` found 3,091 local source
modules; all their names start with `OAI.Algorithms.SubexponentialSAT.`. Their external import names are
only `Mathlib`/`Mathlib.*` and `Lean.Elab.Tactic.Omega`. No local source was missing. There are 9,845 import
directives across that closure. SHA-256 of sorted lines `moduleName + ' ' + sourceSHA256`, joined with
newline and no trailing newline, is `5c2b88aa61bee94280f15b7338f4aab537e5add0084dfcb59b51387831680974`.
The scan stripped comments/string literals using the inspected `lean_audit.strip_code` and recognized
anchored import directives including public/private/meta prefixes. This is source-provenance evidence,
not a compiler-certified import graph. Cross-check resolution with the pinned compiler's dependency query
once available, and preserve source hashes before/after. Include the minimal lakefile and dependency manifest
as campaign artifacts. The trusted challenge can be built separately; do not import its sorried theorem
into the solution/audit environment.

For a small separate-runtime axiom probe, adapt the inspected `lean_audit.py:250-324` mechanism rather than
its broad package-building wrapper: compile the probe with trusted Lean imports only, accept a module and
exact target names at runtime, load with `loadExts := false` and private data, then traverse the kernel
constant environment. Maintain a visited set, collect axiom names, walk each type and definition/proof/opaque
body, and traverse inductive constructors. Also traverse an axiom's type; do not just record its name and
return. Missing declarations must fail instead of silently returning an empty dependency set. Confirm each
requested target is a theorem. Record the initialized-extension setting, exact module/target, visited count,
axiom list, and whether it passes the declared allowlist. Cross-check foundational axiom declarations against
the trusted pinned prelude, or rely on a separately executed Comparator declaration-comparison stage; names
alone do not establish statement fidelity under an environment-mutation threat model. Pair this probe with
fresh kernel replay and saved challenge comparison. This design review is not an executed probe certificate.

## Probe implementation and trusted controls

`verification/AuditTargets.lean` implements the separate-runtime axiom walk. Official Comparator remains
responsible for challenge/solution identity. `verification/check_trusted_probe.py` runs three controls against
the pinned Lean 4.34.1 `Init` only: `Nat.add_zero` passes (32 visited constants, no axioms); a missing target
and the non-theorem definition `Nat.add` each fail with exit code 2. All three expected control outcomes pass
in `verification/trusted-probe-controls-r1.json`. This is not a run against either ETH solution.

The successful exact command was:

```sh
python3 -m mining_lab.checkpoint run --agent codex-eth-verification-plan --task eth-native-axiom-probe-20261104 --phase trusted-probe-controls --summary 'Exact4.34.1 named-target probe: trusted Init theorem accepted, missing target and definition rejected; no external proof imports' --timeout 70 --add-artifact research/eth-external-replication-20261104/verification/AuditTargets.lean --add-artifact research/eth-external-replication-20261104/verification/check_trusted_probe.py --add-artifact research/eth-external-replication-20261104/verification/trusted-probe-controls-r1.json -- python3 research/eth-external-replication-20261104/verification/check_trusted_probe.py --toolchain research/eth-external-replication-20261104/openai/elan/toolchains/leanprover--lean4---v4.34.1 --output research/eth-external-replication-20261104/verification/trusted-probe-controls-r1.json
```

Its checkpoint log is
`research/checkpoints/codex-eth-verification-plan--eth-native-axiom-probe-20261104--20261104T171033Z-795356-11056.txt`:
6.826372 child CPU seconds / 11.807582 wall seconds. Two earlier infrastructure attempts are retained:

- `20261104T170844Z-140488-9649.txt`: source elaboration succeeded, then runtime `findSysroot` found default
  Lean 4.35.0 via PATH and rejected its incompatible `Init.olean`. Cost 2.564065 CPU / 6.300377 wall seconds.
- `20261104T170926Z-012472-10208.txt`: an `/usr/bin/env` invocation treated the absolute executable path
  containing `P=NP` as an assignment and tried to execute `--run`. Cost 0.003024 CPU / 0.005086 wall seconds.

The corrected Python runner sets exact toolchain `PATH`, `LEAN_SYSROOT`, and `LEAN_NUM_THREADS=1` directly;
it removes inherited Lean module paths for these trusted-Init controls only. Actual proof checks must retain
the package-specific search paths supplied by the correct pinned `lake env`. An absolute Lake/Lean executable
does not by itself pin subprocesses or runtime `findSysroot`; set PATH and LEAN_SYSROOT coherently. The root's
first cache attempt exposed the related `Cache.IO` subprocess `lean --print-prefix` issue before proof work.

Total three checkpointed probe-control attempts: 9.393461 child CPU / 18.113045 wall seconds; earlier read-only
preflight and source-review overhead was not metered. USD 0 external compute. No proof source was changed,
no external ETH proof was imported by these controls, and no external publication occurred.

## Ready-module scheduler review and integration control

The root's `openai/build_ready.py` schedules at most two project targets whose local imports have completed,
using actual `lake build +Module` calls so Lake writes its ordinary trace files. It retains an fsynced
completion/cancellation ledger and distinct per-attempt raw logs. Review identified and root corrected partial
attempt-log collisions on resume, orphan compiler groups after a Lake parent exits, dependency-cache admission,
and final source/configuration checks. This reviewer added one further guard: resumed ledger rows must name
known modules and contain the same source digest as the current source manifest. That edit was coordinated
before the real proof build; this reviewer made no active-build source changes.

The copied scheduler was exercised against a separate trusted Lean 4.34.1 fixture under
`verification/scheduler-smoke/`: two initially ready modules A/B and dependent C. A sleeps for two seconds
during fixture compilation; B initially imports a deliberately absent external fixture. The real missing-import
error cancels/drains the live sibling group. Supplying the external fixture without changing A/B/C and resuming
completes all three, with distinct attempt logs. Source drift and changed-manifest/old-ledger digest drift are
rejected; a final ordinary Lake check and completed-ledger no-work resume succeed. All recorded process groups
were absent afterward. An additional read-only replay of the raw `MODULE_START`/`MODULE_END` events confirmed
the maximum simultaneous ready-target starts was two and C started only after successful A/B completions.

```sh
python3 -m mining_lab.checkpoint run --agent codex-eth-verification-plan --task eth-native-axiom-probe-20261104 --phase scheduler-integration-smoke --summary 'Real Lean4.34.1 isolated scheduler smoke:2ready modules, dependent, missing-external failure/resume, guards, group cleanup' --timeout 120 --add-artifact research/eth-external-replication-20261104/verification/run_scheduler_smoke.py --add-artifact research/eth-external-replication-20261104/verification/scheduler-smoke/result.json --add-artifact research/eth-external-replication-20261104/openai/build_ready.py -- python3 research/eth-external-replication-20261104/verification/run_scheduler_smoke.py
```

Checkpoint log `research/checkpoints/codex-eth-verification-plan--eth-native-axiom-probe-20261104--20261104T171405Z-036476-12904.txt`
records 6.501294 child CPU / 12.006026 wall seconds. The fixture result preserves the exact tested scheduler
hash. Before the actual proof launch, root separately added a dependency-preflight receipt/manifest hash guard;
that small later addition is not included in the copied scheduler's integration-test hash. Configure and report
two ready Lake targets with two Lean threads each, rather than claiming only two total CPU threads. These are
scheduler controls, not acceptance of an ETH theorem or a formal proof of process-control behavior.

Combined checkpointed probe/scheduler-control subtotal is 15.894755 child CPU / 30.119071 wall seconds, with
small coordination/source-inspection overhead unmetered and USD 0 external compute. The root's proof build,
dependency/cache work and official checking tools are separate resource records and must not be counted here.

## Inspected sources and reproducibility references

Local files/ranges actually inspected for this methods review:

- `research/lean-audit-notes-claude-20261102.md:1-268` (earlier review and continuation): historical wrapper
  false-accept controls, incomplete import coverage, replacement audit and its incomplete second review.
  SHA-256 `ff0ebb080b4c7a37b1506513ae49c233a0986a49958430a59f59e0c44ab3f67e`.
- `mining_lab/lean_audit.py:1-145,250-324` and targeted symbol searches: independent-runtime environment probe
  and explicit dependency traversal. SHA-256 `5d5df4b5a5ad8652ed15fd479f2fa4e5be1b6966a568251b2f93eabc7112e3e4`.
- Anthropic pinned `eth/README.md`, `Challenge.lean`, `Solution.lean`, `comparator.json`, `lean-toolchain`,
  `lakefile.toml`, `scripts/PrintAxioms.lean`; `.github/scripts/comparator-check.sh:1-139` and
  `.github/workflows/lean-projects.yml:30-65` plus targeted verification-step searches. CI script SHA-256
  `44e52bf00470eafe1b8c1b24d32ac28c2912b8151ae5d9a8ce57bd6f1be7bc3a`.
- OpenAI pinned `lean/lakefile.lean:1-190`, `lean/lean-toolchain`,
  `lean/ComparatorChallenges/SubexponentialSAT.{json,lean}`, `lean/OAI/Algorithms/SubexponentialSAT/Main.lean`;
  lexical import-closure/source-hash scan described above. This is not proof-body review of all 3,091 modules.
- Installed Lean 4.35 `src/lean/LeanChecker.lean` and Lake CLI help/source, targeted version and executable
  inventory. This is not an audit of those implementations.

Primary external sources read, with commands/API semantics derived from the cited implementations:

- [Lean 4.34.1 LeanChecker source](https://github.com/leanprover/lean4/blob/v4.34.1/src/LeanChecker.lean),
  especially lines 10–35 and 51–107; [replay implementation](https://github.com/leanprover/lean4/blob/v4.34.1/src/Lean/Replay.lean),
  especially lines 164–178.
- [Comparator README](https://github.com/leanprover/comparator/blob/865edc14486c3388e9225daa971da8e157488c3e/README.md),
  requirements, development mode, statement comparison and dependency/axiom checks;
  [pinned CI-version macOS shim](https://github.com/leanprover/comparator/blob/575674928e239f5bc452aab72d1dd7b0f1326494/scripts/fake-landrun.sh).
- [lean4export documentation](https://github.com/leanprover/lean4export), module export and transitive
  dependencies; [4.34.0 exporter toolchain](https://github.com/leanprover/lean4export/blob/v4.34.0/lean-toolchain)
  and [4.33.0 exporter toolchain](https://github.com/leanprover/lean4export/blob/v4.33.0/lean-toolchain).
- [Landrun requirements](https://github.com/Zouuup/landrun#requirements), Linux Landlock dependency.
- [Nanoda documentation](https://github.com/ammkrn/nanoda_lib), Cargo build and axiom-policy configuration.
- [Lean4Lean documentation](https://github.com/digama0/lean4lean), fresh mode and kernel implementation provenance.

Review scope is exact listed files/ranges and selected prior reports, not a claim to have semantically audited
the entire experiment log, either ETH proof development, every dependency or the host's virtualization setup.
