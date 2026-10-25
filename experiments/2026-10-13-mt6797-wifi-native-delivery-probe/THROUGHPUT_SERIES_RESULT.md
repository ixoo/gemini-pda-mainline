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
| [rx-batch-4](HIF_TRANSPORT_ANALYSIS.md#boot-4-of-0268-2026-10-25-the-measurement--the-register-work-was-not-the-receive-cost-either) | 0268 (enhanced status block + one aggregated read per queue, WHCR untouched): 12,754 frames, 5,706 aggregates, 0 failures; kept | 2.64 | floor (every receive chunk byte-capped at 1 MiB in under a second): 6.37 (device-side chunks 8.5–12.2) | 86.4% / 77.9% |
| [probe-1](HIF_TRANSPORT_ANALYSIS.md#probe-boot-1-2026-10-25-the-tcp-samples-came-the-ping-and-the-udp-bursts-did-not) | lifecycle tree, batching compiled out (0268 retired from admission); receive probe host-side: TCP samples valid (RTT 61–102 ms median in-chunk, window ample), ping and UDP void (injection order), re-run on the same image | 2.69 | floor (every receive chunk byte-capped at 1 MiB in under a second): 6.78 (device-side chunks 10.1–12.5) | 85.7% / 80.3% |
| [probe-2](HIF_TRANSPORT_ANALYSIS.md#probe-boot-2-2026-10-25-a-graded-repeat-the-probe-ran-disabled-by-the-staging) | same image; probe disabled by a renamed staging flag (graded repeat only) | 2.67 | floor (every receive chunk byte-capped at 1 MiB in under a second): 6.99 (device-side chunks 11.8–12.5) | 86.1% / 81.0% |
| [probe-3](HIF_TRANSPORT_ANALYSIS.md#probe-boot-3-2026-10-25-voided-before-the-measurement-recovered-through-the-reviewed-path) | same image; void: the device command crossed the 4096-byte bound (base 433, not the preflight's 405); recovered through the reviewed path | void | void | — |
| [probe-4](HIF_TRANSPORT_ANALYSIS.md#probe-boot-4-2026-10-25-1139-utc-the-readings-graded-correctly) (11:39 UTC session) | same image; the probe ran: UDP 10 and 20 Mbit/s delivered with zero loss, RTT 7–8 ms at rest and 40–130 under load, window ample; the verdict line was a diagnostic-ceiling artefact (8,192 queued frames) | 3.14 (chunks 3.73–4.07) | floor (every receive chunk byte-capped at 1 MiB in under a second): 7.78 (device-side chunks 14.5–15.8) | 86.2% / 78.3% |
| [boot B](HIF_TRANSPORT_ANALYSIS.md#boot-b-result-2026-10-25-1208-utc-a-regression-0272-retired-0269-reverted) (12:08 UTC, same session as probe-4) | 0272 ordinary data retired at submission + 0269 ceiling raised (both retired/reverted): TX unchanged, receive collapsed (four chunks on the device timeout), RTT to 438 ms; AP downlink read at 54 Mbit/s | 3.07 (chunks 3.13–3.76) | 3.50 (device-side chunks 11.3, 7.6, 1.5, 0.95, 1.2) | 89.1% / 88.5% |
| [boot C](HIF_TRANSPORT_ANALYSIS.md#boot-c-result-2026-10-25-1314-utc-54-mbits-acknowledged-transmit-19-the-log-cut-at-the-cap) (13:14 UTC; cross-session, ±40 % floor) | 0273 fixed rate code 0x4c (OFDM 54 Mbit/s) on the admitted tree with 0270, 0271, 0274: frames acknowledged (5 of 5,132 unacknowledged), TX ×1.9, receive +13 % (inside the floor), in-chunk round trip down by a third; the device log sealed at its 2 MiB cap in the transmit phase (per-frame records), so the verdict failed on the log and no end-of-phase line exists | 5.53 (chunks 6.64–7.84) | floor (every receive chunk byte-capped at 1 MiB in under a second): 7.19 (device-side chunks 16.5–18.2) | 83.0% / 76.5% |
| [boot D](TX_AUTORATE_RESULT.md#state-2-station-record-boot-second-attempt-result-2026-10-25-1506-utc--the-table-is-valid-the-selection-stays-at-6-mbits-the-rate-thread-closes) (15:06 UTC; rate profile; **two chunks, valid but not a series row**; cross-session) | state-2 record (0277) accepted, data without a fixed rate (0276, code 0) acknowledged with the firmware's rate word 0x004b on every frame: the table is valid, the selection stays at 6 Mbit/s; the rate thread closes on the fixed 54 descriptor; log complete, three probe legs, disconnect | 3.45 (chunks 3.81–3.95) | floor (every receive chunk byte-capped at 1 MiB in under a second): 7.91 (device-side chunks 15.8, 10.4) | 86.7% / 82.3% |
| [boot E](HIF_TRANSPORT_ANALYSIS.md#boot-e-result-2026-10-25-1538-utc-the-credit-model-is-the-completion-path-for-transmit-receive-did-not-follow) (15:38 UTC; cross-session against boot C) | 0278 ordinary data retired on credit arrival (no PID, no status report) on the baseline tree, with 0275 v2 and 0279 aggregate records: 5,637 frames retired, mean wait 3.5 ms at four in flight, no expiry, no fault; every TX chunk hit the 1 MiB cap in 0.9 s (the TX figure is a floor); receive inside the floor; UDP 30 Mbit/s zero loss; 0274 v2 verified (beyond=3304); log 173 KB for five chunks | floor (1 MiB in 0.91 s on every transmit chunk): 7.74 (chunks 9.18–9.46, cap-bound) | floor (every receive chunk byte-capped at 1 MiB in under a second): 13.53 (device-side chunks 17.9–20.0) | 89.1% / 86.4% |
| **vendor control** | proprietary driver, Gemian | **14.59** | **31.54** | — |

Noise floor, corrected (2026-10-25): the same image measured TX 3.2–3.4 /
RX 8.5–12.5 device-side at 02:00 and TX 3.7–4.1 / RX 14.5–15.8 at 11:39.
Session-to-session variance is about ±40 %; a driver change is judged
against the adjacent boot in the same session or A/B inside one boot, and
"the band" in any row above means the band of that row's session.
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
8. **The receive path is not the ceiling.** The probe (boot 4) delivered
   UDP at 20 Mbit/s offered with zero loss and no return traffic while TCP
   received 14.5–15.8 device-side in the same session; the round trip is
   7–8 ms at rest and 40–130 ms under load with the window ample. The
   receive number tracks the acknowledgement path, our transmit side; the
   interrupt is not next, the transmit completion lever is
   ([transport record §11](HIF_TRANSPORT_ANALYSIS.md#probe-boot-4-2026-10-25-1139-utc-the-readings-graded-correctly)).

## Measurement protocol and floors (owner, 2026-10-25)

**Floors.** The 1 MiB-per-chunk cap, set for the 6 Mbit/s era, ended every
receive chunk from rx-batch-4 onward before its second (0.45–0.99 s) and
every transmit chunk of boot E (0.91 s): those rates are rates over a
window holding a large share of slow start, and the table marks them as
floors so they are never averaged with steady-state numbers. From boot F
the protocol is a chunk of 4 MiB or 3 s, whichever comes first, with the
rate over the chunk's final half recorded beside the whole-chunk rate
([`hosts/steady_state_chunks.py`](hosts/steady_state_chunks.py)); the
chunk count and the two directions stay the same so the series remains
comparable, and pre-protocol rows are floors.

**Instruments and the sealed logger.** 173 KB for five chunks at 54 Mbit/s
(boot E) settles the logger question: the per-phase histograms (the
transmit rate words, the completion latency, the credit-retire record)
were the right instrument and the 2 MiB cap was never the real
constraint; the cap is not reopened when a future instrument grows, the
instrument changes shape. The corollary: a measurement is never shortened
to fit an instrument (boot D's two chunks were that mistake, declared and
valid but not a series row), and a run that seals its log before its data
ends is a harness fault, not a reason to measure less. The per-frame lines
remain available behind `CONFIG_MT6797_TX_PER_FRAME_RECORD` for a boot
that needs raw lines.

**Memory policy for measurement runs.** Pageable memory is not scarce on
this device: instruments and buffers may use up to about 64 MiB per run
(the TC1 ledger at 52 pages was 6.6 kB of accounting against the
firmware's 468-page, 60 kB budget; depth 12 adds about 18 kB of socket
buffers; the constraint lifted by the depth sweep was a conservation
habit, not RAM). Two memories do not move with this policy: the
device-tree reserved pools (`consys-reserve-memory` 2 MiB,
`reserve-memory-scp_share` 16 MiB, `mblock-7-ccci` 12 MiB, all `nomap`),
which serve whatever must be physically contiguous or uncached for the
HIF and AP-DMA, and the CONNSYS firmware's own heaps, rings and TC pools
inside that reserve, which the host cannot grow by allocating more. Those
move only with device-tree provenance.

## The baseline from boot C (decision, 2026-10-25)

The fixed-54 tree (the lifecycle tree with 0273 at 0x4c and the logging
records) is the admitted baseline every future measurement runs: measured
1.9× faster than fixed 6, its air time no longer the limit. The adaptive
tree (rate code 0 with the state-2 record) is a proposal profile with one
open question. One quantity limits both directions, about 1.5 ms per
frame: TX 7.4 Mbit/s at 54 where the air is 0.3 ms a frame; TCP receive
15.8 with one acknowledgement per 1.47 ms (measured by the probe's
`rttcur` samples), while UDP carries 29 Mbit/s at 2 % loss through the
same path (boot D). The per-frame figure is derived (rate ÷ depth); the
samples and the UDP counts are measured. The next boot attacks that number
directly (the credit model, §15 of the transport record), read on both
directions in the same boot.

## What 802.11ac would need (noted 2026-10-25, after the transport)

The firmware supports VHT 1×1; the station side is host work: HT/VHT
capability advertisement and the peer's capabilities in the station record
and BSS info (PHY type set, HT/VHT capability fields, VHT MCS maps, channel
width), a working rate table (boot D: valid but not adapting), QoS data
with TIDs, WMM parameters and four access-category queues, block-ack
sessions with host-side reordering, and 80 MHz channel configuration.
A-MSDU needs HT capability, so "larger frames per transaction" sits behind
capability advertisement alongside A-MPDU; the only transport lever that
stands alone is fewer bus transactions per frame. The access point already
sends to this station at 54 Mbit/s OFDM: the received-rate record (boot B:
index 12 on 6,249 of 8,541 frames; boot D: 5,849 of 7,446), not an
inference from our twelve advertised rates. None of this helps until the
per-frame cost is fixed: at 1.5 ms a frame the ceiling is the same at 54
or 433 Mbit/s.

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
