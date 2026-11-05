# Nanoda issue44: source applicability

Checked November5 at16:44UTC, using three primary requests and the previously saved pinned patch response. **Our exact68d5 checker does not already contain either issue44 change.** Original and worker-stack256 `tc.rs` are byte-identical, SHA `73f00401…`.

Local `tc.rs:876–882` compares whole structures for projection equality. Lines947–951 and1302–1310 use a two-valued proof-irrelevance result and continue into lazy unfolding after false. The external [3a24072 source](https://github.com/ammkrn/nanoda_lib/blob/3a2407216ee84a75f9e1aead6803d0578be06ae7/src/tc.rs) has those same mechanisms at903–910,979–982 and1337–1345. Local lines417–428 also lack the separated projection-extraction helper.

The [published patch](https://github.com/carlostoledo1891/cert-machine/blob/00340f97a03a55df68696002a11fc59b7b9d66e7/corpus/openai-math/nanoda/issue44.patch) changes projection comparison and makes proof irrelevance three-valued. Its literal context targets3a24072: that version's projection pattern includes `ty_name`, while ours differs. Conceptual relevance extends to our source; a safe port, correctness and clean application remain unestablished.

[Issue44](https://github.com/ammkrn/nanoda_lib/issues/44) reports resource blowups from these mechanisms. Those benchmarks were not reproduced here. The closed local sample's generic equality/reduction recursion cannot establish that this issue causes our ETH runtime or show proof progress. No patch was applied or recommended; no active-process/WIP-stream access, build or proof execution occurred. Actual checker acceptance remains a separate requirement.

Exact hashes, inspected line windows, primary URLs and limitations are in the companion JSON.
