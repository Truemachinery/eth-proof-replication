# Retained-export transport and timing scope

This addendum qualifies `DIAGNOSIS-R6-ANTHROPIC.md` without changing its saved
bytes or the actual r6 result.

The output pump's per-line fsync is a plausible avoidable cost, supported by
the source and by the large newline count in a separate native export. The
Linux run did not isolate fsync throughput or prove that this was its only
bottleneck. The unapplied chunked candidate changes export transport only. It
does not repair the original recorder's timeout-reason overwrite or service
lifecycle/pipe cleanup.

The recorder kills the `systemd-run` CLI process group. Its independently
managed service has `RuntimeMaxSec=7195`; killing the CLI is not equivalent to
stopping that service. The saved failure log lacks export-service completion
accounting, and the candidate leaves this boundary unchanged. The logged partial
export identity is a failed receipt observation, not a checked complete export
or an independently recovered VM file. These limitations do not weaken the
recorded fresh/Comparator/Nanoda acceptance that preceded the failure.

The board/checkpoint shorthand completion time 22:03:28 refers to the final
displayed cleanup log time. The compact API terminal-state observation occurred
at 22:03:45.642 UTC. The connector did not expose a job `completed_at` field;
no more precise API completion timestamp is claimed here.

This is source and saved-log review only, following a same-team independent
reviewer's observation. No production code was changed or executed, no Linux
speed ratio was measured, and no new job was dispatched.
