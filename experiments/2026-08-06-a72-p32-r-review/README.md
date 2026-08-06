# Experiment: P32R integration review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-p32-r-review` |
| Status | `open` (P32A/P32X/P32R source slices and dedicated Buildbox package audited; device gates remain closed) |
| Subsystem | P32A/D/F/X/R rollback ownership and terminal ledger handoff |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Claim | `P32_HOOKS_VALIDATED_P32R_SOURCE_COMPLETE` (pending 0191 Buildbox refresh) |

## Findings

The current 0182–0191 source passes the hook-level obligations: publication
before outer rollback, exact generation/MPIDR/cookie/operation identity,
target disable/die guards, controller kill suppression, and one-shot side
channel consumption.

The review initially identified three integration gaps. The P32A callback
prefix is represented by source patches `0187` and `0190`, the P32X
effect-prefix source slice by `0188` and `0190`, and the P32R owner-ledger
handoff by `0189` and `0190`. The source audit now verifies registration
inventory/capacity coverage, required/seen/missing/forbidden effect masks, and
owner rejection of incomplete coverage. The dedicated profile has passed
Buildbox validation with the guarded P32 code enabled.

The executable check records this source-complete result in
[`results/p32-r-review-20260806.txt`](results/p32-r-review-20260806.txt).
No CPU_ON/OFF or device action is authorized.

The bounded implementation contract is now recorded in
[`DESIGN.md`](DESIGN.md). It defines separate callback-prefix,
architecture-effect, and ledger-handoff records, rejects truncation and
unknown effects, and keeps provider/membership changes owner-controlled. The
independent fifteen-probe model is
[`scripts/integration_oracle.py`](scripts/integration_oracle.py), with its
result in
[`results/p32r-integration-design-20260806.txt`](results/p32r-integration-design-20260806.txt).
The first source slice is recorded in
[`results/p32a-prefix-source-audit-20260806.txt`](results/p32a-prefix-source-audit-20260806.txt)
and parses as a format-patch. The dedicated source audit now closes the P32X
architecture-effect and P32R ledger coverage gaps with explicit inventory and
effect masks. No CPU_ON/OFF or device action is authorized.

A read-only Buildbox-source audit then found that `publish_p32()` was gated on
`MT6797_A72_PHASE_VERIFYING`, a declared phase with no transition in the pinned
owner state machine. Patch `0191` changes that guard to the live
`MT6797_A72_PHASE_ON_ISSUED` phase established by P17/P18 publication. The
observation and fix are recorded in
[`results/p32-publication-reachability-20260806.txt`](results/p32-publication-reachability-20260806.txt).
The fix requires a fresh dedicated Buildbox validation; A39 early-secondary
terminal attribution remains a separate admission blocker.

The first Buildbox submission exposed an integration defect in `0187`: patch
`0182` had already introduced the rollback callback declaration, so the source
slice was repaired to replace that declaration rather than add a duplicate.
The repair is recorded in
[`results/p32a-prefix-source-repair-20260806.txt`](results/p32a-prefix-source-repair-20260806.txt);
the complete series requires a fresh Buildbox validation.

The exact P32X operation placement is now recorded in
[`P32X-PLACEMENT.md`](P32X-PLACEMENT.md), with its source-reference result in
[`results/p32x-placement-review-20260806.txt`](results/p32x-placement-review-20260806.txt).
The `0188` effect-prefix source audit is recorded in
[`results/p32x-effect-prefix-source-audit-20260806.txt`](results/p32x-effect-prefix-source-audit-20260806.txt).
It is not a runtime or hardware-support claim.

The model now exercises the owner-ledger boundary explicitly: it preserves the
pre-fault membership/provider snapshot, moves a held provider to
`FAULT_UNKNOWN`, preserves a `NONE` provider state, rejects premature
provider/HPS/membership/retry side effects, and rejects mutations to the full
trace identity. The kernel-side owner handoff is now implemented by `0189`;
its source audit is recorded in
[`results/p32r-owner-ledger-source-audit-20260806.txt`](results/p32r-owner-ledger-source-audit-20260806.txt).
The complete 179-entry series has a dedicated `a72-p32-rollback` Buildbox
validation at pushed commit `f6f0fe985f67f9b1068d9935314bc485a5abbdea`, with
`CONFIG_ARM64_MT6797_A72_P32_ROLLBACK=y`. The validated package and fetched
checksum/provenance records are in
[`results/p32r-buildbox-validation-20260806.txt`](results/p32r-buildbox-validation-20260806.txt).
This closes the compile/package gate only; no device boot or write was
performed, and the A25/A26/A14 admission gates remain open.

The first dedicated `a72-p32-rollback` profile build at `7864f80` exposed a
real guarded-source signature defect that the generic `full` profile could not
see. It is recorded in
[`results/p32r-buildbox-failure-20260806.txt`](results/p32r-buildbox-failure-20260806.txt).
Patch `0190` fixed that call and closed the inventory/effect-coverage gaps;
the successful dedicated-profile result above validates the guarded source.
