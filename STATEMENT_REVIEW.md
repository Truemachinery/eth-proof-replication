# Statement scope review for the external ETH replication

Prepared 2026-11-04 by `codex-eth-submission`, with Codex assistance. **Source-level review only; all build/checker verdicts are pending.** This is a targeted review of the formal contracts and headline paper claims, not an independent reconstruction of either full mathematical proof.

## OpenAI family 378

Run pin reviewed through the official raw-source endpoints: `4eaee87548250b2682affda7d05d947c05554bae`; toolchain `leanprover/lean4:v4.34.1`. The scope document, challenge and comparator configuration were inspected at this pin. The parent's source manifest must bind the local run to these files.

An explicit local `git diff --exit-code` from the previously reported `7ef5c0cc5ca4b0e072b7a050fca09ab24bc6fa3a` to this pin returned zero for the ETH proof subtree, challenge, comparator configuration, scope document and October 25 manuscript subtree. The challenge SHA-256 is `4183b2057cff350d66848215ff7167196dfc20e1891b598fdddea59077a76685`; configuration `debbfdc9c01104d2369be80da5180978275106df8b685f693fba7ce7da7c5b19`; scope document `a2f7b390d6308997350b903be02c40a1227ebd2b9376982da528574500531f79`. This is file comparison, not proof acceptance.

The [formalization scope](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/lean/docs/378.md) distinguishes two bounds. For fixed `k >= 2`, its Lean claim is exact counting on canonical inputs of bit length `L` in

`(L+1)^O_k(1) * 2^O_k(n (log log n)^2 / sqrt(log n))`,

with polynomially many visited tape cells. The [October 25 manuscript, Theorem 1.1 and following explanation](https://github.com/openai/math/blob/7ef5c0cc5ca4b0e072b7a050fca09ab24bc6fa3a/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/main_full_version.tex#L70) states the sharper single-log-log exponent, plus a fixed-density improvement without that factor. Checking the listed Lean target does not by itself verify those sharper statements.

The [challenge](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/lean/ComparatorChallenges/SubexponentialSAT.lean) names `OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat`. For each fixed `k`, one deterministic finite-state multitape machine and positive constants are chosen before all formulas. It handles width-at-most-`k` finite-set CNFs over `Fin n`; the output tapes contain the exact count and SAT bit, with a halting trace and a polynomial visited-space bound at every prefix. Its runtime scale uses natural logs and `n+16`. It provides no numeric values for its existential constants.

**Manual encoding check, not a new Lean lemma:** let `r` be total literal occurrences. Literal codes are at most `2n-1` and unary. Each list-frame doubles a payload and adds a delimiter. Expanding the two list layers gives `L = n+2+4m+sum_literals(4*code+8) <= n+2+4m+(8n+4)r`. Thus `r<=km` gives polynomial length for fixed width. Finite-set formulas also have polynomially many possible fixed-width clauses. Unary indices therefore do not alone create an exponential encoding gap; a formal length/simulation bridge remains outside this review.

The [comparator configuration](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/lean/ComparatorChallenges/SubexponentialSAT.json) selects that theorem and permits only `propext`, `Quot.sound`, and `Classical.choice`. It disables nanoda by default. A default successful comparator run consequently must not be described as acceptance by two kernels; an additional explicitly configured run would be needed.

## Anthropic ETH development

Run pin inspected locally: `16a5ce41304fcdaea4e0be7c132e1c361dc26da5`; toolchain `leanprover/lean4:v4.33.1`. [MainResults.lean](https://github.com/anthropics/formal-math/blob/16a5ce41304fcdaea4e0be7c132e1c361dc26da5/eth/MainResults.lean) defines the semantic contract; [Challenge.lean](https://github.com/anthropics/formal-math/blob/16a5ce41304fcdaea4e0be7c132e1c361dc26da5/eth/Challenge.lean) names `MainResults.ethIsFalse` and `MainResults.mainTheorem`.

`MainTheorem` quantifies one deterministic Mathlib finite-alphabet multi-stack machine and an absolute constant before `k` and the formula. For `k>=1`, `n>=4`, `m>=2`, no repeated written clauses, and every declared variable occurring, it counts assignments within

`floor(2^(C * min(k*m/sqrt(log2 m), k^2*n*log2(log2 n)/sqrt(log2 n))))`

machine steps. Its input is unary `k,n` followed by `k` binary slots per clause; the count is emitted in `n+1` bits. Clause lists may contain repeated literals, tautologies, or an empty clause. `ETHIsFalse` negates positivity of the infimum exponential rate for 3-SAT; its machines may depend on the rate. This formal contract asserts no polynomial-space bound.

The [paper](https://github.com/anthropics/formal-math/blob/16a5ce41304fcdaea4e0be7c132e1c361dc26da5/eth/paper.pdf), pages 1-2 and Appendix E (pages 40-43), matches the headline exponent and explicitly distinguishes its word-RAM presentation from Lean's machine steps, canonical encoding, explicit parameter ranges and named existential constant. The [PaperIndex](https://github.com/anthropics/formal-math/blob/16a5ce41304fcdaea4e0be7c132e1c361dc26da5/eth/proof/PaperIndex.lean#L244) documents this correspondence. The model simulation and input rewriting are discussed in prose, not kernel-certified by these two target declarations. Our targeted reading found this disclosed boundary; it is not a completed formal bridge or a full paper-proof comparison.

The [README](https://github.com/anthropics/formal-math/blob/16a5ce41304fcdaea4e0be7c132e1c361dc26da5/eth/README.md) separates build/axiom inspection from a Linux comparator check. Its [configuration](https://github.com/anthropics/formal-math/blob/16a5ce41304fcdaea4e0be7c132e1c361dc26da5/eth/comparator.json) requests both targets, the same three permitted standard axioms, and nanoda. Challenge-template placeholder warnings must be distinguished from an accepted solution's actual axiom dependencies; a successful source build alone settles neither question.

## Meaning of an eventual replication result

| Check | Evidence it can supply | Additional question it does not settle |
| --- | --- | --- |
| Fresh target-source build | Our environment elaborates/compiles the pinned proof | Exact match to the intended trusted statement |
| Named theorem axiom inspection | Recorded dependency axioms of those declarations | Whether all target modules were actually checked |
| Comparator | Solution matches the configured challenge and passes the reported kernels/axiom policy | Whether the challenge expresses the intended informal theorem |
| Independent kernel or closure replay | Acceptance by the named implementation with stated closure coverage | A new mathematical proof, semantic interpretation, or practical runtime |
| Human statement review | Explicit reading of machines, quantifiers, encoding, bounds and scope | Automated certification of the full informal correspondence |

Standard axioms must be reported by name. Do not equate a different agent label with independent human review. Independent execution of a published proof can improve reproducibility evidence without being an independent derivation.

Neither asymptotic bound implies `P=NP`, a practical `#SAT` implementation, or faster full Bitcoin SHA-256d search. Our existing experiments implement finite primitives and ordinary solver/encoding paths; they are separate evidence. Applying a counter to a hash CNF requires all gate variables in the size measure, count-preserving encoding, witness extraction, preprocessing, validation and a matched hashing baseline. No such practical advantage follows from accepting either formal theorem.

## Pending completion record

- Bind the selected source pins and reviewed statements/configurations to the final run manifest.
- Insert actual per-stage verdicts and artifact links from the parent replication task.
- Disclose which upstream caches and binaries were reused, which proof modules were rebuilt, and which kernels/closure checks actually ran.
- Retain unsuccessful attempts and unavailable-platform checks. Do not turn an upstream README's reported result into our measured result.

Review operations: primary-source web reads, local source inspection and hashes/diffs, and read-only PDF text extraction using the Codex PDF skill and bundled `pypdf` (pages 1-2 and 40-43 inspected for the stated paper comparison). No theorem build or comparator execution was performed by this reviewer. Resource use was light local reading/extraction, no paid compute; exact review CPU/energy was not metered.
