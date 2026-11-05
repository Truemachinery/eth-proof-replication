# Saved OpenAI Linux failure review

Independent same-team review of workflow `41894905159`, OpenAI job `126801717400`. All announced raw, summary, diagnosis and ZIP identities match; all saved-evidence assertions passed. No proof execution, retry, download or CI edit was performed.

There are 38 matched stage starts/results: 37 exit zero, then `source-build` exits 1 at raw line 3625. Systemd lines 3619–3624 explicitly report `oom-kill`, memory peak 14.0G and swap 2.6G. The command records a 14G limit, two compiler slots and two Lean threads. Recorder duration 10166.260507 s is below its 18580.769665 s budget, with no timeout reason. No displayed Lean/compiler error was found in the source-stage scan. This establishes a resource failure for this attempt; it does not identify the peak compiler or guarantee a different concurrency fits.

The response contains 2880 distinct displayed successful owned Built events: 2879 OAI modules and one challenge. Their exact names/line numbers reproduce the summary and snapshot count. Last event: `OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.HighQueryReturnReplay`, line 3618. The recorded 3092 lexical source files and Lake job progress are different counts. No full target closure is established. No normal real-prefix trace, original fresh checker, Comparator, selected export or extra Nanoda stage started.

Snapshot line 3626 records 3718194367 bytes, above the 2147483648 cap, and `skipped-empty-or-oversize`. Restore missed at line 444 and line 3647 explicitly skips save. No ready manifest/backend identity was emitted and no save/audit job member exists. Thus no OpenAI continuation cache from this run is supported. Attempted lookup-key strings are not saved cache identities. No global cache API query was performed; an OpenAI ancestor-ledger entry based on this run would be unsupported.

Summed stage wall is 10469.154574 s and reaped-child CPU 364.653555 s. Separately reported systemd service CPU is 23097.178 s; it is excluded from Recorder child CPU. These scopes remain separate. No individual compiler memory measurement or performance comparison follows.

The BOM-prefixed endpoint response has 3666 decoded lines and SHA c5b6d74b…. All 13 ZIP members match the saved member manifest and extracted bytes. ZIP `0_openai.txt` is byte-identical to the job response: duplicate packaging, not another run. The ephemeral subprocess raw hash caffbce5… is reported inside that response and was not independently rehashed as a recovered file. The derived summary is intentionally object-only; this review separately parsed array runtime/tool markers.

The supplied diagnosis is consistent with the recovered evidence; no material correction requested. Overall replication and all OpenAI target-check outcomes remain incomplete. The companion JSON preserves exact hashes, assertions, source-line references, full metadata reproduction program and measured review resources. An initial report-writer delimiter SyntaxError before execution is separately preserved, then corrected; it changed no input artifact.

