# Anthropic Linux continuation: accepted checks, incomplete export

The manually dispatched Anthropic-only `verify` continuation at public commit
`309670f70aa79d85752dbdc61799ad8cc56772c2` completed with a failure. Its exact
ancestor cache was validated and restored, the ordinary real-prefix no-build
check passed, and both the original-version fresh Lean checker and exact upstream
Comparator accepted again. Our subsequent retained export failed to finish.
The overall run remains **INCOMPLETE** because that export and the final source
and configuration identity seal did not complete. No theorem rejection was
observed.

Run: `41911047958`; Anthropic job: `126858374463`; OpenAI job was skipped.
The original OpenAI job in run `41894905159` remains separate and was active at
the last metadata read, 22:07 UTC. No additional job was dispatched or cancelled
by this agent.

## Preserved evidence

- `anthropic-job-126858374463.raw.log`: exact GitHub job-endpoint response,
  154647 bytes, SHA-256
  `cf44010f02577d29ffdf40f9288f97c98038bdc84bcd68dc0c8f6e539e228db5`.
  This includes a UTF-8 BOM and 755 decoded lines. It is distinct from the
  ephemeral subprocess raw files whose hashes occur inside the receipts.
- `workflow-41911047958.logs.zip`: exact completed workflow-endpoint response,
  70398 bytes, SHA-256
  `3b1817dba175be522012b458222d6986b128af47fb2873df629cb47f75c83cdd`.
  All 15 safe relative members were extracted exclusively and hashed in
  `workflow-log-members-r1.json`. Aggregate and per-step logs are duplicate
  presentations of events, not additional trials.
- `anthropic-job-summary-r1.json`: receipt derivation, 132925 bytes, SHA-256
  `ae43a88a950d8edae613becf894b8b105e4cfebf064b1818779fb560fc6fb028`.
  `parse_completed_log_r1.py` requires timestamped, unprefixed harness markers;
  checks all 39 start/finish pairs against the run aggregate; and requires the
  three exact Comparator acceptance messages in displayed child output.
- Exclusive timed download receipts are adjacent to the response bodies. The
  earlier single active-job endpoint attempt returned HTTP 404; no live stage
  inference was made from it.

## Actual stage boundary

There are 39 stage receipts: the first 38 returned zero. The final stage is
`retained-target-export`, exit 125. Selected evidence, using one-based lines in
the exact job response:

| Stage | Outcome | Wall seconds | Receipt line |
| --- | --- | ---: | ---: |
| Normal real-prefix `lake --no-build build` | exit 0, all 9768 jobs up to date | 4.875351 | 635 |
| Original Lean 4.33.1 `leanchecker --fresh Solution` | exit 0 | 1655.483232 | 644 |
| Exact Comparator `575674928e239f5bc452aab72d1dd7b0f1326494`, original config | exit 0 | 248.108519 | 667 |
| Additional retained selected-target export | exit 125, incomplete | 1830.009058 | 671 |

The original Comparator configuration is unchanged, SHA-256
`757e5537ccf47d1946521b0b5fb91a230cdcfd8933dc9ab047710709c15ffa7e`:
`Challenge` versus `Solution`, targets `MainResults.ethIsFalse` and
`MainResults.mainTheorem`, empty `definition_names`, the three standard permitted
axioms, and Nanoda enabled. Lines 657–660 report Nanoda acceptance, default Lean
kernel acceptance, and the exact final success message. The two deliberate
`sorry` warnings are in the upstream challenge placeholders; their appearance
does not authorize a solution dependency on `sorryAx`.

Fresh-checker subprocess raw SHA-256 is
`2dadef22794e8d9664207e14725a47422e29be3cf78d3fbc90925425e3ad7b62`;
Comparator subprocess raw SHA-256 is
`9e850080d6cda0383698c3d556c361b48d46085316aace8527bf5f277b185614`.
These are emitted identities, not copies of the subprocess files recovered from
the VM.

## Export failure and bounded correction candidate

The export began at 21:32:44.955 UTC with a 1800-second recorder budget. Its
receipt reports 1830.009 seconds, exit 125, and the reason
`output pipe remained open after child exit` twice. Only the 33-byte systemd
unit-start message reached its stderr log, SHA-256
`70446e13a4238f750344b185c7231fe99c5acc476e131c670db3461467076f0d`.
The failed receipt observes a partial export of 388769780 bytes, SHA-256
`0036aef63c1f8566ee1bb9e1efd0cf0d5f0ac2ff60cf613865a4e9fa7e1db97b`.
The partial file itself was ephemeral, was not kernel-checked, and is not a
complete mathematical artifact.

Recorder source lines 97–118 can first record a stage timeout/124 and then
overwrite that reason and code with live output-pump errors/125 after two
10+5-second join windows. The elapsed time aligns with that path, but the
underlying timeout flag was not preserved independently. Therefore a timeout
followed by incomplete draining is an inference from timing and code. No
exporter or theorem rejection was logged. This run confirms the added exact
`LEAN_SYSROOT` got beyond the earlier immediate child-spawn failure.

Production `ci/record.py` lines 74–77 flush and fsync once per output line,
including binary export stdout. A previously completed native export contains
10913508 newline records; it motivates an avoidable transport cost but does not
measure this Linux run's fsync count, expected final byte size, or a speed ratio.
The outside-ci, **unapplied** candidate
`verification/record_chunked_export_candidate_r1.py`, SHA-256
`fa4117719489920030dc75cc9fac658d17f6153048838123e98f6c843663928a`,
changes only non-echoed export stdout to 4 MiB reads, per-chunk fsync and an EOF
fsync. The 1000-byte diff leaves textual display, stderr separation, required
success-line tests, child argv, process policy, error and timeout branches
unchanged. Its saved 11 small transport controls cover byte preservation,
stderr, nonzero exit, timeout, injected fsync failure and textual parity. Static
review found no acceptance weakening. Linux performance and a full export still
require actual execution; no CI input has been changed by this diagnosis.

## Cache continuation actually exercised

The exact old R4 cache key and manifest were accepted, all 15718 owned payload
files validated and restored, with 1050 completed modules and 422724863 payload
bytes. The ordinary real-prefix no-build check then passed without rebuilding
the project sources. Logged original-manifest preservation and acceptance
receipts bind the old identity; old manifest bytes were not relabelled.

The finally path produced a fresh, current-harness snapshot:

- Context SHA-256:
  `b5c68d05e79b3971cbc05a95dc8aedcc4b9188cfe9912bad1b27efbd398c2f73`.
- Python fingerprint:
  `4da5f828d783536022960c83ecf631d4d883cf70e8b8bf9f8ce5cdb016ebae9f`.
- Manifest SHA-256:
  `46a5d164e4d16098cc6b3352cf4a05f552f002dea02285b571a70650441a9912`.
- Exact new key:
  `eth-owned-anthropic-9fbd29ee32ef2ea4fe15afa713145c3cfcc69aad02da8ac94dad8500bd76f92a-41911047958-1`.
- New backend ID `10025744473`, API-observed compressed size 124275878 bytes;
  staging size 425541455 bytes, payload 422724863 bytes, 1050 completed modules.

The invocation-bound readiness guard allowed maintenance and save after that
fresh snapshot. The old backend ID `10020872295` was pruned and the new cache was
saved; the post-save audit reports the new cache within the included limits.
Any future cross-harness reuse must explicitly pin this new observed identity
and current-context/producer checks. The current ledger does not automatically
authorize arbitrary successors or OpenAI reuse.

## Resource and result limits

Summed stage wall time is 4099.802754 seconds. Reaped child CPU is 235.019053
seconds and excludes systemd-managed service CPU. The fresh checker separately
reported 1651.849 CPU seconds, Comparator 253.410 CPU seconds; retained-export
service completion/CPU accounting was not reported. Small cgroup memory-peak
strings are not independent process RSS measurements. The metadata parser used
0.006745 own CPU seconds and 0.007046 wall seconds; downloads took 0.866651 and
1.000002 wall seconds. Standard public runners, no paid resources or artifact
uploads were added. Full proof exports remain ephemeral; logs and their emitted
hashes are preserved locally.

This is repeated acceptance of the specified formal targets under the named
checks, plus an actual cache-restoration result. It is not a completed Linux
pipeline verdict, a new ETH theorem, a practical SAT algorithm, or a mining
advantage. The final identity seal after the failed export was not reached.
