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
| [boot F](HIF_TRANSPORT_ANALYSIS.md#boot-f-result-2026-10-25-1613-utc-depth-8-did-not-move-transmit-the-slots-are-half-empty-the-limit-is-upstream-of-the-driver) (16:13 UTC; first steady-state protocol run, 4 MiB or 3 s chunks) | 0280 at data depth 8 (ledger 104) on the credit-retire baseline: no change, the service rate is fixed: transmit 9.2 Mbit/s steady (one chunk stalled to 1.9), wait 3.48 → 4.47 ms with the service time 1.24 ms a frame at both depths (utilisation 0.99): the firmware's per-frame transmit processing is the limit at ~800 frames/s; depth returns to 4, the sweep stops, aggregation (HT) is the throughput lever; one receive chunk cut by the protocol's bound race (fixed), not a collapse; UDP 30 Mbit/s zero loss | 7.40 (chunks 9.15–9.36 steady, one at 1.91) | 13.57 (device-side chunks 13.7–20.1, cap-bound after 1.7 s; the fifth at the device's bound 8.9) | 89.7% / 87.8% |
| [boot H, run 3](HIF_TRANSPORT_ANALYSIS.md#boot-h-third-run-2026-10-25-1714-utc-whole-the-transmit-limit-is-the-drivers-own-drops-not-the-air-not-the-depth-and-tcp-holds-a-six-segment-window-because-of-them) (17:14 UTC; steady-state chunks; two earlier runs void on the harness) | 0281 sampled status report (one in 64) on the baseline: 373 samples all at 0x4c status 0 (the air exonerated); the device's TCP at cwnd 6 / ssthresh 5–6 on every chunk with 451 retransmissions (1.9 %) that no counter and no sampled report shows: the driver frees frames unsent when its 8-frame queue is full (no backpressure); echo legs lose 29–54 % above ~9 Mbit/s offered; the transmit limit is the drain rate (~800–1,000 frames/s) plus the drops | 8.95 (chunks 9.19–9.73 steady) | 17.07 (device-side chunks 14.5–20.3, cap-bound after 1.65 s) | 89.6% / 86.7% |
| [boot I](HIF_TRANSPORT_ANALYSIS.md#boot-i-result-2026-10-25-1733-utc-the-mechanism-works-the-queue-discipline-does-not) (17:33 UTC; same run) | 0282 backpressure toward mac80211 on boot H's tree: 2,223 stops and wakes, zero frames freed unsent, and transmit fell to a third with 549 retransmissions (3.3 %) and a receive chunk at the device's bound; reverted by the rule; the losses TCP counts are not the driver's drops nor the air (257 clean samples): retransmission without loss is the remaining reading | 3.34 (chunks 2.46–4.02) | 12.90 (device-side chunks 7.6–19.3; one at the bound) | 89.2% / 87.0% |
| [boot J](HIF_TRANSPORT_ANALYSIS.md#boot-j-result-2026-10-25-1753-utc-transmit-above-12-with-zero-loss-the-retransmissions-were-part-of-the-cost) (17:53 UTC; same run; cross-session against boot I and boot H run 3) | 0282 v2, the queue bound its own option (64 frames, stop 56, wake 32): the configuration fix that released the mechanism; 156 stops and wakes (boot I 2,223), `high_water=56`, zero frames freed unsent, 406 of 406 samples at 0x4c status 0, 6 retransmissions in 14,550 segments, cwnd 58–95; the pipeline saturated (4 ÷ 2.864 ms = 1,397 frames/s, 16.2 Mbit/s predicted); no stall | floor (every transmit chunk byte-capped at 4 MiB in about 2.1 s): 15.02 (chunks 15.51–16.70) | floor (every receive chunk byte-capped): 17.26 (device-side chunks 18.54–19.62) | 84.9% / 86.5% |
| [boot K](HIF_TRANSPORT_ANALYSIS.md#boot-k-result-2026-10-25-1810-utc-transmit-27--on-the-rule-the-revert-row-fired-on-receive-confounded-by-the-harness) (18:10 UTC; adjacent to boot J; chunks 16 MiB or 3 s) | depth 8 (ledger 104) on boot J's tree: transmit steady at 20.9–21.2 on the rule (8 ÷ 4.26 ms = 1,877 frames/s, 21.7 predicted), 564 stops, nothing freed unsent, 4 retransmissions; two receive chunks on the device's 4 s bound (one the receive stall, one the drain after the laptop's close racing the bound); reverted to depth 4 by the rule, the attribution confounded by the harness | 19.87 (chunks 20.87–21.16, duration-bound) | 16.46 (device-side chunks 11.7–19.8; two at the device's bound) | 82.6% / 86.5% |
| [boot L](HIF_TRANSPORT_ANALYSIS.md#boot-l-result-2026-10-25-1837-utc-the-queue-never-stopped-during-receive-transmit-did-not-reproduce-the-acknowledgements-lag) (18:37 UTC; boot K's tree with no driver variable: the 0283 series, the 6 s device bound, the drain accounting; the first clean verdict) | zero stops and wakes in all 18 receive seconds and no receive gap: the receive stall and the acknowledgement split withdrawn; transmit the lower sample of the depth-8 band (wait 4.67 ms, one 203 ms transmit stall with 8 in flight) | 16.15 (chunks 15.50–18.72) | 18.83 (device-side chunks 16.80–21.18; TCP flow view 14.31–21.44) | 86.3% / 87.9% |
| [boot M](HIF_TRANSPORT_ANALYSIS.md#boot-m-result-2026-10-25-1853-utc-depth-12-on-the-model-the-depth-sweep-stops-a-receive-slowdown-the-silence-rule-cannot-see) (18:53 UTC; adjacent to boot L; one variable) | depth 12 (ledger 156): transmit on the model (wait 5.46 ms, 12 in flight, nothing freed unsent, 1 retransmission); the depth sweep stops (three-depth fit asymptote 35.7 Mbit/s); receive queue never stopped; one receive chunk slowed by the sender (one second at 218 KiB) without a silence | 21.87 (chunks 22.73–24.06) | 16.08 (device-side chunks 9.54–20.13) | 81.8% / 87.5% |
| [boot N](HIF_TRANSPORT_ANALYSIS.md#boot-n-result-2026-10-25-1910-utc-depth-16-is-flat-the-air-binds-depth-12-is-the-setting-the-receive-stream-read-on-both-ends) (19:10 UTC; adjacent to boot M; one variable) | depth 16 (ledger 208): transmit flat (1,927 frames/s against 1,900 at depth 12; wait 6.57 ms, 12.7 of 16 in flight): the air binds; depth 12 is the setting; receive stream on both ends: the application lags at moments without closing the window, one chunk's drain has two silences with the window open (link side); receipt false on the transmit direction's normal 141 close (rule fixed), data whole | 22.20 (chunks 23.24–23.77) | 17.94 (device-side chunks 15.39–20.97) | 82.4% / 86.6% |
| [boot O](HIF_TRANSPORT_ANALYSIS.md#boot-o-result-2026-10-25-1938-utc-the-access-point-accepted-wmm-the-four-way-handshake-timed-out-the-kernel-record-was-lost-0284-reverted) (19:38 UTC; void for the measurement) | 0284, WMM and QoS data at the legacy rate: the access point accepted WMM, the four-way handshake timed out with no EAPOL-Key received; the kernel record lost (the seal and the reviewed return refuse while the supplicant lives; the owner restarted the device); 0284 reverted | void | void | — |
| [boot P](HIF_TRANSPORT_ANALYSIS.md#boot-p-result-2026-10-25-2030-utc-the-access-point-sends-eapol-key-on-tid-6-the-gate-refused-it-at-descriptor-byte-9-the-evidence-survived) (20:30 UTC; void for the measurement) | 0284 v2, WMM on, records non-QoS, the EAPOL header traced: the AP's EAPOL-Key arrives as QoS on TID 6 and is refused at descriptor byte 9 (the TID); boot O's cause attributed; the failed join's kernel record survived (the leaf's exit, the seal, the reviewed return) | void | void | — |
| [boot Q](HIF_TRANSPORT_ANALYSIS.md#boot-q-result-2026-10-25-2043-utc-the-four-way-handshake-completes-under-wmm-dhcp-then-failed-the-access-points-qos-replies-refused-at-the-receive-check) (20:43 UTC; void for the measurement) | 0285-0287, records non-QoS: the four-way handshake completes under WMM (the AP's EAPOL-Key admitted on TID 6, ours accepted); DHCP then failed, four QoS replies refused at the CCMP receive check | void | void | — |
| [boot R](HIF_TRANSPORT_ANALYSIS.md#boot-r-result-2026-10-25-2055-utc-qos-receive-admission-works-and-dhcp-binds-two-named-blockers-and-the-measurements-ssh-never-connected) (20:55 UTC; void for the measurement) | 0288, 0289, records non-QoS: QoS receive admitted (`rx_qos=22`, none refused) and DHCP bound; 19 transmit TID refusals and 14 group LLC-mismatch frames (`0xc200`) named as blockers; the measurement's SSH never connected and the helper's crash left no graded receipt | void | void | — |
| [boot S](HIF_TRANSPORT_ANALYSIS.md#boot-s-result-2026-10-25-2132-utc-the-data-path-under-wmm-is-restored-and-measured-both-predictions-held-the-per-tid-replay-branch-opened) (21:32 UTC; first graded run under WMM) | 0290, 0291, records non-QoS: the data path under WMM restored; no transmit refusal (TIDs 0 and 3 used), the LLC-mismatch class discarded (802.3 length, not DHCP); 12 unicast frames refused at `pn=lower` (one counter across TIDs) | 17.17 | 17.64 | — |
| [boot T](HIF_TRANSPORT_ANALYSIS.md#boot-t-result-2026-10-25-2153-utc-per-tid-replay-counters-remove-every-receive-refusal-the-anti-replay-invariant-has-the-shape-ht-needs) (21:53 UTC; one variable, security-relevant) | 0292, records non-QoS: one CCMP replay counter per TID; no receive refusal at any field (`rx_refused=0`); transmit steady at 21.7–22.3 per chunk | 20.86 | 16.38 | — |
| [boot U](HIF_TRANSPORT_ANALYSIS.md#boot-u-result-2026-10-25-2209-utc-the-access-point-uses-ht-toward-this-station-at-the-top-mcs-and-our-receive-path-takes-it-unchanged) (22:09 UTC; one variable) | 0293, HT advertised, descriptor 0x4c: the AP sends HT (MCS7 ×27,538, MCS6 ×9,846) and nothing is refused; two transmit air losses (MPDU_ERROR); TCP retransmissions 32; receive now the binding limit | 19.2 | 13.72 | — |
| [boot V](HIF_TRANSPORT_ANALYSIS.md#boot-v-result-2026-10-25-2225-utc-batching-lifts-receive-modestly-and-transmit-with-it-ingest-is-still-bound-elsewhere-one-correct-replay-refusal) (22:25 UTC; one variable) | HIF_RX_BATCH re-admitted on boot U's tree (HT, 0x4c): receive good chunks 19.5–22.3 (+15 %), transmit 22.3–24.1; device 85.6 % idle; one refusal, a retried duplicate (`pn=equal`), correct | 22.01 | 18.22 | 81.1% / 85.6% |
| [boot W](HIF_TRANSPORT_ANALYSIS.md#boot-w-result-2026-10-25-2244-utc-the-firmware-sends-ht-mcs7-on-a-legacy-station-record-with-no-loss-but-transmit-hardly-moves-the-per-frame-cycle-binds-not-the-air) (22:44 UTC; one variable) | 0294, fixed rate 0x87 (HT MCS7): every sampled frame at MCS7, no loss; transmit +2.6 % because the retire cycle (5.2 ms over 12, about 433 µs a frame) binds, not the air; the interrupt is the next lever | 22.58 | 19.97 | 80.9% / 84.8% |
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
samples and the UDP counts are measured. Boot H's third run then named the
transmit limit: the driver's data queue frees frames unsent above its
drain rate (about 800–1,000 frames a second) with no backpressure, TCP
loses 2 % and holds a six-segment window; the transmit path's own loss
figure is 29 % at 9.5 Mbit/s offered and 54 % at 14 (echo requests, the
device tool's pacing declared), beside the receive path's zero loss at
30. Boot I added backpressure (§19) and boot J fixed its queue bound
(§20): transmit at 15.5–16.7 Mbit/s with zero loss, and the limit is now
the pipeline, depth ÷ credit-retire wait (4 ÷ 2.86 ms, 16.2 Mbit/s
predicted against 16.5 measured). Boot K (§21) at depth 8 held the
rule (21.7 predicted, 21.0 measured, the wait up to 4.26 ms) and lost
two receive chunks to the device's bound, which boot L showed was the
drain and the acknowledgement timing, not a receive stall. Boot M (§23)
is depth 12, once.

## Where throughput stands (2026-10-25, after boot L)

- **Transmit:** about 23–23.5 Mbit/s, the legacy wall: depth 12 (boot M,
  22.7–24.1 per chunk) and depth 16 (boot N, 23.2–23.8) carry the same
  frames a second, so the air binds and depth 12 is the setting; 19 ± 2 at
  depth 8 (boots K and L); nothing freed unsent.
- **Receive:** about 19 Mbit/s delivered over TCP on the device's own
  whole-window count (17–21 per chunk across boots L–N); the laptop's
  final-half figures are its write rate and are withdrawn as a receive
  measure (boot N's include 49.4, above the air); UDP carried 29
  Mbit/s at 2 % loss through the same path (boot D): the path's capacity
  of about 30 stands on the UDP probe alone.
- **The ceiling:** about 30 Mbit/s, the air at a fixed 54 Mbit/s (about
  386 µs a 1,518-byte frame with its overheads, about 2,590 frames a
  second); the depth model's asymptote (35.7) lies above it, so the air
  is the wall and transmit at 23 runs at 77 % of it. Above it only HT
  aggregation helps ([the HT project](HT_PROJECT_SCOPE.md)); the vendor's
  own driver reached 45.1 Mbit/s of transmit on the older protocol
  (vendor control 2).
- **Robustness:** the AP-loss gate passed as the access point's own
  inactivity disassociation; a controlled vanish-and-return test remains
  the one robustness item, independent of all of the above.

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
