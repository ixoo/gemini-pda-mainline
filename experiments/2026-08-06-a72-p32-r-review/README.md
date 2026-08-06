# Experiment: P32R integration review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-p32-r-review` |
| Status | `open` (P32A audited; P32X placement reviewed; Buildbox, P32X implementation, and P32R remain open) |
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
prefix is now represented by source patch `0187` and passes the independent
format-patch/source audit, but it still needs Buildbox validation. Two
integration gaps remain:

1. P32X has no complete architecture-effect prefix for topology, NUMA,
   online/present masks, IPI, IRQ, RCU, and lockdep divergence.
2. P32R consumption changes the P32 record only; it does not yet hand the
   terminal divergence into the membership/provider/A30 ledger before any
   completion or HPS accounting.

The executable check records these gaps in
[`results/p32-r-review-20260806.txt`](results/p32-r-review-20260806.txt).
No CPU_ON/OFF or device action is authorized.

The bounded implementation contract is now recorded in
[`DESIGN.md`](DESIGN.md). It defines separate callback-prefix,
architecture-effect, and ledger-handoff records, rejects truncation and
unknown effects, and keeps provider/membership changes owner-controlled. The
independent nine-probe model is
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
This narrows the next source patch to the arm64 disable boundary first; it is
not an implementation or support claim.
