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
| [pipelining](TX_PIPELINING_RESULT.md) | 0236: every admissible data frame per pass, 52-page TC1 budget (+0243, 0247) | **3.198** | 7.626 | 85.8% / 77.6% |
| [autorate](TX_AUTORATE_RESULT.md) | 0242: fixed-rate bit cleared for data (retired) | no frame acknowledged | — | — |
| [rate-2](TX_AUTORATE_RESULT.md) | 0255: zero rate word for ordinary data, the vendor data descriptor (retired) | no data frame acknowledged (status 3 ×4; fixed-rate frames status 0) | — | — |
| [rx-fix](RX_REBASELINE_RESULT.md#rx-fix-boot-0256-retired-the-order-inside-the-pass-is-not-the-mechanism) | 0256: receive port served before submission in a busy pass (retired) | 2.75 | 7.23 (device-side chunks 11.3–12.7) | 86.2% / 78.5% |
| [rx-rebaseline](RX_REBASELINE_RESULT.md) | lifecycle tree (0236 + 0240–0254), five chunks, one lifetime, nothing changed | 2.760 | 6.99 (device-side chunks 10.5–12.0) | 86.1% / 78.5% |
| [dma-tx-1](HIF_TRANSPORT_ANALYSIS.md#6-transmit-dma-boot-1-2026-10-24-a-composition-defect-not-a-driver-result) | 0258–0260 built with transmit DMA, but the composed device tree lacked the channel: PIO throughout (composition defect; re-run staged) | 2.62 | 6.91 (device-side chunks 10.6–12.9) | 86.2% / 79.9% |
| [dma-tx-2](HIF_TRANSPORT_ANALYSIS.md#6-transmit-dma-boot-1-2026-10-24-a-composition-defect-not-a-driver-result) | 0258–0260, transmit direction by AP-DMA channel 0: attached, 3,712 transfers, 0 failures; receive still PIO | 2.69 | 7.04 (device-side chunks 11.8–12.9) | 86.3% / 79.5% |
| **vendor control** | proprietary driver, Gemian | **14.59** | **31.54** | — |
| **vendor control 2** (2026-10-24) | proprietary driver, Gemian, same method, after the RX-fix boot | **45.1** | **38.5** | — |

The device tree these runs booted is not reproducible from committed inputs (one inherited `board.dtb` since 2026-10-17, see the [transport record §6](HIF_TRANSPORT_ANALYSIS.md#6-transmit-dma-boot-1-2026-10-24-a-composition-defect-not-a-driver-result)); proposal 0261 reproduces it from source ([provenance record](DEVICE_TREE_PROVENANCE.md)); the equivalence boot is pending and precedes further device work.

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
4. **Pipelining confirmed the per-frame host-cost diagnosis.** 0236 submits
   every admissible data frame per worker pass; the ~12 ms per frame was
   descriptor, payload and status per pass, and TX went 1.225 → 3.198
   Mbit/s ([pipelining](TX_PIPELINING_RESULT.md)). That closes this series;
   the rate word is the next single variable.

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
