# Anthropic-only continuation candidate

This revision supersedes the earlier plan to wait for OpenAI before publishing cache compatibility. It permits only the already observed Anthropic predecessor from run 41894905159. OpenAI has no predecessor entry and remains a separate active run.

The final workflow uses fixed, distinct per-proof job concurrency groups and disables cancellation. During the transition from the old global workflow group, the operator starts only Anthropic while the old OpenAI job remains active; no new OpenAI job starts before that old job ends. This keeps at most two active standard jobs.

The finalized-snapshot availability guards are unchanged from r2. The current CI README and reviewed workflow hash are bound by the static ledger; the original 23 producer rows and exact predecessor metadata remain unchanged. Final affected YAML/ledger control r3 passes 29 checks: the 28 receipt/outcome fixtures plus fixed distinct job groups, no global group and no cancellation. Wrapper cost: 1.700219 CPU / 2.000932 wall seconds, exit zero. Result SHA: `924d90ef084aaff69b752d8e6f6ee41aa282d42e5f4bf62c8458a9d67fc651b2`. No actual GitHub cache operation or proof run occurs in this control.

The 19 earlier ancestor controls and two-version Init controls remain historical evidence. The first ancestor control expects the frozen public producer CI bundle from commit `d9a4ad18e3668320bf9d084c7e454ff05e34f2e8` at its recorded preparation-layout path. Its source inputs are public; this layout dependency is not part of the portable Linux proof harness. The r3 YAML/ledger controls use the current public CI bundle directly. All exclusive output names require a fresh checkout or explicit distinct copies for another control run.

Real Linux restoration, source trace validation, checks, extra export and the final identity seal remain unmeasured until the root-reviewed continuation executes. A passing control is not a continuation verdict. Publication and workflow dispatch remain with the parent coordinator.
