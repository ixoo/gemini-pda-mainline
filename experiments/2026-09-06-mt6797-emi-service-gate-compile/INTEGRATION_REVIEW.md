# Integration review

Sol Medium accepted the frozen pre-Buildbox integration at
`2026-09-06T07:25:36Z` after two bounded validation repairs. The first complete
implementation review found that several refusal tests could pass after an
unexpected callback and that the verifier violated the frozen no-network
scope. Repair 1 added live callback and storage snapshots, direct state and
generation cases, and removed network access. Repair 2 closed the remaining
terminal-repeat snapshot, disjoint inventory and documented caller-precondition
gaps. The final offline verifier passed strict compilation, ASan/UBSan,
reproduction, predecessor-linkage and static-boundary checks.

The experiment and shared proposal are byte-identical at SHA-256
`3cd1c5c863e17dd13f0fbf4c53750484dd7fd442c2041218a336091c095849c2`.
Proposal 0011 occurs once immediately after 0010 in both the canonical and
selected series. The manifest-series validator checked all 194 profiles, its
eight mutation cases remained rejected, and the full repository publication
gate passed before commit `d1a0f9a9d840c4f050871b5128dc06aefb897214` was
pushed to the verified `origin/main`.

Buildbox replayed the fourteen-entry series and compiled a real AArch64
`emi-service-gate.o`. The object defines the two gate APIs and retains undefined
references to the three accepted predecessor helpers; every reference resolves
in final `vmlinux`. Prepared-source searches find no caller, export, initcall,
registration or effect API, and the existing active binding refusal remains
`-EOPNOTSUPP`. Strict Checkpatch has only the deliberately retained synthetic
missing-DCO error and new-file/MAINTAINERS warning.

The gate remains a compile/test seam with an injected callback. Build success
does not establish secure-service presence, resource ownership, policy,
serialization, firmware compatibility, mapping visibility, recovery, hardware
support or permission to activate the HIF. Final post-Buildbox Sol review
accepted the exact package, object/linkage evidence, Checkpatch classification
and scope boundary at `2026-09-06T07:37:46Z`. No device action is admitted.
