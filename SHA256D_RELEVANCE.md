# How other agents should use this replication in SHA256d research

This reference concerns the external asymptotic SAT/#SAT constructions. It supplies no measured improvement for Bitcoin's full SHA256d search. Consult the per-proof reports for the actual verification stage reached; a successful build alone is not the complete verdict.

## What can transfer

The papers provide algebraic counting and tensor-contraction ideas worth studying at their actual proof steps. Existing project modules test small exact identities, measurement designs, interpolation and fiber indexing. Their correctness, design cost, rank, attainable measurement values, coefficient bit lengths, reconstruction requirements and memory use must be measured separately.

For a concrete candidate algorithm, document the exact theorem or lemma used, its assumptions and all transformations into the hash circuit. Keep a bridge from the theorem's input size and machine model to the implemented circuit and runtime.

## Conditions for a valid SHA256d application

1. **Count the correct variables.** In a generic CNF reduction, the theorem's variable count includes the auxiliary circuit variables. It cannot be replaced by the 32 nonce bits without a separate justified reduction or structural algorithm.
2. **Preserve multiplicities.** A SAT-equivalent encoding need not be count-preserving. Check that each allowed header assignment has exactly one auxiliary completion, or account for the known number of completions.
3. **Recover a witness.** Exact counting is not itself a nonce. Conditional-count witness extraction requires additional calls and costs, followed by independent full `hashlib` verification.
4. **Preserve the real problem.** Reduced rounds, unconstrained message words, alternate padding/IV, fixed internal states and artificial targets are different search domains. Validate a proposed filter against a trusted full SHA256d implementation and real valid header vectors before treating it as safe pruning.
5. **Charge complete costs.** Include source-to-CNF conversion, measurement/basis construction, arithmetic bit complexity, interpolation, memory, repeated templates, witness extraction and verification. Compare against the strongest matching native midstate baseline.
6. **Respect asymptotic scope.** ETH being false does not establish P=NP, polynomial-time SAT or a useful finite-size crossover. Fixed-size experiments establish neither an asymptotic algorithm nor a general SHA256 lower bound.

## Existing project cautions

- `../eth-simultaneous-notes-20261029.md`: fixed-layout shared rank can exceed pointwise rank. Sparse evaluations do not suffice unless they determine the required count.
- `../eth-fiber-index-independent-review-20261029.md`: exact indexing reduces rejected membership work while preserving matching terms; the saved tiny timings show no speedup.
- `../entropy-rank-control-20261029.md` and `../rank-provenance-audit-20261029.md`: specify the actual boundary relation and elimination semantics before interpreting measured rank. A low-rank representation built by exhaustive enumeration is not automatically cheaper search.
- `../lean-audit-notes-claude-20261102.md` and `../lean-faithfulness-notes-claude-20261102.md`: proof-wrapper acceptance, kernel checking, model fidelity and implementation validation are separate layers.

Start future experiments with a bounded hypothesis, a smallest falsifier, exact provenance and fresh baseline controls. Record negative findings. This replication is a foundation for reading the external proofs accurately, not authorization for cloud spending, public disclosure of private project data or live mining actions.
