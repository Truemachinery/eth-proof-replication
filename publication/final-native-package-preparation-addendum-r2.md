# Final-plan omission guard

This supersedes only the mutable-publisher identity in the R1 preparation note. The final proposed publisher SHA-256 is `393e66e4bc31bb8115c371177a04024ca4d46728ce039b8adda1f32e50ef3bb1`.

A review of the plan boundary found that a hand-edited plan could remove supporting public files while the final gate still validated their closed local originals. Export now requires every selected final native small artifact, all eight native result entries in the receipt list, and every closed native phase bundle. It refuses omissions before creating the destination. This strengthens package completeness; it does not change a proof or checker policy.

R3 adds seven tiny synthetic controls: a complete final fixture still exports, while omission of the map, final seal, phase inputs, raw stream, phase result or receipt-list entry is refused. R3 reported 0.173523 CPU seconds/0.176373 wall seconds. Its source/result are new files; R1 and R2 controls and their earlier publisher hashes remain preserved. Together the three synthetic reports contain 39 checks. Their passing test bodies reported 0.866303 CPU seconds/0.941662 wall seconds; startup, model and bookkeeping overhead are not included.

A separate read/hash/schema compatibility check of only the three already closed real R2 phases passed under the earlier functionally identical phase guard. It read no running Comparator stream and executed no proof tool. Its record is `final-native-existing-schema-check-r1.json`; it reported 0.002207 CPU seconds/0.003461 wall seconds and is not another theorem verification.

The R2 proposal diff compares explicitly redacted source views of the preserved R7 source and this candidate. It records original source hashes separately and does not misidentify the public R7 AST-portable derivative as byte-identical original code. No real R8 plan/export has been produced. Actual all-eight closure, final aggregate acceptance, final reports/reviews, availability checks and root approval remain required before publication.
