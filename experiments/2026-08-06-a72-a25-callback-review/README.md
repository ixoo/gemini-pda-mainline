# Experiment: A25 callback and rollback review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-a25-callback-review` |
| Status | `partial` (source and rollback review passed; same-boot numeric identity remains open) |
| Subsystem | CPUHP startup callback inventory and automatic rollback closure |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Claim | `PARTIAL_A25_SOURCE_ROLLBACK_REVIEW` |

## Scope

This review rechecks the current A25 callback inventory H01–H15, the mandatory
dynamic relative order and conditional insertion points, and the P32A/D/F/X/R
rollback contracts against the current 178-entry series, including source
slices 0187–0189. It is deliberately
not a same-boot CPUHP-state capture and does not assign absolute `DYN+N`
slots.

## Result

The review passes all 15 callback rows, the three mandatory dynamic-order
chains, four conditional insertion classifications, all five P32 closure rows,
and current P32 patches 0182–0189. H13 remains open because the required
same-boot hotplug-state, module/probe, firmware, and boot-parameter capture is
not present. Therefore A25 is not fully closed, and no CPU_ON/OFF or device
action is authorized.

The executable review and its recorded hashes are in
[`scripts/review.py`](scripts/review.py) and
[`results/a25-review-20260806.txt`](results/a25-review-20260806.txt).
