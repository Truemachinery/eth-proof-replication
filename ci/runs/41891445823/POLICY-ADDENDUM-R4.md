# ABI 8 policy clarification for revision 4

This records the approved revision 4 coverage. The earlier policy draft is preserved as `DIAGNOSIS-R3-POLICY-DRAFT.md`; the current diagnosis clarifies socket creation. Original execution failure logs and receipts remain unchanged.

The approved revision explicitly permits the supported Landlock ABI with a minimum of 8, through the pinned Landrun's `--best-effort` mode. Source review of pinned Landrun and go-landlock identifies the missing ABI 9 right as pathname UNIX connect/sendmsg mediation (`RESOLVE_UNIX`). Earlier filesystem rights, classic TCP restrictions, IPC scopes and thread synchronization remain in that source configuration on ABI 8. This is a source-based description, not proof of every kernel operation's behavior.

The independent systemd test establishes denial of AF_UNIX **socket creation**. It does not establish complete UNIX-socket isolation: inherited sockets, `socketpair` and `io_uring` are outside that setting's documented coverage. It is not a complete ABI 9 replacement. Both the actual filesystem write-denial and socket-creation-denial controls remain mandatory; a failed control stops the job. No unrestricted mode or fake sandbox is introduced.

Official Comparator flags and proof/checker policies remain unchanged. Only the five additional harness-owned Landrun calls gain the compatibility flag, with an explicit architecture/ABI floor and early runtime preflight. The next Linux run must supply actual enforcement and proof outcomes. The local static/mock regression does not do so.

Primary sources: [Landrun811 sandbox implementation](https://github.com/zouuup/landrun/blob/811cfff51ceaf3d9843708aa6d22e9b84ccac8b4/internal/sandbox/sandbox.go), [go-landlock exact source](https://github.com/landlock-lsm/go-landlock/tree/e573f52a61e3072813de11359239d2ccae9705d2), [systemd documented creation-filter limits](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#RestrictAddressFamilies=). Same-team static review with exact source hashes is saved in `anthropic/landrun-abi8-source-review-r1.json`; no Linux execution by that reviewer is claimed.
