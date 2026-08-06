# Experiment: P32R integration review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-p32-r-review` |
| Status | `open` (P32A/P32X/P32R source slices and complete Buildbox package audited; device gates remain closed) |
| Subsystem | P32A/D/F/X/R rollback ownership and terminal ledger handoff |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Claim | `P32_HOOKS_VALIDATED_P32R_INTEGRATION_OPEN` |

## Findings

The current 0182–0186 source passes the hook-level obligations: publication
before outer rollback, exact generation/MPIDR/cookie/operation identity,
target disable/die guards, controller kill suppression, and one-shot side
channel consumption.

The review initially identified three integration gaps. The P32A callback
prefix is represented by source patch `0187`, the P32X effect-prefix source
slice by `0188`, and the P32R owner-ledger handoff by `0189`. Each passes an
independent format-patch/source audit; Buildbox validation of the complete
series is now the next gate.

The executable check records these gaps in
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
and parses as a format-patch. Buildbox was unavailable at the audit, so this
is not compiler or hardware evidence. P32X architecture-effect capture and
the P32R ledger handoff remain open; no CPU_ON/OFF or device action is
authorized.

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
It is not a compiler, Buildbox, runtime, or support claim.

The model now exercises the owner-ledger boundary explicitly: it preserves the
pre-fault membership/provider snapshot, moves a held provider to
`FAULT_UNKNOWN`, preserves a `NONE` provider state, rejects premature
provider/HPS/membership/retry side effects, and rejects mutations to the full
trace identity. The kernel-side owner handoff is now implemented by `0189`;
its source audit is recorded in
[`results/p32r-owner-ledger-source-audit-20260806.txt`](results/p32r-owner-ledger-source-audit-20260806.txt).
The complete 178-entry series now has a clean Buildbox validation for pushed
commit `49e2d6f4c0e634c8beaedb99a0c29ead1ad0ff6f`. The validated package and
fetched checksum/provenance record are in
[`results/p32r-buildbox-validation-20260806.txt`](results/p32r-buildbox-validation-20260806.txt).
This closes the compile/package gate only; no device boot or write was
performed, and the A25/A26/A14 admission gates remain open.
