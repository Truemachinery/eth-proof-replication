# Native recorder decoupling

Prepared a new `verify_native_phase_r2.py`; R1 remains byte-identical and unexecuted. R2 changes exactly two literal source paths: the Recorder pin key and import path now use `native-recorder-r1/record.py`. That file is an exclusive byte-for-byte copy of frozen public R6 Recorder SHA `1a7c9f9d8bbf7de0458e83ea0385a280c05db970b2e87493f3e85a6c06c361c0`. It prevents later changes to live CI Recorder behavior from changing native verification.

No phase behavior changed. The inverse path substitution exactly reconstructs R1, and AST syntax checks passed for R1, R2 and the copied Recorder. No import, test or proof/launcher phase execution was performed. CI, workspace and running source builder were not edited. Existing capture controls and peer review retain their historical version scope. The companion JSON binds original peer review `578329ba…`, full old/new/copy hashes and exact diff.

`native-phase-runbook-r2.md` provides the same eight explicit commands with the R2 launcher and new r2 record folders. Root still verifies source/default closure and enforces preidentity, trace, phase order and final aggregation. All target verdicts remain pending.
