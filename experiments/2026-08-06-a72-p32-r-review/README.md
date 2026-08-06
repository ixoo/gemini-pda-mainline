# Experiment: P32R integration review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-p32-r-review` |
| Status | `open` (hook/identity guards validated; P32R integration gaps confirmed) |
| Subsystem | P32A/D/F/X/R rollback ownership and terminal ledger handoff |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Claim | `P32_HOOKS_VALIDATED_P32R_INTEGRATION_OPEN` |

## Findings

The current 0182–0186 source passes the hook-level obligations: publication
before outer rollback, exact generation/MPIDR/cookie/operation identity,
target disable/die guards, controller kill suppression, and one-shot side
channel consumption.

The review does not close the full frozen P32 contract. Three integration gaps
remain:

1. P32A does not yet record the nested `cpuhp_kick_ap()` callback prefix and
   reset state.
2. P32X has no complete architecture-effect prefix for topology, NUMA,
   online/present masks, IPI, IRQ, RCU, and lockdep divergence.
3. P32R consumption changes the P32 record only; it does not yet hand the
   terminal divergence into the membership/provider/A30 ledger before any
   completion or HPS accounting.

The executable check records these gaps in
[`results/p32-r-review-20260806.txt`](results/p32-r-review-20260806.txt).
No CPU_ON/OFF or device action is authorized.
