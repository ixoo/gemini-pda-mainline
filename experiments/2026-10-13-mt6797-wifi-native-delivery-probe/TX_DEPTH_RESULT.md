# Data depth four: measured, consumed

One installed-candidate boot, one join, five chunks per direction, no retry.
The standard disconnect was accepted; cleanup reached whole-ledger stage 3
and reserved deauthentication reported status 0, transmitted. The controller
exited 0. Reviewed return and independent changed-boot Gemian verification
passed. This closes this finite depth comparison, not reconnect or sustained
Wi-Fi support. See [exact runtime scalars](results/tx-depth-runtime-scalars.json)
and [predeclaration/build identity](TX_DEPTH_COMPARISON.md).

## Comparison

| Metric | Pump-1 | Depth four |
| --- | ---: | ---: |
| Device TX aggregate Mbit/s | 0.291 | 0.506 |
| Device RX aggregate Mbit/s | 2.846 | 7.061 |
| Device CPU idle during TX | 86.5% | 84.3% |
| Device CPU idle during RX | 82.6% | 77.3% |
| TX statuses during TX / nonzero | 208 / 0 | 341 / 0 |
| Device TX statuses during RX / nonzero | 295 / 0 | 475 / 0 |

TX rose 73.9% over pump-1; baseline-2 TX was 0.206 Mbit/s under its older
51.8 s protocol. RX rose 148.1% over pump-1. Both new directions completed
five chunks with the same 1 s or 1 MiB bound and 100 ms gaps; plain nc data,
SSH control/progress, unchanged 2 MiB logger. Aggregate spans include gaps
and control overhead. Eight-CPU aggregate idle can hide one saturated core.

TX delivered 364224 bytes over 5.763185584 s; chunk rates were 0.575,
0.609, 0.621, 0.483 and 0.621 Mbit/s, all duration-ended. RX delivered
5242880 bytes over 5.94 s; every chunk hit its 1 MiB byte cap in 0.80–0.99 s.
Device-side chunk rates were 9.321, 8.473, 10.107, 10.486 and 9.020 Mbit/s.
This demonstrates approximately **8.5–10.5 Mbit/s RX capability in these short
chunks**, not a sustained rate. The 6 Mbps descriptor setting belongs to device
TX; no AP downlink PHY rate was measured.

## Ownership, status and credits

The trace reached four outstanding owners and never exceeded four. It ended
with 850 pool allocations/completions, zero pending/unowned, 724 completed-PID
reuses, six wraps and one separate reserved allocation. No out-of-order
completion occurred in this run; the actual-source fixtures exercise that
case. All owners and credits retired before stage 3. Ordinary-data phase:
846 completions, all status 0. Netdev TX drops/errors zero in both intervals;
RX dropped nine per direction, RX errors zero. Preserve those drops.

| Valid advanced firmware TX count | Pump TX | Depth TX | Pump RX | Depth RX |
| --- | ---: | ---: | ---: | ---: |
| 1 | 205 | 341 | 288 | 454 |
| 2 | 3 | 0 | 7 | 18 |
| 3 | 0 | 0 | 0 | 3 |

All these records have advanced=1. `ucTxCount` is directly observed; its
source does not define a retry formula. If it includes the initial attempt,
conditional extra attempts are pump 3/7 versus depth 0/24 during TX/RX.
RX-column events are device TX while receiving, not AP retry counts.
Whole-phase depth histogram is 825/18/3, sum 870 reported count units,
conditional extras 24. Status 0 reports transmission, not verified encryption
or an independent AP-ACK observation.

## Evidence and return

Live boot `f5572c15-f40b-448e-be37-19fdb30d296a`, build `957b5f3e`,
full boot2 SHA-256 `574fb99045fb13261235372fb1549b8682116fc534fc13d417226eb6787726c7`.
Actual configuration differs from pump-1 only by depth=4; fixed-rate descriptor,
credit guard, management waiter, admission and deadlines are unchanged.

All 75 pre-recovery seal entries verified once; seal SHA-256
`5672a969c963db97f8de16ede07b70bb5f7939efa42a7753588a9950f711f6c9`.
Complete kmsg: 780577 bytes, 5515 contiguous records (0–5514), SHA-256
`068faf3da1b4468d723c2e0f98404e6ee5f0c0b26ad704e6ae7dbf941edd8b78`.
No cap hit, truncation, fault or censorship flag. Quiescence and RAM-service
regression passed. Root independently confirmed Gemian `3.18.41+`, aarch64,
boot `f6c84475-5fff-4477-ab7a-ca45539d85ed` after reviewed return.

Host harness, source analysis and evidence verification were delegated;
root retained device custody and this final result. Inputs were verified at
stage boundaries or after material changes, not after every preparation edit.

## Completion-gap evidence and pump cause

[Exact completion-gap distribution](results/tx-depth-completion-gaps.json)
uses kernel TX-status timestamps, not on-air timestamps. Within the five TX
chunks: 270 completions and 265 adjacent gaps; 130 gaps are 4–5 ms, 94 are
28–32 ms (only three in 28–30 ms). Median 6.232 ms, p95 35.643 ms,
maximum 100.057 ms. The larger cluster is approximately 31.8 ms. These
within-chunk bins exclude intentional gaps; the full TX interval contains
341 completions/340 gaps and is recorded separately.

The actual pump counts every immediate iteration, even when TX progresses,
and after 32 it schedules the full 20 ms idle delay despite pending owners,
credits or queued data. That structural delay also postpones status retirement
and refill. The bimodal log supports starvation from this yield; it cannot
assign each observed hole to a guard trip without a scheduler trace. Likewise,
4.2 ms completion spacing is not a direct measurement of a frame's airtime.
The selected next pass tests this cause while preserving depth and rate.

## Next bounded question

Depth helped but did not remove the TX ceiling. The owner selected pump-yield
semantics as the next single-variable pass; rate remains separate. No further
depth change, credit change, DMA, key reuse, rekey or protected re-arm follows
from this result. Reconnect remains closed and safeguards dormant.
