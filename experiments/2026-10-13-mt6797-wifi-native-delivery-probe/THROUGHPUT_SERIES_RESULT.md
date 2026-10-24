# Throughput series — where the driver stands and what limits it

Result record, 2026-10-23. Five sealed measurement runs on the same laptop, AP
and TCP protocol, plus one control on the vendor driver. No new device action is
described here; each run's own artefacts are named.

## Measured

| Run | Change | TX Mbit/s | RX Mbit/s | CPU idle TX/RX |
|---|---|---:|---:|---|
| baseline-2 | none (diagnostic profile) | 0.206 | not measured | 87.5% / — |
| pump-1 | immediate scheduling while work is pending | 0.291 | 2.846 | 86.5% / 82.6% |
| depth-1 | four data frames in flight, PID-matched | 0.506 | 7.061 | 84.3% / 77.3% |
| yield-1 | count no-progress turns; 1 ms while pending | 0.837 | 7.002 | 80.8% / 76.0% |
| phase-pending | active data phase counts as pending receive | 0.876 | 7.133 | 81.5% / 75.9% |
| [quiet-console](TX_QUIET_CONSOLE_RESULT.md) | console `loglevel=4`, no `ignore_loglevel`; driver unchanged | 1.044 | 8.015 | 86.8% / — |
| [station-2](TX_STATION_RESULT.md) | single build arm (0234, 0237, 0238, 0239); same command line | 1.192 | 9.852 | 86.3% / 77.2% |
| [station-3](TX_STATION_RESULT.md) | + 0245, 0246, 8 MiB ring; teardown completes | 1.225 | 10.010 | 87.7% / 76.9% |
| [flow-control](TX_FLOW_CONTROL_RESULT.md) | 0235: hold the mac80211 queue instead of dropping (retired) | 0.922 | 8.097 | 87.7% / 79.7% |
| **vendor control** | proprietary driver, Gemian | **14.59** | **31.54** | — |

Protocol in every column: five chunks per direction, 1 s or 1 MiB per chunk,
plain TCP for data, SSH only for control, prompt standard disconnect. The
vendor control used the same laptop as the far end.

## What the runs establish

1. **The link is not the limit.** The vendor driver moves 14.59 Mbit/s TX and
   31.54 Mbit/s RX on the same access point with the same host.
2. **Depth and scheduling are real but small levers.** Depth four and the
   progress-aware yield together took TX from 0.206 to 0.837 Mbit/s. Removing
   the 20 ms reschedule alone gave +41%; depth gave another +74%.
3. **The idle-timer hypothesis is dead.** `phase-pending` made an active data
   phase count as pending so the worker could never fall back to the 20 ms
   interval mid-stream. TX moved 0.837 → 0.876 (+4.7%), inside noise. That patch
   was therefore reverted; depth and yield are retained.

## What the numbers point at next

Per frame, from the sealed yield log: submit→complete median **9.19 ms** (of
which 4.2 ms is the frame's air time at the fixed 6 Mbps descriptor rate),
completion→next submit **4.8 ms**, giving ~12 ms of host-side work per frame and
~0.88 Mbit/s at ~1400 B. Two further facts constrain the explanation:

- CPU is ~80% idle, so this is latency per frame, not throughput per byte;
- completion gaps are bimodal: 4.2 ms inside bursts, 12–25 ms between them.

Two candidate causes remain, and they are separable:

- **per-frame HIF cost** — descriptor, payload and status each cost a transfer,
  so ~12 ms is three ~4 ms transactions (batching or DMA would collapse this);
- **per-frame descriptor rate** — every frame is sent at a fixed OFDM 6 Mbps
  (`join-tx.h`: `d[11] = 0x80`, `d[26..27] = 0x4b << 2`), so rate adaptation is
  disabled and the air-time ceiling is 6 Mbps regardless of channel quality.

The next experiment should change exactly one of those and measure against
0.876 Mbit/s. Everything else — depth, scheduling, the idle timer — has been
measured and is now either implemented or excluded.

## Evidence

- `artifacts/wifi-throughput-baseline-2/`, `-pump-1/`, `-depth-1/`, `-yield-1/`,
  `-phase-pending-1/` — sealed runs; each keeps its kmsg, plan and claim.
- `artifacts/wifi-vendor-baseline-1/vendor-baseline.json` — the control, with
  its caveats (vendor driver exposes no `iw`, so band/width/MCS unmeasured).
- Private analysis: `V65` (control and first analysis), `V66` (the falsified
  hypothesis and the per-frame cost argument).
