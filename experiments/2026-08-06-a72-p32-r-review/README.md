# Experiment: P32R integration review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-p32-r-review` |
| Status | `open` (P32A/P32X source slices audited; Buildbox and P32R remain open) |
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
prefix is now represented by source patch `0187`, and the P32X effect-prefix
source slice is represented by `0188`; both pass independent
format-patch/source audits, but Buildbox validation is still required. One
integration gap remains:

1. P32R consumption changes the P32 record only; it does not yet hand the
   terminal divergence into the membership/provider/A30 ledger before any
   completion or HPS accounting.

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

The exact P32X operation placement is now recorded in
[`P32X-PLACEMENT.md`](P32X-PLACEMENT.md), with its source-reference result in
[`results/p32x-placement-review-20260806.txt`](results/p32x-placement-review-20260806.txt).
The `0188` effect-prefix source audit is recorded in
[`results/p32x-effect-prefix-source-audit-20260806.txt`](results/p32x-effect-prefix-source-audit-20260806.txt).
It is not a compiler, Buildbox, runtime, or support claim; P32R completeness
and ledger handoff remain open.

The model now exercises the owner-ledger boundary explicitly: it preserves the
pre-fault membership/provider snapshot, moves a held provider to
`FAULT_UNKNOWN`, preserves a `NONE` provider state, rejects premature
provider/HPS/membership/retry side effects, and rejects mutations to the full
trace identity. The kernel-side owner handoff still requires an implementation
and a clean Buildbox compile.
