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
| [service-1](DEVICE_TREE_PROVENANCE.md#equivalence-boot-passed-2026-10-24) | same kernel as dma-tx-2; device tree built from the committed series (0261) instead of the inherited binary | 2.63 | 6.77 (device-side chunks 10.0–12.5) | 86.4% / 79.6% |
| [service-2](DEVICE_TREE_PROVENANCE.md#closing-the-chain-on-the-device-result-2026-10-24) | same image; the booted tree read back and compared with the build | 2.67 | 7.54 (device-side chunks 11.7–12.7) | 86.5% / 78.2% |
| [rate-3](TX_AUTORATE_RESULT.md#rate-visibility-boot-result-2026-10-24--branch-3-an-empty-rate-table) | 0262 rate record + 0263 unforced data rate (retired): every status-3 frame reports rate word 0x0000; control frames 0x004b | no data frame acknowledged | — | — |
| [pass-rate](RX_REBASELINE_RESULT.md#pass-rate-boot-result-2026-10-24--neither-direction-moved-the-polled-read-is-the-ceiling) | 0264 census + 0265 one data submission per pass (retired): 5,011 passes/s, 0.034 frames/pass | 2.55 | 7.16 (device-side chunks 11.5–12.2) | 86.4% / 78.4% |
| [rx-dma](HIF_TRANSPORT_ANALYSIS.md#9-receive-direction-dma-boot-result-2026-10-24--engaged-intact-and-not-the-ceiling) | AP-DMA both directions: 3,870 out, 8,510 in, 0 failures; kept | 2.63 | 6.67 (device-side chunks 9.6–11.8) | 85.9% / 81.0% |
| [state-2](TX_AUTORATE_RESULT.md#state-2-station-record-boot-inconclusive-join-refused-0266-retired-2026-10-24) | 0266 state-2 station record (retired): our encoder refused state 2 (-22), join stopped before any data phase | inconclusive (join refused) | inconclusive (join refused) | — |
| [rx-batch-1](HIF_TRANSPORT_ANALYSIS.md#boot-1-of-0268-2026-10-25-the-join-stopped-at-its-credit-wait-the-block-read-had-consumed-the-tx-release-counts) | 0268 first form (enhanced status block + aggregated reads): the block read consumed the TX release counts, the join stopped at its credit wait; amended | inconclusive (join stopped) | inconclusive (join stopped) | — |
| [rx-batch-2](HIF_TRANSPORT_ANALYSIS.md#boot-2-of-0268-2026-10-25-the-credits-came-the-join-guard-refused-at-the-second-eapol-message) | 0268 amended (block TX counts merged into the credit path): every credit returned, join reached EAPOL message 2, then the join guard refused with -EIO at debt 0; guard record added | inconclusive (join stopped) | inconclusive (join stopped) | — |
| [rx-batch-3](HIF_TRANSPORT_ANALYSIS.md#boot-3-of-0268-2026-10-25-the-guards-words-name-the-abnormal-interrupt-the-cause-is-our-own-whcr-write) | 0268 with the guard record: `whisr=0x42`, the device's abnormal interrupt; cause: the enable wrote WHCR bit 16 (RX enhancement, a mode the vendor clears); WHCR no longer written | inconclusive (join stopped) | inconclusive (join stopped) | — |
| [rx-batch-4](HIF_TRANSPORT_ANALYSIS.md#boot-4-of-0268-2026-10-25-the-measurement--the-register-work-was-not-the-receive-cost-either) | 0268 (enhanced status block + one aggregated read per queue, WHCR untouched): 12,754 frames, 5,706 aggregates, 0 failures; kept | 2.64 | 6.37 (device-side chunks 8.5–12.2) | 86.4% / 77.9% |
| **vendor control** | proprietary driver, Gemian | **14.59** | **31.54** | — |
| **vendor control 2** (2026-10-24) | proprietary driver, Gemian, same method, after the RX-fix boot | **45.1** | **38.5** | — |

Runs before 2026-10-24 booted an inherited `board.dtb` that no build produced; proposal 0261 reproduces it from source and the [equivalence boot](DEVICE_TREE_PROVENANCE.md#equivalence-boot-passed-2026-10-24) confirmed the series' results stand on it.

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
6. **Neither is the receive data copy.** With AP-DMA moving every received
   packet, receive stayed at 6.67 host-side; the per-frame poll structure
   (WRPLR read, guard, status) is the receive ceiling, and the interrupt
   with the enhanced-status read is the next transport step
   ([transport record §9](HIF_TRANSPORT_ANALYSIS.md#9-receive-direction-dma-boot-result-2026-10-24--engaged-intact-and-not-the-ceiling)).
5. **The transmit data copy is not the bottleneck.** Transmit-DMA boot 2
   moved every data frame by AP-DMA with zero failures and changed neither
   direction ([transport record §7](HIF_TRANSPORT_ANALYSIS.md#7-conclusion-the-transmit-data-copy-is-not-the-bottleneck));
   the forced 6 Mbit/s rate is what remains on transmit, and the receive
   worker is measured separately.
7. **Nor is the receive register work.** Receive by the enhanced status
   block and aggregated reads (0268, boot 4) moved every frame of the data
   phase with zero failures and left receive at 6.37 host-side. The same
   log shows the transmit completion rate during the receive chunks at the
   TCP acknowledgement rate, so the receive number may be clocked by the
   transmit path's per-frame latency; an acknowledgement-free receive
   measurement separates that from the receive path before the interrupt
   is tried ([transport record §10](HIF_TRANSPORT_ANALYSIS.md#boot-4-of-0268-2026-10-25-the-measurement--the-register-work-was-not-the-receive-cost-either)).

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
