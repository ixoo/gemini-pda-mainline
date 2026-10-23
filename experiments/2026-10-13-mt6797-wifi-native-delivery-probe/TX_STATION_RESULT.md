# Single-arm station boots: consolidation is neutral; two harness and quota limits

Result record, 2026-10-23. Two boots on the `mt6797-a53-wifi-station` profile,
the consolidated single build arm (0234) with the proven monitor control
(0237), the data-end framing tolerance (0238) and, from the second boot, the
old mode parameters kept visible (0239). Same laptop, AP and TCP protocol as
the throughput series. Build inputs `ea9f8127` (station-1) and `f2db098f`
(station-2).

## station-1 (boot `abf5b2ef…`, candidate `7cc0a894…`, boot2 `2fdaa4e6…`)

Never reached Wi-Fi. The device-side session leaf reads the driver's old
`native_delivery_diag` parameter from sysfs before bringing the interface up;
0234 had removed it, the leaf's mode stage failed, and the device sat idle
until the host's poll budget ran out. The device's SSH server then refused
new connections and a manual power cycle into Gemian was needed; no sealed
log. Harness interface result, not a driver result; fixed by 0239.

## station-2 (boot `cb54b5d7…`, candidate `5cbd382f…`, boot2 `598c26b8…`)

Admitted at 35.8 s uptime, firmware start once, join, DHCP, three pings,
both TCP directions complete.

| Direction | station-2 | quiet-console | vendor |
|---|---:|---:|---:|
| TX, host received | **1.192 Mbit/s** (chunks 1.45 × 5) | 1.044 | 14.59 |
| RX, host sent | **9.85 Mbit/s** (device 8.47; device chunks 16–18) | 8.02 | 31.54 |
| CPU idle TX / RX | 86.3 % / 77.2 % | 86.8 % / — | — |

Completion gaps (2,312 ordinary completions, all statuses): median
**1.11 ms**, 75th percentile 8.0 ms, 1,466 below 6 ms, 809 in 6–12 ms, 15 in
12–25 ms, 21 above 25 ms. The single arm is behaviour-neutral or slightly
better than the quiet-console tree it was consolidated from.

**First failure.** The data phase ended at PM-relative 13.9 s by a local
disconnect, as in the quiet-console run, before the host's acknowledgment
(written at 17.4 s and then refused as late). The leaf's acknowledgment wait
checks its data-window marker in `dmesg`; the data phase had logged about
30,000 records (three per frame), the 1 MiB kernel ring had wrapped past the
marker, so the leaf took the window as closed, terminated the supplicant,
and the driver saw a disconnect. The teardown then stopped on the first pass
after data end: the 4,096-pass lifetime quota, inherited from the one-shot
scan diagnostics, had been consumed by the join under immediate
rescheduling, so the lifetime fail-stopped before any teardown command
(`status=-110 branch=1`, zero framing drops, zero Action frames).

Both are host-chosen limits, not device or firmware behaviour:

- the single-arm profiles now boot with an 8 MiB kernel ring, and proposal
  0246 demotes the two per-frame slot lines to debug messages, keeping the
  TX-done record the classifiers read;
- proposal 0245 removes the pass quota from the stop condition; the
  lifetime stays bounded by its join, frame, credit, data and teardown
  deadlines.

The session host refused export (owner quiescence); a separate reviewed
preservation proved the device quiescent, sealed the complete log (30,199
records) and returned the device to changed-boot Gemian
`135292c1-d711-46a4-855f-2ed92b3ff6c7`. No retry.

## Evidence

`artifacts/wifi-throughput-station2-1/` (sealed session), install receipts
under `artifacts/device-install-evidence/mt6797-wifi-tx-station-deployment-1/`
and `…-station2-deployment-1/`, [scalars](results/tx-station-runtime-scalars.json).
