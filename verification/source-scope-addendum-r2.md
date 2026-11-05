# OpenAI encoding-bound source addendum — 2026-11-05

This is a source-reading clarification to the November4 statement review, not a new proof or checker invocation. The configured replication target remains `OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat`.

At pinned commit `4eaee87548250b2682affda7d05d947c05554bae`, `SqrtLogSpace/EncodingBounds.lean` formalizes `encoding_le_declaredSize_sq`: for width-at-most-k CNF F on n variables, with m=F.card and L=Encoding.formulaBitLength F,

`L + 1 <= (8*k + 7) * (n + m + 1)^2`.

`encoding_pow_le_declaredSize` transports its powers into the runtime and space estimates. `SqrtLogSpace/Statement.lean` then proves `runtimeBound_le_eth` for n>=20 and nonnegative C,A, bounding the runtime by

`C * (8*k+7)^d * (n+m+1)^(2*d) * 2^((4*A)*rho(n))`,

where `rho(n) = n * (log2(log2(n)))^2 / sqrt(log2(n))` is defined in `SqrtLogSpace/Asymptotics.lean`. `SqrtLogSpace/Final.lean:104` states the additional `exact_count_eth` theorem and uses those lemmas to express exact counting/SAT and polynomial visited space in declared n+m size. This still has the squared log-log factor; it does not establish the sharper single-log-log manuscript bound.

The original statement review's manual encoding calculation was explicitly outside that review's formal scope. It should not be read as a claim that no formal encoded-length inequality exists in the source. The named auxiliary theorem is not our configured Comparator target, and this addendum does not supply a separate transitive axiom audit or expanded target verdict for it. Formal inequalities inside the canonical representation also do not certify every informal/textbook input translation, computational-model simulation, implementable constant or finite-size crossover.

Read ranges: Final.lean1–201 (full file), EncodingBounds.lean1–109 (full file), Statement.lean1–33 (full file), Asymptotics.lean1–105 (partial). The companion manifest binds actual source bytes and records the exact ranges and file lengths. Original inputs were read only; no source, proof environment, running checker or public package was changed.

Use this clarification with [STATEMENT_REVIEW.md](../STATEMENT_REVIEW.md), [the current replication index](../README.md) and [SHA256d requirements](../SHA256D_RELEVANCE.md).
