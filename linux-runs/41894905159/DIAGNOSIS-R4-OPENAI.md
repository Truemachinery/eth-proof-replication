# OpenAI Linux source build: memory limit, no target verdict

OpenAI job `126801717400` in workflow `41894905159` completed with a failure.
The source-build service was OOM-killed at the configured 14G memory limit.
No fresh whole-closure checker, Comparator, selected-target export or independent
kernel check was reached. No Lean theorem error was observed in the saved log.
This is an incomplete replication with a resource failure, not a refutation or
acceptance of the named formal target.

The public producer is revision
`d9a4ad18e3668320bf9d084c7e454ff05e34f2e8`, manually dispatched in `all` mode.
The exact OpenAI source, Lean 4.34.1, Mathlib, Comparator, exporter and Nanoda pins
are present in `RUN_START` and the derived summary. The proof source was not
edited. The two-frontend gate, two Lean runtime threads and systemd 14G service
limit are visible in the recorded source-build argv.

## Preserved response and archive

- `openai-job-126801717400.raw.log`: exact completed GitHub job-endpoint body,
  513886 bytes, SHA-256
  `c5b6d74be5996d77cd7cb7e421d88dde529793f4d9849772f99bdd69f5ae4bac`.
  The body has a UTF-8 BOM and 3666 decoded lines. It is distinct from the
  subprocess raw files whose hashes are emitted inside its receipts.
- `workflow-41894905159.logs.zip`: exact completed workflow-endpoint body,
  246432 bytes, SHA-256
  `0a18fdb544c960346bdc235b6e29a116d322fb5a77ab74351a53526c445c2194`.
  Its 13 available relative members were exclusively extracted and hashed in
  `workflow-log-members-r1.json`; the archive includes both aggregate job logs.
  The earlier active-run ZIP attempt remains preserved separately with its
  HTTP 404 result. Available archive members are not additional experiment runs.
- `openai-job-summary-r1.json`: derived receipt and successful-module list,
  448505 bytes, SHA-256
  `2647a7c4e8a4626ebb8c9cc9756699b64a66835f9911938caca166d8e1afbf2f`.
  Parser `parse_completed_log_r1.py`, SHA-256
  `e25554e5f4a88445085f62bc48953e0ea7647957cafd44a02e75149017fa8816`,
  verifies all 38 start/finish pairs and the run aggregate without proof-tool
  execution. It accepts timestamped, unprefixed harness JSON objects only.

## Actual failure boundary

The first 37 stages exited zero. `source-build`, the 38th stage, exited one
after 10166.260507 wall seconds, below its 18580.769665-second recorder budget.
Its subprocess raw log is reported as 276678 bytes, SHA-256
`caffbce51fe44960a0d0222d6b8ffb511ecc2572f46e0432ee7e6d70ef44e2ce`.
That file was ephemeral; the GitHub response is the recovered evidence.

The exact response lines 3619–3624 state:

```
Finished with result: oom-kill
Main processes terminated with: code=killed/status=TERM
Service runtime: 2h 49min 26.195s
CPU time consumed: 6h 24min 57.178s
Memory peak: 14.0G
Memory swap peak: 2.6G
```

The successful displayed build events contain 2880 distinct owned modules:
2879 `OAI.*` modules and one `ComparatorChallenges.*` module. There are no
duplicate successful owned-module events. This agrees with the finally snapshot
count. The last completed module is
`OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.HighQueryReturnReplay`; the log
does not identify which in-flight compiler caused the peak. The last Lake
progress number, `11803/12015`, counts Lake jobs and must not be substituted for
a compiled-module count. The lexical copied-source inventory is a separate
3091 OAI modules plus one challenge module.

## No OpenAI continuation cache was saved

The finally snapshot observed 3718194367 payload bytes for those 2880 completed
modules. That exceeds the current 2147483648-byte per-proof payload cap, so it
reported `skipped-empty-or-oversize`. Cache save and post-save audit steps were
skipped. There is **no saved OpenAI cache key, backend ID or manifest digest**
from this run, and no payload available for an ancestor-cache continuation.

The observed source/configuration/runtime context digest is
`aa5fab3860eddccf2a16596c69e2b3b6d8ff7ea107b01ede0231132cc10f4bcf`;
the current Python harness fingerprint is
`e0bea202958d514063c5d020c64b2b5ad5489deff43306d3d805069e71baae04`.
These identify the skipped snapshot request, not an extant cache. Adding an
OpenAI legacy-cache ledger entry for this run would be unsupported.

## Resource scope and next decision

Summed stage wall time is 10469.154574 seconds. Reaped-child CPU is 364.653555
seconds and excludes the separately reported source service CPU of 23097.178
seconds. The logged cgroup memory limit/result is actual resource evidence;
individual compiler peak and the effect of reducing frontend concurrency were
not measured here. The parser used 0.012012 own CPU and 0.012362 wall seconds.
Job and archive downloads took 1.131055 and 1.050835 wall seconds. No paid
runner, artifact upload or new cloud service was used.

The existing native OpenAI build is a separate ongoing attempt and was not
changed. A Linux retry would need a reviewed memory/continuation plan: reducing
concurrency is a candidate, not a guarantee that a single compiler fits the
limit, and the observed oversized payload cannot be treated as a saved cache.
No retry, cancellation, CI edit or resource expansion was performed by this
diagnosis. All formal OpenAI target-check outcomes remain pending.
