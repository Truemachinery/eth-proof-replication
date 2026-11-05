# R7 staged repair handoff

**Prepared only; not applied, published or dispatched.** The exclusive public
layout is `verification/ci-repair-candidate-r7/`, containing 24 fixed `ci/`
files and `.github/workflows/replicate.yml`. All 25 selected live revision 6
inputs still match their original hashes. The native OpenAI attempt remains the
priority; this preparation includes no cold OpenAI Linux retry or proof-tool
execution.

`ci-repair-candidate-r7-inputs-r1.json`, SHA-256
`68e3cfd1b03d66e45bcfe21a93ad212d2342a67de2061e67547d2cfbe8ca6713`,
binds every staged public path and its original hash. Nine files changed; sixteen
remain byte-identical. The source/runtime/tool pins, compiler gate C source,
proof sources, original target/axiom configurations, real Landrun permissions,
14G service limit and per-proof non-cancelling workflow concurrency are preserved.

## Concrete changes

1. Binary export stdout uses the reviewed 4 MiB pump with per-chunk and EOF
   fsync. Textual output, stderr separation, raw-byte hashes and exact success
   sentinel checks retain their previous behavior. Finished receipts include
   `timed_out`, which records expiry of the recorder's own wait. A subsequent
   pipe-drain failure can still return 125 but retains the deadline flag and
   combines the timeout and drain reasons.
2. The retained export explicitly passes 1800 seconds to both the isolated
   service builder and recorder. Under the existing builder this requests at
   most 1795 seconds of service runtime plus a five-second stop allowance,
   subject to the overall harness deadline. There is no global service kill.
   A service may time out before the recorder wait and then have
   `timed_out=false`; the systemd result remains separate raw evidence.
3. OpenAI source compilation admits one frontend; Anthropic admits two. Both
   retain two Lean runtime threads and `MemoryMax=14G`. This reduces permitted
   combined compiler concurrency; single-compiler memory fit remains unmeasured.
4. Owned-output snapshot, restore, staging and backend bounds use explicit
   per-proof limits: OpenAI 6 GiB, Anthropic 2 GiB, at most 8 GiB retained total.
   The 32 MiB staging reserve remains. Backend API audit enforces each entry's
   own proof-specific limit. This stays below the previously verified included
   repository allowance without a purchased increase or Actions artifact uploads.
   Ownership, path, file size/hash, no-overwrite and ready-snapshot guards remain.
   Two existing control sources have only their old single-limit API call sites
   updated; their historical result files and original frozen sources remain.
5. Exactly one predecessor is supported: the observed revision 6 Anthropic
   cache. The pruned revision 4 entry is replaced. The old fingerprint is
   recomputed from the actual 24 producer rows, including the old ledger, and
   the current exact source/configuration/runtime context. Approval of the new
   producer uses exactly 23 nonledger rows plus the workflow hash, avoiding a
   circular ledger hash. The ordinary current fingerprint still binds the new
   ledger. Exact matched key, original manifest SHA, payload guards and
   original-manifest preservation remain mandatory. There is no OpenAI entry:
   its oversized snapshot was never saved.

Current ledger SHA-256:
`247130dc03d737b2ab46ec0898cb5d3438b3faa8b2618dc9b04495ccef5cdd40`.
Workflow SHA-256:
`33c8581f513743184a8c198778e015613e39533a24f7047ac340506a746a0412`.

## Only authorized predecessor

Producer commit `309670f70aa79d85752dbdc61799ad8cc56772c2`, run
`41911047958`, job `126858374463`, backend ID `10025744473`, observed compressed
size 124275878 bytes. Exact key:

```
eth-owned-anthropic-9fbd29ee32ef2ea4fe15afa713145c3cfcc69aad02da8ac94dad8500bd76f92a-41911047958-1
```

- Manifest:
  `46a5d164e4d16098cc6b3352cf4a05f552f002dea02285b571a70650441a9912`.
- Old Python fingerprint:
  `4da5f828d783536022960c83ecf631d4d883cf70e8b8bf9f8ce5cdb016ebae9f`.
- Exact source/configuration/runtime context:
  `b5c68d05e79b3971cbc05a95dc8aedcc4b9188cfe9912bad1b27efbd398c2f73`.

These identities come from preserved completed-run receipts. The new controls
do not download or independently validate actual backend cache bytes.

## Validation and resources

The separately versioned local controls cover 97 successful checks:

| Evidence | Checks | Scope |
| --- | ---: | --- |
| `record-r7-control-result-r1.json` | 12 | Exact binary/text/stderr bytes, exit/timeout/fsync failure, combined timeout/drain reasons; harmless fixtures and mocks |
| `cache-policy-r7-control-result-r1.json` | 27 | Per-proof and total boundaries, ownership/hash/no-overwrite and mocked backend policy; no multi-GiB allocation |
| `r7-driver-resource-control-result-r1.json` | 7 | Actual driver AST and service-command builder, source environments, matching export budgets, exact workflow labels/key |
| `cache-policy-control-result-r7-r1.json` | 29 | Actual YAML receipt/outcome guards, preserved predecessor on early failure, valid partial snapshots, concurrency and current ledger binding |
| `ancestor-cache-control-result-r7-r1.json` | 22 | Actual producer receipt binding and synthetic exact-predecessor acceptance/rejections, including old-ledger omission/current-ledger inclusion |

The controlled commands consumed **8.198256 CPU seconds / 13.347787 summed wall
seconds**, including the preserved initial Python 3.9 `tomllib` import failure.
That unchanged control source passed under installed Python 3.13; the Linux
workflow uses a Python version supporting `tomllib`. Source preparation,
metadata/checkpoint bookkeeping, model time and read-only review are outside
those command totals. The authorization was 30 CPU / 180 command wall seconds;
no paid compute, network acquisition, Lean/proof execution or multi-GiB fixture
was used. Historical failed tests and terminal run evidence were not overwritten.

The initial staging copy selection included nested evidence paths and rejected
its count before copying; it was corrected to the exact 25 top-level selected
inputs. The empty new staging directory was verified before copying. A
checkpoint attempt to attach the hidden `.github` path was rejected by the
existing local allowlist before saving; the frozen input map binds those bytes
instead, with no allowlist modification.

The chunked transport and resource changes address observed harness limitations.
They do not establish a Linux speed ratio, prove that the next job fits memory
or cache limits, supply a new mathematical result, or close either earlier
incomplete Linux run. Root must review this concrete candidate before any apply,
publication or optional Anthropic-only production continuation. No new OpenAI
run is part of this handoff.
