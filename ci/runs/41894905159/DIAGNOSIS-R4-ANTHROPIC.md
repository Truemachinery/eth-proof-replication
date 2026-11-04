# Linux Anthropic checks accepted; additional export failed

Run [41894905159](https://github.com/Truemachinery/eth-proof-replication/actions/runs/41894905159), Anthropic job `126801716984`, used public commit `d9a4ad18e3668320bf9d084c7e454ff05e34f2e8`. Its final job conclusion is **failure**. The first failing harness stage was number 40, `retained-target-export`; all 39 earlier stages exited zero.

The completed required checks precede that failure:

| Stage | Exit | Wall seconds | Raw stage SHA-256 |
|---|---:|---:|---|
| Original source/default build | 0 | 1506.188021 | `c99704b2bb42e0a64509eb0c1bb5c1b823f6412129621c624e77b9aefcafd961` |
| Normal real-prefix trace check | 0 | 15.661242 | `b0c1e25797acc6c6d6270e45fc1a944eb15cc202aa0a0e401978fcb7eee2ccfa` |
| Original Lean 4.33.1 `leanchecker --fresh Solution` | 0 | 1701.586100 | `0e94ea5075bee643fce711bf3e9847875107bb7a9d6f044dd67b0792ef1667b0` |
| Original Comparator 575 config, including Nanoda | 0 | 272.250102 | `9adacc0cf08acb3b8ffd484627a748c6f09144000d646cf58058b7dbb9f2d35c` |
| Additional retained target export | 1 | 0.968310 | `4de5d52f1bdc17e322106755a16195acc81b2fc67dcbaf3b2ec929809efb32f6` |

Comparator printed both kernel acceptance messages and its required success line. The original config SHA is `757e5537ccf47d1946521b0b5fb91a230cdcfd8933dc9ab047710709c15ffa7e`: targets `MainResults.ethIsFalse` and `MainResults.mainTheorem`, no definition holes, only `propext`, `Quot.sound`, `Classical.choice`, and Nanoda enabled. The early ABI, actual filesystem write-denial, and socket(AF_UNIX) creation-denial controls passed. ABI 8 retains the narrower coverage documented in r4; this is not full ABI 9 or complete UNIX-socket isolation.

The additional export failed before producing any export bytes:

```text
uncaught exception: process 'lean' exited with code 255
could not execute external process 'lean'
```

This is an environment/execute-policy failure in our additional provenance stage, not a rejected theorem. The final post-check source-identity comparisons were not reached, and the harness correctly retained status `incomplete`. No later proof stage ran. This report does not relabel the overall job as passed.

Both pinned exporters call `findSysroot` at [Main.lean:5](https://github.com/leanprover/lean4export/blob/15f6055e299ad5b89345e533cc2192f4cc00f659/Main.lean#L5). [Lean 4.33.1 Path.lean:180–187](https://github.com/leanprover/lean4/blob/v4.33.1/src/Lean/Util/Path.lean#L180-L187), identical here in 4.34.1, first reads `LEAN_SYSROOT`, otherwise starts `lean --print-prefix`. Our retained-export Landrun call omitted that environment variable and granted no execution of the child Lean. The successful original [Comparator safeExport](https://github.com/leanprover/comparator/blob/575674928e239f5bc452aab72d1dd7b0f1326494/Main.lean#L134-L150) grants execution of the proof toolchain prefix instead.

The root-authorized minimal correction adds only `--env LEAN_SYSROOT` to our retained-export call. Its value comes from the existing exact real proof prefix, separately from the gated source-build prefix. No execute or write permission is added; upstream sources, tools, checker configuration, axioms and targets are unchanged. Corrected driver SHA is `d3d38d581b583891fad340a377ff799dab8d396a26a947b2fffe04d74cd7b77c`. Two-version trusted-Init controls and exact input hashes are recorded outside `ci/` in `verification/export-sysroot-control-result-r1.json`, SHA `78294fd4de5afe05d40c4a10af897eb094945d245c90437d7cb4724b359556de`. They do not execute ETH checks or Linux Landrun.

The exact GitHub completed-job response is UTF-8 BOM text, not a ZIP: `anthropic-job-126801716984.raw.log`, 241386 bytes, SHA `96b5a97a88747174e013598c24e73eba3c2f1e2943e112f5f80ade7a44cf0574`. `anthropic-job-download-r1.json` records retrieval; `anthropic-job-summary-r1.json` contains the 40 trusted stage receipts, original config, runtime identities and one run receipt. The full workflow-ZIP endpoint returned HTTP 404 while OpenAI remained active; that failed retrieval is preserved separately. No ZIP or member inventory is claimed yet.

The owned-output snapshot records 1050 completed modules, payload 422724863 bytes, staging total 425541455 bytes, manifest SHA `f03170368e5705c17d4354d5bf685822e4d4ffeb9c42f6b046413c5cd95e3ecb`. Cache backend ID `10020872295` reports 124278111 bytes under exact key:

```text
eth-owned-anthropic-dd4d7b438fa94c8ca1a9ea561fb4028a8e17cbce3be307a03ce84651ea925bf0-41894905159-1
```

Old Python fingerprint: `9c0011429218dd9eb6addf639baad7c55358ef35c15cc96c783dca1ba61af4c0`; source/config/runtime context SHA: `b5c68d05e79b3971cbc05a95dc8aedcc4b9188cfe9912bad1b27efbd398c2f73`. Runtime public `ci/` has **23** harness rows; the workflow template is mapped to `.github/` and is not one of those rows. The Actions hash in the cache key is a separate identity. No compatibility bypass or cache rewrite is implemented by this correction.

The 40 stage wall intervals sum to 3798.776071 seconds. Their reaped-child CPU sum, 230.229452 seconds, explicitly excludes systemd-managed service CPU. Raw systemd counters separately report source-build CPU 3781.610 seconds, fresh-checker CPU 1681.496 seconds and Comparator CPU 277.396 seconds. Reported cgroup memory fields are not independent process-RSS measurements. Retrieval, diagnosis and the 2.782466 CPU / 4.943681 wall second Init control do not replace these original costs. No paid resource or workflow dispatch was added by this review.
