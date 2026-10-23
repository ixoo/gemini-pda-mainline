# Quiet-console measurement: console cost removed, teardown framing refusal

Result record, 2026-10-23. One sealed boot on the `mt6797-a53-wifi-quiet-console`
profile: the tx-yield driver (patch 0233) with one change, the kernel command
line keeps messages below warning level off the serial console
(`loglevel=4`, no `ignore_loglevel`). Build input `7237af14`, candidate
`candidate-a4158f41…`, boot2 `da4fadcc…`, kernel notes `4eba0b54…`, mainline
boot `cc8a3b7c-ff91-4136-b983-accd84aff9bf`. Same laptop, AP and TCP protocol
as the throughput series (five chunks per direction, 1 s or 1 MiB each).

## Measured

| Direction | quiet-console | phase-pending (previous) | vendor |
|---|---:|---:|---:|
| TX, host received | **1.044 Mbit/s** (chunks 1.12 → 1.29) | 0.876 | 14.59 |
| RX, host sent | **8.02 Mbit/s** (device chunks 9.9 → 12.0) | 7.13 | 31.54 |
| CPU idle during TX | 86.8 % | 81.5 % | — |

Per-frame cost, from the sealed log (2,487 ordinary completions, all statuses):

| Gap between TX completions | quiet-console | yield-1 |
|---|---:|---:|
| median | **1.05 ms** | 8.22 ms |
| 75th percentile | 7.9 ms | 15.8 ms |
| < 6 ms | 1,665 | 402 |
| 6–12 ms | 743 | 288 |
| 12–25 ms | **40** | 303 |
| > 25 ms | 38 | 46 |

## What it establishes

1. **The synchronous console was a large share of the host-side per-frame
   constant.** With the same driver, the median completion gap fell from
   8.2 ms to about 1 ms and the 12–25 ms population almost disappeared. The
   driver emits several informational lines per data frame; printing them on
   the 921600-baud console inside the worker serialised with the transfers.
2. **TX did not rise in proportion** (+19 %). The remaining limit at this
   point is the bounded data queue, which still frees the ninth queued frame
   unsent: TCP sees that as loss. Proposal 0235 (mac80211 flow control) is the
   next single variable; 0236 (four frames in flight on the TC1 budget and
   several submissions per pass) follows.
3. **A teardown defect surfaced.** The data phase ended (local disconnect at
   PM-relative 13.9 s, 2,481 of 2,483 data frames completed, 19 PID wraps,
   zero unowned) with the host-to-device stream still in flight. The first
   receive record after the monitor-control disable carried the other
   state's framing (header 1548 in a 1596-byte selection); the exact-match
   gate refused it and the lifetime fail-stopped before any teardown command
   was sent, so no key removal, station removal or BSS deactivation ran and
   the host refused export until the device was proven quiescent. Proposal
   0238 counts and drops such records after data end and lets the teardown
   proceed; it is in every later measurement series.

## Session outcome

Capture passed (fresh identity at 6.9 s uptime, firmware start once, common
init 285/285). Join, DHCP, three initial pings, both TCP directions and the
local disconnect ran. The session host then refused export because its
quiescence query failed (exit 63), a host-side result; the driver's own
fail-stop is item 3 above. A separate reviewed preservation proved the device
quiescent, sealed the complete log (12,030 records through the explicit seal,
`67c45123…`), requested the native reboot and confirmed changed-boot Gemian
`d2d47ea1-90df-4845-9e8c-8ac1b1dff2b0`. No retry. Standard-disconnect
grading, delivery status and cleanup stage are **not established** by this
run; throughput and the per-frame cost are.

## Evidence

`artifacts/wifi-throughput-quiet-console-1/` (sealed session, PRE_RECOVERY and
FINAL hash lists), `artifacts/device-install-evidence/mt6797-wifi-tx-quiet-console-deployment-1/`
(install receipt, full readback verified),
[validator](validate-tx-quiet-console-candidate.py),
[scalars](results/tx-quiet-console-runtime-scalars.json).
