# Current: §64's short-GI boot (AS: 0326 receive, 0327 transmit) approved and building, graded against AR

The fragment enables `CONFIG_MT6797_HT_SGI_RX` and
`CONFIG_MT6797_HT_SGI_TX` for that boot. The device is on Gemian
(`e1400235…`); boot2 holds AR's `936c5e65…`.

# Historical: 40 MHz done in both directions; transmit at a documented fixed MCS5 at 40 MHz (1.16× the MCS7 20 MHz control), receive 1.34×; the profile holds HT40, HT40 transmit, rate code 0x85, receive aggregation and the peek

Next on the roadmap: short GI and VHT; the transmit status read as a
power item; power management for the idle disconnect. The device is on
Gemian (`e1400235…`); boot2 holds AR's `936c5e65…`.

# Historical: boot AR graded; MCS5 at 40 MHz transmits 1.16× MCS7 at 20 MHz (15.01 against 12.96) with fewer retries; kept in the profile pending the owner

[Boot AR](HIF_TRANSPORT_ANALYSIS.md#boot-ar-result-2026-10-26-2223-utc-mcs5-at-40-mhz-transmits-116-the-mcs7-20-mhz-control-with-fewer-retries).
The device is on Gemian (`e1400235…`); boot2 holds AR's `936c5e65…`.

# Historical: §62's MCS5-at-40-MHz boot, AR (aa1e0436), staged on boot2 (936c5e65…); graded against AP's 12.96

Gemian (`de14e6c5…`) is shut down for the owner's boot2 selection.

# Historical: §62's MCS5-at-40-MHz image (boot AR) building, graded against AP; the fragment sets HT40_TX and rate code 0x85 for that boot

# Historical: boot AQ graded; the firmware's automatic rate stays at OFDM 6 Mbit/s on the HT record (TX 3.60 against 12.96); the fixed MCS7 restored, 0277 out of the series; §62's MCS5 at 40 MHz is the next transmit constant

[Boot AQ](HIF_TRANSPORT_ANALYSIS.md#boot-aq-result-2026-10-26-2201-utc-the-firmwares-automatic-rate-still-sits-at-ofdm-6-mbits-on-the-ht-record).
The device is on Gemian (`de14e6c5…`); boot2 holds AQ's `be5a5e82…`.

# Historical: §63's control (AP) graded: TX 12.96, attempts 93 % first; boot AQ (auto rate, 0c5232b9) staged on boot2 (be5a5e82…)

Gemian (`2434157c…`) is shut down for the owner's boot2 selection.

# Historical: §63's auto-rate pair approved: the control, boot AP (f73f4bf6, fixed MCS7 at 20 MHz), staged on boot2 (863c01f2…); the auto-rate image (0277 and rate code 0) building

0277 (the state-2 station-record update) is in the lifecycle series at
its canonical place, and the fragment sets
`CONFIG_MT6797_DATA_FIXED_RATE_CODE=0x0` for that boot. The fixed rate
stays the default unless §63 passes. Gemian (`61502d44…`) is shut down
for the owner's boot2 selection.

# Historical: §62 approved: the control (AP: HT40 receive, MCS7 at 20 MHz, 0325's attempts record) building, then HT40 transmit at a fixed MCS5 (AQ)

The device is on Gemian (`61502d44…`); boot2 holds AO's `0988dc59…`.

# Historical: boot AO graded; transmit at 40 MHz ran 0.54× the control (frames acknowledged, slower each); CONFIG_MT6797_HT40_TX off again, HT40 receive kept

[Boot AO](HIF_TRANSPORT_ANALYSIS.md#boot-ao-result-2026-10-26-2122-utc-transmit-at-40-mhz-runs-at-054-the-control-the-option-off-again).
The device is on Gemian (`61502d44…`); boot2 holds AO's `0988dc59…`.

# Historical: §61's control (AN) graded: TX 13.50, valid; boot AO (HT40 transmit, 7878a677) staged on boot2 (0988dc59…)

Gemian (`ee54858a…`) is shut down for the owner's boot2 selection.

# Historical: §61's control, boot AN (AM's image, no write), armed on boot2; the HT40 transmit image building (CONFIG_MT6797_HT40_TX on in the profile for that boot)

Gemian (`c580366e…`) is shut down for the owner's boot2 selection.

# Historical: §61's transmit-at-40-MHz pair approved: AM's image as the control (no write), then the HT40 transmit image (0324)

The device is on Gemian (`c580366e…`); boot2 holds AM's `7533e245…`.

# Historical: HT40 receive taken as local support (1.34× the same-session 20 MHz control); transmit at 40 MHz being written

The device is on Gemian (`c580366e…`); boot2 holds AM's `7533e245…`.

# Historical: boot AM graded; 40 MHz receive works (grant SCB, all frames at 40 MHz), RX 26.68 = 1.34× AL, short of 1.4×; the owner decides on keeping the option

[Boot AM](HIF_TRANSPORT_ANALYSIS.md#boot-am-result-2026-10-26-2103-utc-receive-at-40-mhz-works-receive-134-the-20-mhz-control-short-of-the-14-predicted).
The profile has `CONFIG_MT6797_HT40` on. The device is on Gemian
(`c580366e…`); boot2 holds AM's `7533e245…`.

# Historical: §60's HT40 receive boot, AM (build d587f977), staged on boot2 (7533e245…); read on receive against AL's 19.87

The composer admits exactly `CONFIG_MT6797_HT40` (absent→y) and no
tree change against AL's image. Gemian (`ee596b2e…`) is shut down for
the owner's boot2 selection.

# Historical: §60's control (boot AL) graded: RX 19.87 in band, TX 12.29 out of band; the HT40 boot (AM, d587f977) waits on the owner's reading rule

[Boot AL](HIF_TRANSPORT_ANALYSIS.md#boot-al-result-2026-10-26-2056-utc-the-20-mhz-control-receive-in-band-transmit-out-of-band).
The device is on Gemian (`ee596b2e…`); boot2 holds AL's `4a864d0f…`.

# Historical: §60's 20 MHz control, boot AL (35f9d3bf), staged on boot2 (4a864d0f…); the HT40 image building (CONFIG_MT6797_HT40 on in the profile for that boot)

Gemian (`f193bfb3…`) is shut down for the owner's boot2 selection. If
AL is in band, the HT40 boot follows.

# Historical: §60's HT40 receive pair approved: AL (20 MHz, receive aggregation and the peek) first, then the HT40 image (0323)

0323 is in the series behind `CONFIG_MT6797_HT40`, off in the profile
until the HT40 boot's build commit. The device is on Gemian
(`f193bfb3…`); boot2 holds AK's `4280a8e5…`.

# Historical: §58's control (boot AK) out of band (TX 11.45, RX 12.00, a software-frame burst); no comparison; AL built (35f9d3bf) and not staged; the confirmation repeats on another day, control first

[Boot AK](HIF_TRANSPORT_ANALYSIS.md#boot-ak-result-2026-10-26-1930-utc-the-control-is-out-of-band-no-comparison-al-not-staged).
The profile stands with receive aggregation and the peek on. The device
is on Gemian (`f193bfb3…`); boot2 holds AK's `4280a8e5…`.

# Historical: §58's good-air control, boot AK (build 00d07727: the peek on, receive aggregation off), staged on boot2 under the five-chunk harness; boot AL (35f9d3bf, aggregation on) building

Boot2 holds `4280a8e5…`, written over AJ2's `a7f2b300…` and read back
in full. Gemian (`a3746c2c…`) is shut down for the owner's boot2
selection. If the control is in band (TX ≥ 17.9, RX ≥ 15.4), AL
follows.

# Historical: §58's good-air confirmation building; the control (boot AK: the peek on, receive aggregation off) first, then boot AL (aggregation on)

The fragment turns `CONFIG_MT6797_RX_AMPDU` off for the control's
build only; the next commit turns it back on for AL and the profile.

# Historical: §58 predeclared: the good-air confirmation (control first, then aggregation on, five-chunk harness, nothing else changed); the transmit status read queued as a power item

Receive aggregation stands as +44 % on the same air (12.22 against
8.46, AH/AI), with transmit unchanged; the absolute figure in good air
is the next measurement. The software-frame bursts are a run-validity
signal. The device is on Gemian (`a3746c2c…`); boot2 holds AJ2's
`a7f2b300…`.

# Historical: boot AJ2 graded; the WHISR peek kept for its cost (HIF receive per pass −84 %, rates unchanged); CONFIG_MT6797_HIF_RX_PEEK and RX_AMPDU on in the profile, the cost line off

[Boot AJ2](HIF_TRANSPORT_ANALYSIS.md#boot-aj2-result-2026-10-26-1906-utc-the-peek-skips-97--of-passes-and-cuts-the-hif-receive-time-per-pass-by-84--the-rates-do-not-move-57s-fourth-row):
`all_pass`. 97 % of passes skipped the block, with no failure or
stall. TX was 14.54/14.67/8.19 (the last a 1 s chunk 23 KB short of
its cap, not explained). The device is on Gemian (`a3746c2c…`); boot2
holds `a7f2b300…`.

# Historical: the WHISR peek boot staged as AJ2 (§57; build 0ac0f8e0, boot2 a7f2b300…); watcher armed

Boot AJ's install wrote boot2 (`a7f2b300…`, over AF's `220a431b…`) and
read it back in full. Gemian's shutdown then hung: logind reported a
shutdown in progress while systemd stopped answering. The receipt
stayed incomplete, the harness refused the deployment, and the
owner's boot2 selection ran no measurement. The owner power-cycled the
device to Gemian (`0f5a7d5a…`). AJ2's install read the full partition,
skipped the write as matching, and recorded a confirmed shutdown.
Gemian is down for the owner's boot2 selection.

# Historical: the WHISR peek boot AJ (§57; 0322) approved; building

0322 reads WHISR alone before the enhanced status block and skips the
block on a zero word. The boot is AH's configuration on the same
lifecycle harness plus the peek; the per-phase cost line is on for this
boot only. The device is on Gemian (`7c247ff2…`); boot2 holds AF's
`220a431b…`.

# Historical: receive aggregation taken as local support (owner decision on the AH/AI pair); RX_AMPDU on in the profile, the cost line off; the WHISR peek next

Transmit was unchanged with receive aggregation active (15.18 against
14.90 Mbit/s on the same air), receive was 44 % higher, and AE's
window released every frame in order. The device is on Gemian
(`7c247ff2…`); boot2 holds AF's `220a431b…`.

# Historical: the short pair read on transmit (boots AH and AI): transmit 15.18 with receive aggregation against 14.90 without, on the same air; receive 12.22 against 8.46; the owner decides on taking receive aggregation

[Boot AI](HIF_TRANSPORT_ANALYSIS.md#boot-ai-result-2026-10-26-1732-utc-the-control-refuses-the-same-software-frames-and-transmits-the-same-aggregation-does-not-collapse-transmit-on-this-air):
both runs refused the same software-frame class, so the gate measured
the hour. AE's collapse did not recur. Both images ran at about
15 Mbit/s, just under §55's band. The device is on Gemian
(`7c247ff2…`); boot2 holds AF's `220a431b…`. The fragment still
enables both options for AE′.

# Historical: boot AH (AE′) discarded by §55's software-frame gate (268 refusals in the first data phase); transmit did not collapse, recorded only; the control not staged

[Boot AH](HIF_TRANSPORT_ANALYSIS.md#boot-ah-result-2026-10-26-1727-utc-ae-discarded-by-the-software-frame-gate-transmit-did-not-collapse):
`all_pass`. Three lifetimes ran TX 15.43/15.20/14.92 with no failed
send, a credit wait maximum ≤ 48 ms and a 15–20 % busy fraction. The
728-byte software-frame class has persisted since 16:35 UTC with
either image. A repeat needs the owner's word. The fragment still
enables both options for AE′. The device is on Gemian (`0dfd3785…`);
boot2 holds AE′'s `850638d0…`.

# Historical: boot AH, AE′ of the short pair (§55/§56), staged on boot2 under the lifecycle harness (build 93d2dc56)

Boot2 holds `850638d0…`, written over AF's `220a431b…` and read back in
full. The composer admits exactly `CONFIG_MT6797_RX_AMPDU` and
`CONFIG_MT6797_PASS_COST_RECORD` (absent→y) and no tree change. The plan
is three lifetimes, one chunk each, with no loss cycle. Gemian
(`e166aa6e…`) is shut down for the owner's boot2 selection. The
control (AF's image) follows.

# Historical: §55 predeclared (supersedes §54's bracket), follow-ups decided in §56: AE′ then the control under the lifecycle harness, gated on the software-frame class; awaiting approval to stage AE′

Three lifetimes, one 1 s / 1 MiB chunk per direction, no loss cycle.
A run whose first data phase logs more than 8 software-frame refusals
is discarded. AE′ (`93d2dc56`) is built; the control is AF's image
(`220a431b…`, on boot2 now). The device is on Gemian (`e166aa6e…`).

# Historical: §54's control 1 (boot AG) void, the device-side supplicant left 5.2 s into the data phase; the bracket is void; AE′ built, not staged

[Boot AG](HIF_TRANSPORT_ANALYSIS.md#boot-ag-result-2026-10-26-1635-utc-control-1-did-not-complete-the-bracket-is-void-under-54s-rule):
`session_exit=1` after one TX chunk (10.18 Mbit/s), with 148 refusals
of a new 728-byte software-frame shape. The fragment still enables
`CONFIG_MT6797_RX_AMPDU` and `CONFIG_MT6797_PASS_COST_RECORD` for AE′,
which is built (`93d2dc56`) and not staged. The device is on Gemian
(`e166aa6e…`); boot2 holds AF's `220a431b…`.

# Historical: §54's control 1 (boot AG, AF's image) armed on boot2; AE′ (RX_AMPDU and the per-phase cost line on, for that boot only) building

Control 1 needed no write (boot2 matched AF's `220a431b…`). Gemian
(`3910a501…`) is shut down for the owner's boot2 selection. The
fragment enables `CONFIG_MT6797_RX_AMPDU` and
`CONFIG_MT6797_PASS_COST_RECORD` for AE′ only. Control 2 is AF's image
written back.

# Historical: §54 predeclared (supersedes §53): control (AF's image) → AE′ (AE + per-phase cost) → control, same air; awaiting approval to run control 1

AE proved the window. The station record matches the vendor, and
receive aggregates did not starve the transmit pool (TX ran first,
with 141 receive packets). The triple is compared only if both
controls are in band (TX ≥ 17.9, RX ≥ 15.4). The device is on Gemian
(`3910a501…`); boot2 holds AF's `220a431b…`, which is control 1.

# Historical: the paired AE run (§53) predeclared: AE's image right after AF on the same air, graded against AF's 15.07/13.74; awaiting approval to stage

The boot2 write must reproduce AE's `25865da4…`. Only a transmit
collapse reverts 0321; only TX within 15 % of AF with RX at least
20 % above it enables the option. The device is on Gemian
(`3910a501…`); boot2 holds AF's `220a431b…`.

# Historical: boot AF graded; no collapse with the option off, but both directions below their bands; the air moved; the window is neither cleared nor implicated

[Boot AF](HIF_TRANSPORT_ANALYSIS.md#boot-af-result-2026-10-26-1528-utc-no-collapse-without-the-option-but-both-directions-below-their-band-no-row-matches-cleanly):
`all_pass`. TX 15.07 Mbit/s (4 failed sends, credit wait max 87 ms) and
RX 13.74, both about a quarter below their non-aggregated bands, with
the option off. AE's collapse did not recur, and no §52 row matches
cleanly. `CONFIG_MT6797_RX_AMPDU` stays off. The device is on Gemian
(`3910a501…`); boot2 holds `220a431b…`.

# Historical: boot AF, the separating run (§52), staged on boot2 (build db2b7733: AE's tree, RX_AMPDU off)

Boot2 holds `220a431b…`, written over AE's `25865da4…` and read back in
full. The composer admits one config change against AE's image
(`CONFIG_MT6797_RX_AMPDU` y→absent) and no tree change. Gemian
(`c78edf17…`) is shut down for the owner's boot2 selection.

# Historical: the separating run (§52) predeclared: AE's tree with RX_AMPDU off, on the same air; awaiting approval to build and stage

A transmit collapse here points at the air, and the window is cleared.
A normal transmit leaves AE's collapse unexplained, and AE's image
itself decides. The device is on Gemian (`c78edf17…`); boot2 holds
AE's `25865da4…`.

# Historical: boot AE graded; the reorder window delivers every frame in order (no pn=lower, RX chunks up to 25.6), but transmit collapsed; §51's fourth row; RX_AMPDU off in the profile

[Boot AE](HIF_TRANSPORT_ANALYSIS.md#boot-ae-result-2026-10-26-1416-utc-the-window-holds-and-releases-every-frame-in-order-but-transmit-collapses-51s-fourth-row):
`session_exit=1`. 2,377 frames held and released in order, no hole
skipped, no deadline fired, 3 refusals (none QoS). RX chunks 25.56,
22.79, 19.91 and 20.92; the fifth was cut by the scheduled disconnect.
TX fell to 0.018 Mbit/s with 30 failed transmit statuses and a 208 ms
credit wait, cause not established. The option is off again; the
owner decides between dropping 0320–0321 and a run that separates the
air from the window. The device is on Gemian (`c78edf17…`); boot2
holds `25865da4…`.

# Historical: boot AE, the receive-reorder boot (§51), staged on boot2 (build 63aba59d: 0320–0321)

Boot2 holds `25865da4…`, written over boot AD's `ffa6c506…` and read
back in full. The composer admits no config change and no tree change
against AD's image; the change is 0320–0321 in the kernel. Gemian
(`735dc1c6…`) is shut down for the owner's boot2 selection.

# Historical: the receive-reorder boot AE (§51; 0320–0321) predeclared and approved; building

0320 names a refused block-ack sub-frame by the gate that refused it
(`field=pn`). 0321 puts a per-TID reorder window with the vendor's
parameters ahead of the strict PN check: the ADDBA start, size 64+4, a
200 ms first-hole deadline checked each worker pass, and a flush on
ADDBA/DELBA, reset and close. Host test `tests/run-rx-reorder-test.py`.
`CONFIG_MT6797_RX_AMPDU` is on in the fragment for this boot only. The
device is on Gemian (`735dc1c6…`); boot2 holds `ffa6c506…`.

# Historical: boot AD graded; receive aggregation is established, but the firmware delivers retransmitted holes out of order and the strict PN check drops them; a driver reorder window is next; RX_AMPDU off in the profile

[Boot AD](HIF_TRANSPORT_ANALYSIS.md#boot-ad-result-2026-10-26-1333-utc-the-access-point-aggregates-toward-us-the-firmware-delivers-retransmitted-holes-out-of-order-50s-second-row):
`all_pass`. With `ucRxAmpdu=2` the firmware accepted ADDBA on TIDs 6,
0 and 5 (window 64), and all 17,594 QoS frames were sub-frames. 341
were refused, the logged ones all Retry sub-frames at `pn=lower`, and
RX fell to 8.74 (TX 21.45 unchanged). Next is a bounded per-TID
reorder window ahead of the PN check, with a timeout flush and a drop
counter, plus refusal naming by PN for sub-frames. The device is on
Gemian (`735dc1c6…`); boot2 holds `ffa6c506…`.

# Historical: boot AD, the receive-aggregation boot (§50), staged on boot2 (build f704d72a: 0317–0319, depth back to 12)

Boot2 holds `ffa6c506…`, written over boot AC's `e723ddfb…` and read
back in full. The composer admits two config changes (depth 24→12,
`CONFIG_MT6797_RX_AMPDU` absent→y) and no tree change. The work's
depth pins are back to 12. Gemian (`6a7f2948…`) is shut down for the
owner's boot2 selection.

# Historical: the receive-aggregation boot (§50; 0317–0319) predeclared, under review; mac80211's offloaded RX BA left out (802.3 delivery is not reordered)

0317 enables receive A-MPDU in the station record (`ucRxAmpdu=2`,
`ucRxBaSize=64`). 0318 records the firmware's `EVENT_ID_RX_ADDBA` and
`DELBA` instead of failing the lifetime. 0319 admits `(status &
0xffbf)==0` sub-frames into the pairwise check with the strict PN
unchanged; host test `tests/run-ccmp-ba-status-test.py`. All sit
behind `CONFIG_MT6797_RX_AMPDU`, set in the fragment for this boot.
mac80211's offloaded RX BA and `ampdu_action` are left out because RX
decap offload delivers 802.3 frames, which mac80211 does not reorder.
Under review, not built. The device is on Gemian (`6a7f2948…`); boot2
holds AC's image.

# Historical: boot AC graded; depth 24 fills and the rate does not move; the firmware's concurrency is the transmit limit; aggregation's firmware question is next (offline); depth back to 12

[Boot AC](HIF_TRANSPORT_ANALYSIS.md#boot-ac-result-2026-10-26-1252-utc-depth-24-fills-and-the-rate-does-not-move-the-firmwares-concurrency-is-the-transmit-limit):
`all_pass`, `inflight_max=24` with no fault, expiry or lost
completion. The credit wait went from 4.44 to 7.15 ms and TX was 18.5
(chunks 19.3–20.5), not higher than depth 12's 21.99. §48's second
row: aggregation is the only transmit lever, and its ADDBA question
goes to the RE VM. The profile's depth is back to 12; 0316's range
stays. The device is on Gemian (`6a7f2948…`); boot2 holds `e723ddfb…`.

# Historical: boot AC, the depth-24 boot (§48), staged on boot2 (build a1347edc: 0316, depth 24)

Boot2 holds `e723ddfb…`, written over boot AB's `8f481a70…` and read
back in full. The composer admits two config changes (depth 12→24, the
per-phase cost y→absent) and no tree change. The work's depth pins are
24 (compose, validator, bind, review, prepare plan). Gemian
(`fa9518ef…`) is shut down for the owner's boot2 selection.

# Historical: boot AB2's reading corrected (the pipeline holds its full depth; not yet "firmware-bound"); the depth-24 boot (§48, 0316) predeclared, under review

The transmit pipeline ran at its full depth of 12 (4.44 ms per frame
in the firmware, about 2,000 frames/s), with the host spending about
100 µs per frame and idling 40 %. That fits a depth cap as well as a
firmware concurrency limit, and depth 24 decides. 0316 raises the
range to 24 (ledger 312 of 468 pages). The verdict admits depth 24.
Receive's only lever is a cheaper or rarer status read. Under review,
not built. The device is on Gemian (`fa9518ef…`); boot2 holds
`8f481a70…`.

# Historical: boot AB2, the per-frame cost boot repeated on boot AB's image, staged (boot2 verified, not rewritten)

The installer read boot2's full partition as `8f481a70…`
(`skipped-already-matching`). The composer admits no change over boot
AB. Gemian (`189177e6…`) is shut down for the owner's boot2 selection.

# Historical: boot AB graded (the worker is idle 61 % of the wall; its busy time is HIF reads on empty passes); rates degraded, a repeat on the same image proposed

[Boot AB](HIF_TRANSPORT_ANALYSIS.md#boot-ab-result-2026-10-26-1215-utc-the-worker-is-idle-61--of-the-wall-its-busy-time-is-hif-reads-on-empty-passes-the-rates-were-degraded-so-it-is-repeated-before-a-decision):
`all_pass`. The worker was busy 18.4 s of the 46.9 s data phase. 74 %
of that was HIF register reads (status 13.7 µs per pass, the block read
20.5 µs, 95 % of them empty). Direct per-frame work was about 42 µs
submit, 15 µs completion and 41 µs delivery, a fifth of the ~0.5 ms
wall time per frame, so the time sits between passes. TX 10.13 and RX
14.13 are far below the band (5 air losses, 243 retransmissions), so
the split is repeated on the same image before a decision. The
fragment keeps 0315 on for that repeat. The device is on Gemian
(`189177e6…`); boot2 holds `8f481a70…`.

# Historical: boot AB, the per-frame cost boot (§47), staged on boot2 (build c412175c: 0315 on, the interrupt patches retired)

Boot2 holds `8f481a70…`, written over boot AA8's `c924d5c2…` and read
back in full. The composer admits two config changes
(`CONFIG_MT6797_HIF_RX_IRQ` y→absent, `CONFIG_MT6797_PASS_COST_RECORD`
absent→y) and one tree difference, the wifi child's `interrupts`
removed with 0298. Gemian (`e800691c…`) is shut down for the owner's
boot2 selection. After this boot the fragment turns the per-phase cost
off again.

# Historical: the interrupt patches retired (the line is closed); the per-frame cost boot (§47, 0315) predeclared, under review

The interrupt patches 0297–0303, 0306, 0308, 0309 and 0314 are
retired. 0304, 0305, 0307 and 0310–0313 are rebased onto 0296, and
their host tests pass. The per-frame arithmetic is corrected in §46:
about 0.5 ms of wall time per transmitted frame, against MCS7 air of
0.19 ms and the vendor's about 0.26 ms, so 0.2–0.25 ms is ours. The
legacy series ran at the same frame rate. 0315 records the worker's
cost per phase. The ROADMAP's stale HT and reconnect lines are fixed.
Under owner review, not built. The device is on Gemian (`e800691c…`);
boot2 holds `c924d5c2…`.

# Historical: boot AA8 graded; the interrupt line is closed for this configuration (the receive engine is the poll); the interrupt option is off again

[Boot AA8](HIF_TRANSPORT_ANALYSIS.md#boot-aa8-result-2026-10-26-1149-utc-the-vendors-order-changes-nothing-the-interrupt-line-is-closed-for-this-configuration):
`all_pass`. WHIER `0xffffff47` was written before the firmware download
(`0x00000000>0xffffff47`) and survived to the data-phase arm
(`whier=0xffffff47>0x7fffff07`). `taken=0`, pending 0/3,301
frame-bearing and 0/62,877 idle. §45's second row: no host-side
difference this series could name makes the line assert, so no further
boots go to it. The firmware's host mask stays an RE question. Data
path: TX 21.48 (chunks 22.5–22.9), RX 16.82, clean ledger. The device
is on Gemian (`e800691c…`); boot2 holds `c924d5c2…`.

# Historical: boot AA8, the WHIER-order boot (§45), staged on boot2 (build ff54fe80: 0314, the interrupt option on for this boot only)

Boot2 holds `c924d5c2…`, written over reconnect gate 2's `425c7c56…`
and read back in full. It was composed over that installed image: the
first attempt used AA7's candidate as the parent and was refused at
binding, before any device action. The composer and validator admit
exactly two changes: `CONFIG_MT6797_HIF_RX_IRQ` none→y and the drop
diagnostic 3→0. Gemian (`2a4ce560…`) is shut down for the owner's boot2
selection. After this boot the fragment turns the interrupt option off
again.

# Historical: reconnect gate 2 passed in session; the scan delay is stack policy; 0304 absorbs a lost association response on hardware; next: the WHIER-order boot (§45)

[Reconnect gate 2](LIFECYCLE_RESULT.md#reconnect-gate-2-result-2026-10-26-1113-utc--the-classifier-grades-in-session-the-scan-delay-is-the-stacks-0304-absorbs-a-lost-association-response-on-hardware):
`session_exit=0`, with the in-session classification at `cycles=3
loss_cycle=2 lifecycle_pass=true`. Each lifetime's first scan request
reached the hook 0/712/911 ms after the rearm and was admitted, so the
~0.9 s is the supplicant's or mac80211's. The dropped association
response of lifetime 3 was followed by mac80211's retry 104 ms later,
admitted by 0304, and the join completed. The ledger was clean. The
drop option is reverted to 0 in the fragment. The device is on Gemian
(`2a4ce560…`); boot2 holds `425c7c56…`.

# Historical: reconnect gate 2 staged on boot2 (build 1f8d19ae: the scan-request record, the association-response drop at lifetime 3, the plan-aware lifecycle classifier)

Boot2 holds `425c7c56…`, written over boot AA7's `e4783dff…` and read
back in full. The composer and validator admit exactly the drop option
(`CONFIG_MT6797_DIAG_DROP_ASSOC_RESP_LIFETIME` none→3). The offline
preparation passed first. Gemian (`a031c555…`) is shut down for the
owner's boot2 selection. The run takes about seven minutes. It passes
only with `session_exit=0` from the in-session grading.

# Historical: the reconnect gate passed (regraded with its pins; rejoin with keys 1.97 s after the loss); next: fix the lifecycle classifier's cycle default, then the WHIER-order boot (§45)

[Reconnect gate](LIFECYCLE_RESULT.md#reconnect-gate-result-2026-10-26-0225-utc--the-access-points-own-loss-on-the-wmmht-tree-rejoin-with-keys-197-s-after-the-loss-report-about-a-second-faster-than-the-ap-loss-gate):
the access point's own `reason=4` loss after 365 s, the rearm, and a
rejoin with both keys 1.97 s after the loss report (2.94 s in the
AP-loss gate). The ledger was clean, with no `-90` and
`window_505_508=0` in all three lifetimes. The session's exit 1 is the
in-session classifier running without the plan (two-cycle default),
also present in the AP-loss gate. Regraded with `cycles=3
loss_cycle=2`, every gate passes. 0304 was not exercised. The device is
on Gemian (`a031c555…`); boot2 holds `e4783dff…`.

# Historical: the reconnect gate (§44) staged on boot2 (boot AA7's image, verified, not rewritten); the WHIER-order boot (§45) after it

The reconnect gate runs on the AP-loss gate's lifecycle harness: three
lifetimes, one chunk each, with cycle 2 waiting for the access point's
own loss. It is pinned to boot AA7's candidate, composed through the
AA7 chain with no configuration change. Its record patterns were
checked against boot AA7's log, and every per-lifetime record matched
once. The plan's recorded depth is corrected to 12. The installer read
boot2 as `e4783dff…` (`skipped-already-matching`), and Gemian
(`fea5bf2d…`) is shut down for the owner's boot2 selection. The run
takes about seven minutes, most of it the idle wait for the loss.

# Historical: boot AA7 clean (0310 fixed the receive stop); the reconnect gate (§44) predeclared and being prepared; the WHIER-order boot (§45) after it

[Boot AA7](HIF_TRANSPORT_ANALYSIS.md#boot-aa7-result-2026-10-26-0210-utc-clean-0310s-window-was-reached-once-and-passed-the-receive-stop-is-closed):
`all_pass`, no `-90`, `failures=0` over 24,500 aggregates, and
`window_505_508=1`. A 505–508-byte aggregate (fatal before 0310) moved
as one 512-byte block. `max_bytes=25,600`. Rates were TX 17.94 (chunks
1–2 slow, 444 TCP retransmissions, no air loss) and RX 15.42 (the dips
were sender-side). Neither is attributed to the change. The join was
validated a third time. The interrupt option is off; its open leads
are the WHIER initialization order, the AHB variant's CCCR `IENx` and
the firmware host mask. The device is on Gemian (`fea5bf2d…`); boot2
holds `e4783dff…`.

# Historical: boot AA7 (the DMA receive rounding, the refused-transfer record, the interrupt option off) staged on boot2

[Boot AA6](HIF_TRANSPORT_ANALYSIS.md#boot-aa6-result-2026-10-26-0152-utc-void-again-on--90-in-the-receive-batch-the-cause-is-the-transfer-size-rounding-not-the-buffer):
transmit ran five chunks (22.8–21.0), then the lifetime stopped at the
receive direction's start with -90 again. The cause is
`mt6797_hif_transfer_size()` choosing the mode before the receive's
eight-byte rounding: 505–508 bytes became a 512-count byte command. The
host sweep shows exactly 505–508 refused. 0310 rounds first (host test
`tests/run-transfer-size-test.py`). The probe at one read in eight
restored 12,763 passes/s. Owner: the interrupt question closes on
what it excludes (the mask, wrapper, order, read-clear and SPI). The
option is off in the profile and the receive stays the poll. The
enable is open, with three leads:

- the AHB variant's `sdio_open()` (built for MT6797, per the pinned
  Makefile) sets CCCR `IENx`, which our driver never writes;
- the vendor writes WHIER at adapter initialization, before the
  firmware starts, where we write it about 4 s after;
- the firmware keeps its own host-interrupt mask.

The vendor's separate DMA interrupt is compiled off
(`CONF_HIF_DMA_INT 0`). Boot AA7 (§43) is AA6 plus
0310 and 0311 with the option off. It is staged: build `7eeb2c26`,
boot2 `e4783dff…` over `ccb73bae…`, written and read back in full. The
composer and validator admit exactly one config change,
`CONFIG_MT6797_HIF_RX_IRQ` y→unset. Gemian (`34cabf67…`) is shut down
for the owner's boot2 selection. The device is on Gemian
(`34cabf67…`); boot2 holds `ccb73bae…`.

# Historical: boot AA6 (full WHIER 0x7fffff07, the probe 1 in 8, the batch bound) staged on boot2

The direct aperture is the HIF command interface, so the Gemian WHIER
and WHCR numbers are transaction leftovers. Those reads restarted the
device twice, and there are no further Gemian register reads. No WHISR
bit at or above 8 appears in any session, so 0306's `0x1e00` cannot
fire. 0308 arms the vendor default less ABNORMAL and firmware-assert
(`0x7fffff07`; the value first given, `0xbfffff07`, withheld bit 30
instead of 31). 0309 samples the line before one read in eight and
logs WHISR at the first take and at disarm. 0307 bounds the receive
batch, and 0304–0305 are validated.

Boot AA6 is staged: build `4496c9b6`, boot2 `ccb73bae…` over
`345753c1…`, written and read back in full. The first stage attempt was
refused before any device action: the preceding Gemian boot had
changed to `88a02dda…` after the aperture-read restarts. It was
re-derived with that pin. Gemian is shut down for the owner's boot2
selection.

# Historical: boot AA5 (WHIER 0x1e00, the two-point probe, the join changes) staged on boot2

The Gemian reading (HIF §40): WHIER `0x00001e00` (the firmware's
software interrupts 9–12), WHLPCR `0x101`, the wrapper mask 0, and SPI
283 level-low live at about 70 interrupts a second. Our `0x7` (the done
bits) could not drive the line. Boot AA4's `pending=0/30980` is
uninformative and its line conclusion is withdrawn; its data path
stands (TX 22.58, RX 20.46).

Boot AA5 (§41) is predeclared: 0306 arms `0x1e00`, and 0303 is reworked
to sample before and after the block read. 0304–0305 carry the join
retry and the early M1. All of them are in the lifecycle profile.

Boot AA5 is staged: build `3a2d28b8`, boot2 `345753c1…` over
`fc08179f…`, written and read back in full. Gemian (`129a25b3…`) is
shut down for the owner's boot2 selection.

# Historical: boot AA4 (the HIF line's pending state at the controller, 0302–0303) staged on boot2; 0304–0305 committed, outside the profile until after AA4

[Boot AA3](HIF_TRANSPORT_ANALYSIS.md#boot-aa3-result-2026-10-26-0049-utc-the-wrapper-was-never-masked-the-line-stays-silent-38s-second-row):
boot AA2's image re-run (boot2 verified, `skipped-already-matching`);
`all_pass`. The wrapper mask read 0 before arm. `taken=0` held with
WHIER 0x7 and INT_EN set. The read-clear inference is withdrawn: the
enabled sources are read-only. RX 20.5 and TX 22.6 aggregate are the
measured design ceiling without aggregation. The first EAPOL-Key
stalled 996 ms again.

Under review, not committed to a build:

- 0302: the disarm leaves the wrapper mask alone, and `whier=` is
  printed on disarm.
- 0303: the pending-state probe (boot AA4, §39).
- 0304: two authentication and association attempts (host test
  `tests/run-join-attempt-test.py`).
- 0305: the first EAPOL-Key on tag 1 from the accepted association on
  (host test `tests/run-early-m1-test.py`).

The lifecycle profile carries 0302–0303 only. 0304–0305 join it after
AA4, then the reconnect gate.

Boot AA4 (build `0c803c25`, boot2 `fc08179f…`, predecessor `561e2025…`,
written and read back in full) is staged. Gemian (`cfbcce3f…`) is shut
down for the owner's boot2 selection.

# Historical: boot AA2 void; boot AA3 (§38 re-run on the unchanged image) predeclared and being staged; two join defects named, to be fixed before the reconnect gate

[Boot AA2](HIF_TRANSPORT_ANALYSIS.md#boot-aa2-result-2026-10-26-0038-utc-void-the-join-failed-before-the-data-phase-the-interrupt-never-reached-its-arming-point):
authentication completed and the association request was acknowledged,
but no association response was received; the access point's first
EAPOL-Key was refused at predicate=association and the join stopped
(-95, branch 1) before the data phase. First such failure in the series;
the interrupt was attached masked and never armed, so 0301 is not
involved. Owner: the -95 is the driver's, not the air's
(mgd_prepare_tx admits one attempt per join subtype; mac80211's retry
failed it); a bounded retry and an earlier M1 admission (the 1 s EAPOL
stall on half of connects) follow as separate patches with host tests,
before the reconnect gate. Boot AA3 re-runs §38 on the same image
(installer verifies boot2); the slow-poll boot is renumbered AA4. The
device is on Gemian (`27ee846e…`).

# Historical: boot AA's interrupt never fired (taken=0); boot AA2 (boot AA plus 0301, the wrapper line mask unmasked) staged on boot2

[Boot AA](HIF_TRANSPORT_ANALYSIS.md#boot-aa-result-2026-10-26-0028-utc-the-interrupt-arms-cleanly-and-never-fires-38s-taken--0-row-stopped-there):
attached as irq 218; armed `whier=0x00000000>0x00000007
whlpcr=0x00000100>0x00000101` status 0; disarmed status 0; `taken=0
rearmed=0` across a clean 44.3 s data phase. Nothing else moved (no
refusal, ledger exact, about 1,191 frames/s, TX 22.16, RX 16.22). The
candidates (the poll read-clearing WHISR first, a further CONSYS or
infra gate, the line or its polarity) wait for a later bounded look;
boot AB depends on the line. Owner: the missing register is the vendor's
wrapper line mask at 0x200 (`sdio.h` __enable_irq/__disable_irq); 0301
writes and records it (mask=) in the arm and disarm paths; boot AA2 is
boot AA plus 0301. If taken stays 0, the poll's read-clear is the cause
and boot AB's slow poll is next. The composer and validator admit no
config change and an identical tree (the parent, boot AA, already
carries the 0298 interrupt). Boot AA2 is staged on boot2 at 82717df4
(image 561e2025…, predecessor 6f24c213…), written and read back from
Gemian (boot `9a690b5a…`), device command 4,074 of 4,096 bytes,
preflight passed, the device shut down cleanly; the owner selects boot2.

# Historical: boot AA (the WLAN HIF interrupt as a wake source; tests the line) staged on boot2

[Boot Z](HIF_TRANSPORT_ANALYSIS.md#boot-z-result-2026-10-25-2351-utc-the-declaration-is-harmless-at-depth-one-the-aggregate-is-what-goes-undelivered-the-lifetime-then-stopped-on-missing-transmit-reports):
depth one under boot Y's declaration delivered (five transmit chunks at
9.4-10.4, TCP healthy, about 750 frames/s, zero refusals): the fault is
the aggregate or the agreement, not the declaration. 56 transmit reports
never arrived; that stalled the depth-one pipeline and the lifetime
stopped mid-receive (join stopped, branch 4): not a harness truncation.
Ceiling without aggregation about 1,950 frames/s, 23.6 Mbit/s. TX_AMPDU
leaves the fragment and the depth returns to 12. Aggregation waits on
one bounded firmware question; the receive interrupt is the next boot.
[§37](HIF_TRANSPORT_ANALYSIS.md#37-the-receive-interrupt-scoped-2026-10-25-the-vendors-shape-ours-and-the-smallest-bridge):
the vendor's WLAN HIF line is SPI 283 on `wifi@180f0000` (not in our DT;
our consys line SPI 130 is WMT/BTIF); its ISR touches no register,
masks the line and wakes the thread, which reads the status block and
re-arms (`WHLPCR` INT_EN_SET, `WHIER_DEFAULT`). Our pump sleeps 4-20 ms
when idle or stalled. [§38](HIF_TRANSPORT_ANALYSIS.md#38-boot-aa-predeclared-2026-10-25-to-be-implemented-after-review-the-receive-interrupt-as-a-wake-source):
the interrupt as a wake source with the poll kept as the safety net,
behind `MT6797_HIF_RX_IRQ`. Owner, 2026-10-25: implemented as 0297-0300
and approved; the fragment sets `CONFIG_MT6797_HIF_RX_IRQ=y`. Owner,
before the build: WHIER arms only TX, RX0 and RX1 done (0x00000007);
boot AA tests the line, not the throughput (the poll is unchanged); the
throughput step is boot AB (§39, the receive poll on a wake plus a 10 ms
fallback). The first package carried `TX_AMPDU=y` by default (the
withdrawal had deleted the fragment line) and was not staged; the
fragment now disables it explicitly. The composer admits exactly one
declared tree difference (0298's wifi interrupt). Boot AA is staged on
boot2 at 348be4c6 (image 6f24c213…, predecessor f775c477…), written and
read back from Gemian (boot `3885482b…`), device command 4,074 of 4,096
bytes, preflight passed, the device shut down cleanly; the owner selects
boot2.

# Historical: boot Y's firmware transmit aggregation regressed; the declaration checked correct (PHY 0x18 = OFDM|HT at the pin; ampdu=0x1b is the peer's); boot Z (aggregation declared, depth one) staged on boot2

[Boot Y](HIF_TRANSPORT_ANALYSIS.md#boot-y-result-2026-10-25-2335-utc-firmware-transmit-aggregation-reports-every-frame-delivered-while-tcp-sees-loss-the-stream-collapsed-35s-stop-row):
the record took (tx_ampdu=2, tx_ba=64, the peer's ampdu=0x1b), then the
first transmit chunk delivered 8.28 Mbit/s with the device's TCP at cwnd
1 and the SSH control session died; every transmit status was 0 at
0x0087 and every credit returned. Transmit status and delivery disagree
under aggregation; causes not distinguished (the AP's reorder buffer
and the firmware's sequence handling, the fixed-rate descriptor in an
A-MPDU, TID 3). `CONFIG_MT6797_TX_AMPDU` leaves the fragment; 0296 stays
behind its option. Owner: a regression (57 frames/s against about
1,200, both directions starved with the association intact: an
aggregation state the peer does not share). The vendor source shows no
host step missing (no ADDBA acceptance with block-ack in the firmware;
EVENT_ID_RX_ADDBA is receive-only and none was emitted; ADDBA_REJECT is
global and never sent). Aggregation boots now carry a precondition (the
link carries the previous volume) and a stop rule (transmit frames/s
below half: stop, revert, do not grade). A transmit block-ack session
record has no host input in the source. Next in the owner's queue:
submission batching. Owner's two suspects checked: `sta_phy`/`bss_phy`
0x18 is OFDM|HT in the pinned bit assignment (ERP-P2P makes OFDM bit 3),
and ampdu=0x1b is the access point's own A-MPDU parameters. [§36](HIF_TRANSPORT_ANALYSIS.md#36-boot-z-predeclared-2026-10-25-aggregation-declared-as-in-boot-y-one-frame-in-flight-the-discriminator):
`TX_AMPDU=y` with `CCMP_TX_DEPTH=1` separates "the declaration breaks
framing" from "the aggregate breaks delivery"; stop rule below about 275
frames/s. Owner, 2026-10-25: approved as predeclared. The compose,
validator, bind and review records are pinned to depth 1 (13 ledger
pages) and the allowances admit exactly the depth change. Boot Z is
staged on boot2 at f62f9e45 (image f775c477…, predecessor 2d09ef9d…),
written and read back from Gemian (boot `84fe607a…`), device command
4,074 of 4,096 bytes, preflight passed, the device shut down cleanly; the
owner selects boot2.

# Historical: boot X's declaration compatible; boot Y (transmit aggregation in the firmware, read as service time) staged on boot2

[Boot X](HIF_TRANSPORT_ANALYSIS.md#boot-x-result-2026-10-25-2313-utc-the-records-qos-and-ht-declaration-is-compatible-nothing-the-declaration-could-move-moved):
`records_qos=1`, `join HT records: declared=1 sta_phy=0x18 mcs=0xff
cap=0x09ef bss_phy=0x18 protect=2 op1=0x07 op2=0x0006`; the ledger
whole with three air losses, every credit returned, no refusal, rate
still 0x0087; TX 21.27, RX 18.94, within the spread. The access point
runs a 40 MHz BSS (secondary below); we declare HT20. Next: block-ack in
the station record with several frames per aggregate window, read as
wait_avg / depth (0.46 ms here). Owner: boot X passed its purpose and
missed its criterion on a second-half loss episode (with three status-3
frames); the declaration stays, named as the first thing to split if
block-ack disappoints. [§35](HIF_TRANSPORT_ANALYSIS.md#35-boot-y-predeclared-2026-10-25-transmit-aggregation-in-the-firmware-read-as-service-time):
0296 `TX_AMPDU=y` (ucTxAmpdu enabled, ucTxBaSize 64, the peer's
ucAmpduParam; receive A-MPDU still disabled). The vendor's submission
batching (one transfer per queue, `CFG_SDIO_TX_AGG`) is read and is the
next lever if the service time stays near 0.46 ms. Owner, 2026-10-25:
approved as predeclared. The composer's and validator's allowances admit
exactly TX_AMPDU. Boot Y is staged on boot2 at 70df93c9 (image
2d09ef9d…, predecessor 9b74c622…), written and read back from Gemian
(boot `0c2f26a4…`), device command 4,074 of 4,096 bytes, preflight
passed, the device shut down cleanly; the owner selects boot2.

# Historical: boot W sends HT MCS7 with no loss and the per-frame service time binds; boot X (the records' QoS and HT declaration, a no-change compatibility step) staged on boot2

[Boot W](HIF_TRANSPORT_ANALYSIS.md#boot-w-result-2026-10-25-2244-utc-the-firmware-sends-ht-mcs7-on-a-legacy-station-record-with-no-loss-but-transmit-hardly-moves-the-per-frame-cycle-binds-not-the-air):
clean verdict; every sampled frame at 0x0087, status 0; TX 22.58 (chunks
23.5-24.2), RX 19.97; credit-retire wait unchanged at 5.2 ms over 12
(about 433 us a frame against 189 us of air), device 85 % idle, 96 % of
block reads empty. Owner: 40 MHz and short GI retired (air-only, low
value); the next project is firmware aggregation (the station record's
QoS/HT/A-MPDU fields; the descriptor's BA bit is already clear), read as
service time per frame (below about 0.2 ms amortises; near 0.43 the cost
is per MPDU). The shared-worker and shared-medium couplings are recorded.
The fixed MCS7 stays. [§34](HIF_TRANSPORT_ANALYSIS.md#34-boot-x-predeclared-2026-10-25-the-records-qos-and-ht-declaration-a-compatibility-step-whose-success-is-that-nothing-moves):
`WMM_QOS_RECORDS=y` and 0295 `HT_RECORDS=y` declare ucIsQBSS/ucIsQoS and
the AP's HT capability and operation in the post-association records,
block-ack still disabled; success is that nothing moves, read on the TC
mapping (credits returning on TC1). Then the block-ack boot. Owner,
2026-10-25: approved as predeclared. The composer's and validator's
allowances admit exactly WMM_QOS_RECORDS and HT_RECORDS. Boot X is staged
on boot2 at a34cff21 (image 9b74c622…, predecessor 0b0e2e01…), written and
read back from Gemian (boot `dd7fd353…`), device command 4,074 of 4,096
bytes, preflight passed, the device shut down cleanly; the owner selects
boot2.
Nothing is staged; the device is on Gemian (`dd7fd353…`).

# Historical: boot V's receive batching paid (RX 18.22, TX 22.01) and stays admitted; boot W (fixed HT MCS7 on transmit) staged on boot2

[Boot V](HIF_TRANSPORT_ANALYSIS.md#boot-v-result-2026-10-25-2225-utc-batching-lifts-receive-modestly-and-transmit-with-it-ingest-is-still-bound-elsewhere-one-correct-replay-refusal):
batching on with no failure (20,994 aggregates, up to 16); receive good
chunks 19.5-22.3 against boot U's 18.1-18.6, not toward 25-30; device
86 % idle during receive; transmit 22.3-24.1 per chunk with 4
retransmissions. One refusal, a retried duplicate (`pn=equal`, Retry)
refused correctly. Owner: 0268 stays admitted; the earlier "neutral" was
a condition (the acknowledgement clock), and transmit and receive share
one worker. [§33](HIF_TRANSPORT_ANALYSIS.md#33-boot-w-predeclared-2026-10-25-the-fixed-ht-mcs7-on-transmit-one-constant):
`DATA_FIXED_RATE_CODE=0x87` with 0294 widening the option's range;
prediction toward 25 on transmit (189 µs per frame, long GI), slightly
more air loss. Then one decision: the interrupt or the air-rate levers.
Owner, 2026-10-25: approved as predeclared. The composer's and
validator's allowances admit exactly `DATA_FIXED_RATE_CODE` 0x4c → 0x87.
Boot W is staged on boot2 at 43f4fa20 (image 0b0e2e01…, predecessor
c06ff1ae…), written and read back from Gemian (boot `885a03ed…`), device
command 4,074 of 4,096 bytes, preflight passed, the device shut down
cleanly; the owner selects boot2.

# Historical: boot U shows the access point uses HT toward this station at the top MCS, received with no refusal; boot V (receive batching re-admitted) staged on boot2

[Boot U](HIF_TRANSPORT_ANALYSIS.md#boot-u-result-2026-10-25-2209-utc-the-access-point-uses-ht-toward-this-station-at-the-top-mcs-and-our-receive-path-takes-it-unchanged):
HT negotiated; downlink MCS7 ×27,538, MCS6 ×9,846; zero refusals on
38,106 QoS frames. The verdict failed only on two transmit air losses
(status 3, MPDU_ERROR) folded into the ownership gate; the gate is now
split (`tx_delivery`, an air-loss warning when every failure is status
3). TX 19.2, RX 13.72, TCP retransmissions 32: not attributed from one
run. Receive ingest is the binding limit (the AP offers 65-72 Mbit/s of
air, we take 18).
[§32](HIF_TRANSPORT_ANALYSIS.md#32-boot-v-predeclared-2026-10-25-receive-batching-re-admitted-on-boot-us-tree):
`CONFIG_MT6797_HIF_RX_BATCH=y` on boot U's tree; then boot W, the fixed
MCS7 descriptor (0x87). Owner, 2026-10-25: approved as predeclared.
The composer's and validator's allowances admit exactly
`CONFIG_MT6797_HIF_RX_BATCH=y`. Boot V is staged on boot2 at 1246fc2d
(image c06ff1ae…, predecessor a227cbd5…), written and read back from
Gemian (boot `5356f352…`), device command 4,074 of 4,096 bytes,
preflight passed, the device shut down cleanly; the owner selects boot2.

# Historical: boot T's per-TID replay counters removed every receive refusal (all_pass); boot U (HT capability advertised, descriptor unchanged) staged on boot2

[Boot T](HIF_TRANSPORT_ANALYSIS.md#boot-t-result-2026-10-25-2153-utc-per-tid-replay-counters-remove-every-receive-refusal-the-anti-replay-invariant-has-the-shape-ht-needs):
`rx_refused=0 rx_refused_qos=0`, the anti-replay invariant per TID and
strict; TX 20.86 (every chunk 21.7-22.3), RX 16.38 (one chunk-2 dip
that slowed at the sender); ledger exact; the probe's UDP legs retired.
Next, per the owner's sequence: HT capability advertised with WMM, the
fixed 0x4c descriptor and records non-QoS kept, the receive rate record
read for HT modes and the receive refusals watched for a change of
shape. The PN drops fell in boot S's receive window, not its transmit
window, so they were not boot S's transmit dip. The fixed-rate trade is
recorded: nothing is refused, yet TCP retransmits on channel dips at a
fixed 54 Mbit/s. [§31](HIF_TRANSPORT_ANALYSIS.md#31-boot-u-predeclared-2026-10-25-ht-capability-advertised-the-descriptor-unchanged):
0293 advertises HT20 MCS 0-7 and admits exactly that element and the
HT20 width; descriptor, records and block-ack refusal unchanged. Owner,
2026-10-25: approved as predeclared. The composer's and the candidate
validator's configuration allowances, inherited as empty, now admit
exactly `CONFIG_MT6797_HT_CAPABILITY=y`. Boot U is staged on boot2 at
625c1eb3 (image a227cbd5…, predecessor c7f650a8…), written and read
back from Gemian (boot `bafaa65c…`), device command 4,074 of 4,096
bytes, preflight passed, the device shut down cleanly; the owner
selects boot2.

# Historical: boot S restored and measured the data path under WMM (all_pass, WMM cost nothing measurable); boot T (one CCMP replay counter per TID, security-relevant) staged on boot2

[Boot S](HIF_TRANSPORT_ANALYSIS.md#boot-s-result-2026-10-25-2132-utc-the-data-path-under-wmm-is-restored-and-measured-both-predictions-held-the-per-tid-replay-branch-opened):
the first graded receipt of the HT chain: TX 17.17, RX 17.64 Mbit/s.
The transmit variance is one TCP congestion episode (chunk 3: cwnd 84,
ssthresh 64; retransmissions 1 to 7; nothing dropped), so the QoS
framing is not a suspect. TID 3 carried 203 frames (boot R's SSH
failure explained), and the LLC-mismatch frames are 802.3 length frames.
The 12 `pn=lower` refusals are a per-TID packet-number mismatch.
[§30](HIF_TRANSPORT_ANALYSIS.md#30-boot-t-predeclared-2026-10-25-one-ccmp-replay-counter-per-tid-a-security-relevant-change):
0292 keeps eight strict replay counters per context, seeded per TID from
mac80211, and names the TID and counter of each refusal. The probe's
dead UDP trigger and failing echo legs are retired. Then HT, the cheap
route (fixed rate, no aggregation) first. Owner, 2026-10-25: approved
as predeclared. Boot T is staged on boot2 at 42307a6a (image
c7f650a8…, predecessor f7cdcf2f…), written and read back from Gemian
(boot `566c4f7e…`), device command 4,074 of 4,096 bytes, preflight
passed, the device shut down cleanly; the owner selects boot2.

# Historical: boot S restored and measured the data path under WMM (all_pass); 12 unicast frames refused at pn=lower opened the per-TID replay counter

[Boot S](HIF_TRANSPORT_ANALYSIS.md#boot-s-result-2026-10-25-2132-utc-the-data-path-under-wmm-is-restored-and-measured-both-predictions-held-the-per-tid-replay-branch-opened):
the first graded receipt of the HT chain (`all_pass=True`,
`verdict_failed=[]`): TX 17.17, RX 17.64 Mbit/s at the legacy rate.
No transmit refusal (`tx_tid=48581/0/0/203/...`: TID 3 is the SSH
control session's AF21); the LLC-mismatch frames carry an 802.3 length
(`0x002e`), not DHCP. Open: 12 unicast QoS frames (TID 0 and TID 5)
refused at `field=pn pn=lower`, the one pairwise counter across TIDs;
the next change is a per-TID pairwise replay counter, named as
security-relevant, its own boot, before the records' QoS declaration.
Transmit is below boot M's 22.9 with the firmware side unchanged
(retire wait 5.37 ms, fewer queue stops): recorded, cause not measured.
Nothing is staged; the device is on Gemian (`566c4f7e…`).

# Historical: boot R admitted QoS data on receive and DHCP bound; two named blockers and the seal gap fixed; boot S (the data path under WMM) staged on boot2

[Boot R](HIF_TRANSPORT_ANALYSIS.md#boot-r-result-2026-10-25-2055-utc-qos-receive-admission-works-and-dhcp-binds-two-named-blockers-and-the-measurements-ssh-never-connected):
`rx_qos=22 rx_refused_qos=0`, DHCP bound, pings answered; the
measurement's SSH never connected. Blockers: 19 transmit frames refused
at the TID admission (0284 allowed only QoS control 0, unnamed), and 14
group frames refused at status `0xc200` (`RX_STATUS_LLC_MIS`, the
class `data-rx.h` already decodes; by size and the earlier type word,
802.2 LLC frames rather than DHCP; the vendor drops them). The seal gap
was the laptop helper's crash on a measurement that never ran (the
naming loop added for boot N) plus an owner check that cannot pass
when SSH never connects; both fixed on the host (`unreached_stream.py`, the total
loop). [§29](HIF_TRANSPORT_ANALYSIS.md#29-boot-s-predeclared-2026-10-25-the-data-path-under-wmm-two-admissions-every-refusal-named):
0290 discards the LLC-mismatch class as the vendor does, named with
its type word, and names status bits in every refusal; 0291 admits QoS
transmit on TIDs 0-7 (descriptor TID 0, TC1, the vendor's non-QoS
template), counted per TID, each refusal named by TID and access
category. No replay check is relaxed. Owner, 2026-10-25: approved as
predeclared, LLC_MIS discarded and named. Boot S is staged on boot2 at
349f8165 (image f7cdcf2f…, predecessor 45c802cd…), written and read
back from Gemian (boot `bcd86356…`), preflight passed, the device shut
down cleanly; the owner selects boot2.

# Historical: boot Q completed the four-way handshake under WMM; DHCP then failed, the access point's QoS replies refused at the CCMP receive check; the next change records that check's refusals

[Boot Q](HIF_TRANSPORT_ANALYSIS.md#boot-q-result-2026-10-25-2043-utc-the-four-way-handshake-completes-under-wmm-dhcp-then-failed-the-access-points-qos-replies-refused-at-the-receive-check):
the AP's EAPOL-Key admitted on TID 6, our messages 2 and 4 accepted,
keys installed, connected; the association and ledger unchanged. Then
four DHCP discovers went out as QoS data and four QoS frames came back
and were refused at the post-key receive check (`rx_qos=0`,
`rx_refused_qos=4`), which fixes descriptor byte 9 at `0x40` and the QoS
control at 0. That check records no per-frame refusal, so its field is
inferred, not named: the next change records it (logging only), then the
data-path counterpart of 0286. Owner, 2026-10-25: boot R is that
admission as one variable (0289, any TID with a consistent QoS control,
both checks), with 0288 naming every remaining refusal;
[§28](HIF_TRANSPORT_ANALYSIS.md#28-boot-r-predeclared-2026-10-25-qos-data-admitted-at-the-receive-checks-one-variable).
The records' QoS declaration moves to boot S.
Boot R is staged on boot2 at 1af78599 (image 45c802cd…, predecessor
13703a41…), written and read back from Gemian (boot `8afdfec0…`),
preflight passed, the device shut down cleanly; the owner selects boot2.

# Historical: boot P named the handshake's obstacle (the AP's EAPOL-Key on TID 6, refused at descriptor byte 9) and its evidence survived; boot Q (0286 admit, 0287 TID 6 uplink, 0285 refusal record; records non-QoS) is staged on boot2 at 65679190 (image 13703a41…, predecessor 48bec39b…); the HT-chain measurement freeze starts with it

[Boot P](HIF_TRANSPORT_ANALYSIS.md#boot-p-result-2026-10-25-2030-utc-the-access-point-sends-eapol-key-on-tid-6-the-gate-refused-it-at-descriptor-byte-9-the-evidence-survived):
four EAPOL-Key frames arrived as QoS data on TID 6 (translated,
EtherType 0x888e) and were refused at descriptor byte 9, which carries
the TID; boot O's silent handshake was the same refusal. The failed
join's kernel record reached the laptop through the leaf's exit, the
seal and the session's reviewed return.
[§27](HIF_TRANSPORT_ANALYSIS.md#27-boot-q-predeclared-2026-10-25-the-qos-eapol-key-admitted-our-eapol-on-tid-6-records-still-non-qos)
admits the TID, sends our EAPOL on TID 6 (the queue stays the explicit
TC4 port), records every refused pre-key frame, and keeps the records
non-QoS; success is a completed handshake and nothing else moved. Then
boot R (the records' QoS declaration), then HT capability.
Boot Q's image was written and read back from Gemian (boot `86417b2f…`),
preflight passed, and the device shut down cleanly; the owner selects boot2.

# Historical: the failed-boot evidence gap closed in two layers; ramoops lost to a cold power-key boot; boot P (WMM on, records non-QoS, the EAPOL header traced) predeclared, awaiting the owner's review before staging

[§26](HIF_TRANSPORT_ANALYSIS.md#26-boot-p-predeclared-2026-10-25-the-discriminating-boot-wmm-on-and-the-records-non-qos-instrumented)
is the discriminating boot: 0284 v2 with `WMM_QOS_RECORDS` off, and
every pre-key frame's header (length field, frame control, QoS control,
EtherType, BSS tag, verdict) recorded. The evidence gap is closed by
the leaf's failed-join exit and, behind it,
`failure_preservation.py`: the session stops the owned supplicant,
re-checks and seals, or exports the kernel record before refusing; the
watcher's return stops the owned processes and exports before its
proof. Ramoops did not survive boot O because the owner's restart was a
cold power-key boot (`boot_reason=0`), not a layout mismatch. The access
point negotiates WMM: the first HT prerequisite holds.

# Historical: boot O failed at the four-way handshake (the access point accepted WMM, no EAPOL-Key arrived); the kernel record was lost; 0284 reverted; a failed join must become sealable before the next join-path boot

[Boot O](HIF_TRANSPORT_ANALYSIS.md#boot-o-result-2026-10-25-1938-utc-the-access-point-accepted-wmm-the-four-way-handshake-timed-out-the-kernel-record-was-lost-0284-reverted):
the association with WMM succeeded; ten seconds later the access point
deauthenticated with reason 15 (handshake timeout), no EAPOL-Key having
reached the supplicant. The session would not seal and the reviewed
return would not run while the supplicant lived (as designed); the
owner restarted the device into Gemian `27f35470…`, and the ramoops
console did not survive. The lifecycle fragment is back to boot M's
tree. Before another join-path change is booted, a failed join must
leave its kernel record recoverable (the leaf ending its own supplicant,
or an export that does not need its quiescence). Closed: the leaf now
ends a failed join's data-phase wait itself (owner-reviewed
`join_failure_exit.py`), applied to every staged boot from here.

# Historical: the HT project starts: boot O (0284, WMM and QoS data at the legacy rate, success is that nothing moves) is staged on boot2 at 1882d5d3 (image 8c813def…, predecessor 95f81866…); the owner selects boot2

[§25](HIF_TRANSPORT_ANALYSIS.md#25-boot-o-predeclared-2026-10-25-wmm-and-qos-data-at-the-legacy-rate-a-de-risking-step-whose-success-is-that-nothing-moves):
[0284](../../patches/proposals/0284-wifi-mt6797-negotiate-WMM-and-carry-data-as-QoS-data-at-the-legacy-rate.patch)
registers four queues and `conf_tx`, admits the WMM element, declares
the station and the BSS QoS to the firmware when the access point
answers with WMM, and carries data (TID 0) and EAPOL as QoS data each
way; block-ack is refused, the descriptor, rate, ledger and depth (12)
are unchanged. The AAD of the 26-byte header is the firmware's on both
paths, not the host's; the host's risks are the admissions, the QoS
EAPOL-Key of the handshake first. No throughput expectation: success
is that nothing moved.
Boot O's image was written and read back from Gemian (boot `a8d4e94f…`)
over boot N's depth-16 image, so its composition is checked against boot
N with two symbols (the depth back to 12 and the WMM option): one
variable against boot M's configuration. Preflight passed; the device
shut down cleanly.

# Historical: depth is finished; transmit on the legacy rate sits at its wall (~23.5 Mbit/s, depth 12 the setting); the receive slowdowns are link-side; HT is the project; the next step is the owner's decision

[Boot N](HIF_TRANSPORT_ANALYSIS.md#boot-n-result-2026-10-25-1910-utc-depth-16-is-flat-the-air-binds-depth-12-is-the-setting-the-receive-stream-read-on-both-ends):
depth 16 carried 1,927 frames a second against depth 12's 1,900 with the
wait up a fifth, so the air binds; the lifecycle fragment is back at
depth 12. The receive stream, read on both ends: the device's
application lags at moments without closing the window, and the one
slow chunk's silences fell in its drain with the window open and the
device idle, a link-side event. The receipt read false only on the
transmit direction's normal 141 close (the direction-level rule now
accepts it); the data is whole. Throughput stands at about 23.5
transmit and about 19 receive (device count; the laptop's final half is
withdrawn as a receive measure) against a 30 Mbit/s air ceiling. A failed
verdict now names its check and phase (`verdict_failed`). [HT](HT_PROJECT_SCOPE.md)
is the project; mac80211 negotiates HT only with WMM, so its first boot is
WMM and QoS data at the legacy rate, a data-path change not yet started.
The access-point vanish-and-return test is the remaining robustness item.

# Historical: the air ceiling corrected to about 30 Mbit/s (transmit at 77 % of it); receive stays on the device's count; boot N (depth 16, the receive stream's state) is staged on boot2 at e13b2a90 (image 95f81866…, predecessor 7a9a40e8…); HT scoped as a project

Boot M is re-read with the owner: the fixed-54 air carries about 2,590
frames a second, about 30 Mbit/s, below the depth model's asymptote, so
the air is the wall. The brief's "device-side final halves" of 28–34
Mbit/s are the laptop's write rate; the device never delivered above
24.3 in a whole second, so receive stays quoted on the device's count.
[§24](HIF_TRANSPORT_ANALYSIS.md#24-boot-n-predeclared-2026-10-25-depth-16-and-the-receive-streams-state)
runs depth 16 once (25–26 expected) and records the receive stream on
both ends (the device's window every 50 ms, its socket queue every
0.5 s, the driver's frames a second). [HT](HT_PROJECT_SCOPE.md) is
scoped as a five-item project; items 1–2 are host-only.
Boot N's image was written and read back from Gemian (boot `38cd7be3…`),
preflight passed, and the device shut down cleanly; the owner selects boot2.

# Historical: boot M (depth 12) held the model and ends the depth sweep at about 23 Mbit/s transmit; one receive chunk slowed without a silence; the next step is the owner's decision

[Boot M](HIF_TRANSPORT_ANALYSIS.md#boot-m-result-2026-10-25-1853-utc-depth-12-on-the-model-the-depth-sweep-stops-a-receive-slowdown-the-silence-rule-cannot-see):
transmit 22.7–24.1 Mbit/s at a 5.46 ms wait with 12 in flight, nothing
freed unsent and one retransmission; the three-depth fit's asymptote is
35.7 Mbit/s, so the sweep stops at depth 12 (kept in the fragment). The
receive queue never stopped (high water ≤ 12). Receive chunk 5 slowed to
9.54 Mbit/s on the device's count with the laptop sending at 12.9 and
one second at 218 KiB, without a 200 ms silence: a real receive slowdown
the silence rule misses, not the acknowledgement queue. Above the ~33–36
Mbit/s wall only HT helps; the AP-loss vanish-and-return test is the
remaining robustness item.

# Historical: boot L withdrew the receive stall and the acknowledgement split; receive is measured on the device's count; transmit at depth 8 is a band of 19 ± 2; boot M (depth 12, once) is staged on boot2 at faea70e6 (image 7a9a40e8…, predecessor c0f4a6f1…); the owner selects boot2

[Boot L](HIF_TRANSPORT_ANALYSIS.md#boot-l-result-2026-10-25-1837-utc-the-queue-never-stopped-during-receive-transmit-did-not-reproduce-the-acknowledgements-lag),
no driver variable, first clean verdict: zero stops in every receive
second, no receive gap inside the receive window, every drain complete,
no timeout. The intermittent receive stall is withdrawn (chunk
boundaries and acknowledgement batching, read as a receive defect for
three boots), and with it the acknowledgement split. The receive rate is
the device's count over its span; the TCP flow's view is reported
beside it, never averaged. 0283 v2 logs the gap's before and after as
deltas, and the record keeps only gaps inside a direction's markers.
Transmit at depth 8 is 19 ± 2 (boot K 20.9, boot L 17.5).
[§23](HIF_TRANSPORT_ANALYSIS.md#23-boot-m-predeclared-2026-10-25-depth-12-once-then-stop):
depth 12 once, 24.6 predicted at a 5.66 ms wait, then the sweep stops.
Boot M's image was written and read back from Gemian (boot `9721fff5…`),
preflight passed, and the device shut down cleanly.

# Historical: boot L predeclared (depth 8 restored, receive measured over the send window, the queue's per-second series and receive gaps, the verdict's stale gates replaced) is staged on boot2 at 7fddd16f (image c0f4a6f1…, predecessor 5f5a187c…); the owner selects boot2

Boot K's revert fired on a receive artefact under a transmit change; the
rule is amended (a timeout reverts a change on its own path, or when the
safety counters show loss) and depth 8 is restored.
[§22](HIF_TRANSPORT_ANALYSIS.md#22-boot-l-predeclared-2026-10-25-depth-8-again-measured-over-the-send-window-with-the-queues-time-series)
adds no driver variable: the device's bound moves to 6 s, the laptop
measures each receive chunk over its send window and records the drain
beside it, 0283 prints the queue's stops, wakes and high-water per second
and every receive gap over 200 ms, and the throughput verdict keeps its
live gates and replaces the stale ones. The boot answers four questions:
transmit near 20.9, the clean receive rate, boot K's chunk 3, and whether
the queue ever stops during receive (expected: never). No
acknowledgement-split boot before those answers; HT stays closed below
the 33 Mbit/s ceiling. Boot L's image was written and read back from
Gemian (boot `4a464713…`), preflight passed with the 6 s bound and the
drain accounting rendered, and the device shut down cleanly.

# Historical: boot K held the rule on transmit (21.0 Mbit/s at depth 8, 21.7 predicted) and lost two receive chunks to the device's bound; the fragment is back at depth 4; the next boot is the owner's decision

[Boot K](HIF_TRANSPORT_ANALYSIS.md#boot-k-result-2026-10-25-1810-utc-transmit-27--on-the-rule-the-revert-row-fired-on-receive-confounded-by-the-harness):
transmit 20.9–21.2 Mbit/s steady (+27 % on boot J), wait 4.26 ms with 8
in flight, 564 stops, nothing freed unsent, four retransmissions. Two
receive chunks ended on the device's 4 s bound, so §21's revert row
fired and `CONFIG_MT6797_CCMP_TX_DEPTH` is 4 again. The attribution is
confounded: the 16 MiB cap made receive chunks duration-bound for the
first time, and the drain after the laptop's close (0.6–0.8 s on the
whole chunks) races the device's bound; one of the two is that race,
the other the intermittent receive stall again, this time with a deep
queue. Separating them needs the receive bound past the drain and the
stops split by direction.

# Historical: boot J released the mechanism (TX 15.5–16.7 Mbit/s, zero loss, the pipeline saturated at depth ÷ wait); the acknowledgement path read from source; boot K (depth 8, 16 MiB chunks) is staged on boot2 at 5a3e577d (image 5f5a187c…, predecessor 5e19a3c6…); the owner selects boot2

[Boot J](HIF_TRANSPORT_ANALYSIS.md#boot-j-result-2026-10-25-1753-utc-transmit-above-12-with-zero-loss-the-retransmissions-were-part-of-the-cost)
took §20's second branch: 156 stops and wakes (boot I's 2,223),
`high_water=56` of 64, nothing freed unsent, six retransmissions in
14,550 segments; backpressure was right and the eight-frame bound was
not. The transmit ceiling is now depth ÷ `wait_avg` (4 ÷ 2.864 ms =
1,397 frames/s, 16.2 Mbit/s predicted, 16.5 measured), and the wait fell
to 2.86 ms once nothing was dropped. From source: the 802.11 ACK never
reaches the host, but the receive path's TCP acknowledgements share the
one data queue, its stop and its four-frame window, so the receive-stall
hypothesis stands as consistent, not proven, and is watched rather than
reproduced. [§21](HIF_TRANSPORT_ANALYSIS.md#21-boot-k-predeclared-2026-10-25-depth-8-on-boot-js-tree)
predeclares boot K: depth 8 (ledger 104) on boot J's tree, chunks at
16 MiB or 3 s; HT stays closed. Boot K's image was written and read
back from Gemian (boot `3722770b…`) and the device shut down cleanly;
the watcher starts the same run on the owner's boot2 selection.

# Historical: boot J (0282 v2: queue bound 64, stop 56, wake 32) is staged on boot2 at e51cb584 (image 5e19a3c6…, predecessor d589c647…); the owner selects boot2; the watcher starts the five-chunk run

Boot J's image was written and read back from Gemian (boot `fa957e17…`),
the device shut down cleanly; the measurement is the same as boots H and
I (five steady-state chunks each way, the echo legs, the TCP state per
chunk, the early-stop record), read against
[§20's table](HIF_TRANSPORT_ANALYSIS.md#20-boot-j-predeclared-2026-10-25-backpressure-with-the-queue-decoupled-from-the-depth).

# Historical: Current: boot I showed the backpressure mechanism works and its queue discipline does not; 0282 v2 decouples the queue bound (64 frames, stop at 56, wake at 32); boot J measures it; the AP-loss gate passed as an AP-initiated disassociation

[Boot I](HIF_TRANSPORT_ANALYSIS.md#boot-i-result-2026-10-25-1733-utc-the-mechanism-works-the-queue-discipline-does-not)
and [§20](HIF_TRANSPORT_ANALYSIS.md#20-boot-j-predeclared-2026-10-25-backpressure-with-the-queue-decoupled-from-the-depth):
2,223 stops and wakes (one every 16 ms) with zero frames freed unsent
throttled transmit to a third because the 8-frame bound sat at the
in-flight depth's order; 0282 stays (silent drops are never the
fallback again) and its bound becomes its own option, 64 frames with
wide hysteresis. Boot J is that one variable on the same run; its table
decides whether the drain rate is confirmed (HT opens) or higher. The
[gate](LIFECYCLE_RESULT.md#ap-loss-gate-result-2026-10-25-1548-utc--three-lifetimes-the-loss-was-the-access-points-own-inactivity-disassociation-reported-as-reason-4-and-the-station-rejoined-within-2-s-of-its-rearm)
is re-read as the access point's own inactivity disassociation (no owner
actuation existed) and passes on those terms; no owner times are owed.

# Historical: boot I (backpressure) reverted by the rule; the retransmissions TCP counts are not the driver's drops nor the air; boot J reads the device's TCP counters for loss against spurious retransmission

[Boot I](HIF_TRANSPORT_ANALYSIS.md#boot-i-result-2026-10-25-1733-utc-backpressure-held-and-transmit-fell-the-losses-tcp-counts-are-not-the-drivers-drops-0282-reverts)
and [§20](HIF_TRANSPORT_ANALYSIS.md#20-boot-j-predeclared-2026-10-25-loss-or-spurious-retransmission-read-from-the-devices-tcp):
2,223 stops and wakes with zero frames freed unsent, and transmit fell to
a third with 549 retransmissions and a receive chunk at the device's
bound; 0282 reverts (the lifecycle fragment is back to boot H's tree,
the option stays). The remaining reading is retransmission without loss
(loss probes and spurious timeouts against a late acknowledgement); boot
J reads the device's TcpExt counters before and after the transmit
phase on boot H's image, harness only. HT stays closed. The owner's AP
power times are still owed.

# Historical: boot H's third run is whole: the transmit limit is the driver's silent drops above its drain rate (no backpressure) plus the drain itself; boot I adds backpressure

[Run 3](HIF_TRANSPORT_ANALYSIS.md#boot-h-third-run-2026-10-25-1714-utc-whole-the-transmit-limit-is-the-drivers-own-drops-not-the-air-not-the-depth-and-tcp-holds-a-six-segment-window-because-of-them)
and [§19](HIF_TRANSPORT_ANALYSIS.md#19-boot-i-predeclared-2026-10-25-backpressure-toward-mac80211-one-variable):
373 sampled frames all acknowledged at 0x4c; the device's TCP at cwnd 6
with 451 retransmissions that no counter shows; the source names the
drop (a full 8-frame data queue frees the next frame unsent, no
ieee80211_stop_queues anywhere); the echo legs lose 29–54 % above about
9 Mbit/s offered. HT stays closed. Boot I: 0282 stops mac80211's queues
at the bound and wakes them when drained, one variable, the same run;
0282 is in the series and the lifecycle fragment, its package building at
`b02ddb84`, the work directory derived; its expectation is loss to zero
and 10–20 Mbit/s, not a multiple, read with `wait_avg`, `inflight_max`,
stops and wakes beside the rate; HT opens only on zero-loss transmit at
the drain rate. Boot I is staged: boot2 `d589c647…` over `0f1ca6cf…`
(full readback verified from Gemian `0550b47c…`), device shut down,
watcher armed; the owner selects boot2. The owner's AP power times are
still owed.

# Historical: boot H's first run void (harness stop after one chunk; the sampled report works); the second run adds the transmit probe and the device's TCP state; HT is not opened

[§18](HIF_TRANSPORT_ANALYSIS.md#18-boot-h-second-run-predeclared-2026-10-25-the-transmit-probe-and-the-devices-tcp-state):
boot F's reading is corrected a third time (depth 8 neutral, the offer
rate is the limit, mechanism not identified); boot H's one chunk proved
the air exonerated (39 samples at 0x4c, status 0) and recorded the
access point's downlink distribution; the silent early stop is a named
harness fault now recorded with its reason. The second run on the same
image carries a device-to-laptop echo probe at 10/20/30 Mbit/s and the
device's congestion window per chunk; its table decides between the
driver and TCP before any HT work. The second run is staged on the same
image (boot2 `0f1ca6cf…`, the installer's full readback matched and the
write skipped; device shut down; watcher armed; the owner selects boot2);
the console indicator is off this run for the device command's bound.
The second run stopped after one chunk again (the device's nc ends the
laptop's close with SIGPIPE, 141, not 1), this time with the stop named
in the receipt by the early-stop record; its one congestion-window sample
(cwnd 7, ssthresh 5 at 9.2 Mbit/s) provisionally reads TCP-paced. The
transmit leg accepts 141; the third run is staged on the same image
(installer skip with full readback, device shut down, watcher armed; the
owner selects boot2). The owner's AP power times are still owed.

# Historical: boot F read as no change (the firmware's per-frame transmit processing is the limit, ~800 frames/s); boot G cancelled; boot H samples the status report 1 in 64; HT aggregation is the throughput project

[Boot F result](HIF_TRANSPORT_ANALYSIS.md#boot-f-result-2026-10-25-1613-utc-depth-8-did-not-move-transmit-the-slots-are-half-empty-the-limit-is-upstream-of-the-driver)
(corrected reading) and [§17](HIF_TRANSPORT_ANALYSIS.md#17-stalls-named-and-boot-h-predeclared-2026-10-25-the-sampled-status-report):
the service time is 1.24 ms a frame at both depths (utilisation 0.99), so
the firmware's per-frame transmit processing is the limit and depth,
report, ledger and buffers cannot move it; depth returns to 4, boot G
(depth 12) is cancelled. Stalls are a named object with device-clock
timestamps; every result quotes stall-free chunks beside the whole run.
Boot H restores the rate and latency instruments by sampling one data
frame in 64 with the MCU status report (0281, predeclared with its
table). The throughput lever is aggregation, which means HT (a project);
one bounded RE question first (software CCMP in the firmware's transmit
path?), private memo, no boot: answered, no AES tables in either image,
the cost is not encryption. Boot H is staged: lifecycle package at
`a1aa339a` (depth 4, credit retire, one report in 64), boot2 `0f1ca6cf…`
over `78bc8d58…` (full readback verified from Gemian `ccba9a97…`), five
steady-state chunks with the device bound at 4 s. Its first run was void
for the series: the 4 s device bound made the laptop close a transmit
chunk first and the leaf read the device's exit 1 as a fault after one
chunk; the sampled report itself worked (39 samples, 39 reports, all at
0x4c with status 0, latency 4–8 ms). The transmit leg now accepts that
close; the run is repeated on the same image. The owner's AP power times
are still owed.

# Historical: boot F (depth 8) measured neutral; the transmit limit is upstream of the driver (the sender's TCP); depth returns to 4; next are transmit UDP legs and the TCP retransmission count

[Boot F result](HIF_TRANSPORT_ANALYSIS.md#boot-f-result-2026-10-25-1613-utc-depth-8-did-not-move-transmit-the-slots-are-half-empty-the-limit-is-upstream-of-the-driver):
first steady-state protocol run (4 MiB or 3 s); transmit 9.2 Mbit/s
steady at depth 8 as at depth 4, the retire wait up 28 %, 3.6 of 8 slots
occupied on average: the frames are not arriving at the driver fast
enough; one chunk stalled on a TCP timeout; receive reached 20 Mbit/s on
a 2 MB window over a 300–600 ms round trip; UDP 30 zero loss. Depth
returns to 4 (0280 stays the option), the sweep stops, the protocol's
bound race is fixed (device 4 s). Next: a transmit UDP leg and the TCP
retransmission count, both harness instruments; then the air-loss and
send-buffer levers if TCP is the limit. The AP-loss gate is recorded;
the owner's actual power times are still owed.

# Historical: the AP-loss gate ran (loss by keep-alive, not beacons; rejoin passed); the protocol moves to 4 MiB or 3 s chunks; boot F (depth 8) is next

[Gate result](LIFECYCLE_RESULT.md#ap-loss-gate-result-2026-10-25-1548-utc--three-lifetimes-the-loss-reported-by-the-firmwares-keep-alive-judgement-not-by-beacons):
no loss report within 60 s of the cut (beacon-loss detection not armed
on this tree), the eventual report reason 4 (the firmware's keep-alive
judgement), the rejoin within 2 s against the restored access point, a
third lifetime passed, the ledger clean across the loss; 0267's refused
join path still unexercised. The measurement protocol becomes 4 MiB or
3 s per chunk with a final-half rate (the 1 MiB cap made every receive
chunk since rx-batch-4 and boot E's transmit a floor, marked in the
series table); the memory policy and the instrument corollary are
recorded. 0280 (depth with the ledger derived from it) is in the series.
Boot F is staged: lifecycle package at `4a6c3785` (depth 8, ledger 104),
boot2 `78bc8d58…` over `528d1d1d…` (full readback verified from Gemian
`104bb967…`), five steady-state chunks (4 MiB or 3 s) with the probe,
preflight passed, device shut down, watcher armed; the owner selects
boot2. Boot G (depth 12) follows on boot F's numbers.

# Historical: the AP-loss gate is running; boots F and G (depth 8 then 12) are predeclared on the credit-retire baseline

[§16](HIF_TRANSPORT_ANALYSIS.md#16-boots-f-and-g-predeclared-2026-10-25-the-depth-one-variable-each):
with data retired on credit arrival the depth is the only bound on the
frames the firmware holds; the ledger admits 52 of the firmware's 468
pages. 0280 makes the depth and the ledger pages options; boot F runs
depth 8 (104 pages), boot G depth 12 (156), one variable each, five
chunks, the per-chunk cap raised to 4 MiB, the revert rule standing;
each read against its own rising wait. Boot E's page accounting is
reconciled (13-page data frames plus 1-page acknowledgements match the
credits to 0.8 %; one 128-byte unit on both sides) and the vendor's
resource contract is sourced from nic_tx.c (50 ms poll, no per-frame
FIFO). The AP-loss gate runs over the boot-E image now.

# Historical: boot E measured; the credit model (0278) is admitted as the transmit completion path; the TX harness cap now binds; AP-loss gate next

[§15 result](HIF_TRANSPORT_ANALYSIS.md#boot-e-result-2026-10-25-1538-utc-the-credit-model-is-the-completion-path-for-transmit-receive-did-not-follow):
5,637 frames retired on credit arrival (mean wait 3.5 ms at four in
flight, no expiry, no fault, zero-payload check passed); every TX chunk
hit the 1 MiB cap in 0.9 s, so the transmit figure (9.2–9.5 Mbit/s) is a
floor and `byte_cap_per_chunk` must be raised before the next transmit
measurement (owner's call on the finite protocol); receive 17.9–20.0,
inside the floor: the receive limit is not the transmit completion path
(UDP 30 Mbit/s at zero loss; TCP receive paced by a 29 ms round trip).
0274 v2 verified on hardware (beyond=3304). The AP-loss gate is staged
over the boot-E image (the same image, `528d1d1d…`, install skipped as
already matching with full readback; three lifetimes, one chunk each,
cycle 2 waits for the access-point loss; watcher armed; the owner
selects boot2 and cuts the access point's power 60–120 s into the
second lifetime's data phase, restoring it 60 s later). Then fewer bus
transactions per frame on transmit and the receive round trip from the
device side.

# Historical: the fixed-54 tree is the baseline; boot E (the credit model, five chunks, aggregate logging) is next

[§15](HIF_TRANSPORT_ANALYSIS.md#15-boot-e-predeclared-2026-10-25-the-corrected-credit-model-read-on-both-directions):
one quantity (about 1.5 ms a frame) limits both directions; boot E
attacks it with 0278 (no PID, no status report, retired on credit
arrival with a submission timestamp read at the credit event) on the
baseline tree, with 0275 v2 and 0279 keeping five chunks under the
logger's cap. Boot E is staged: lifecycle package at `c6fa0edc`, boot2
`528d1d1d…` over `df7d6e65…` (full readback verified from Gemian
`3279578d…`), five chunks, preflight passed, device shut down, watcher
armed; the owner selects boot2. Boot D closed the rate thread (0277 a proposal with one open
question; the two-chunk numbers valid, not series rows; the UDP 30 leg
is the strongest receive evidence). Then the AP-loss gate, independent.

# Historical: boot D measured (state 2 accepted, the firmware selects 6 Mbit/s); the rate thread is closed on the fixed 54 descriptor; the AP-loss gate is next

[Boot D result](TX_AUTORATE_RESULT.md#state-2-station-record-boot-second-attempt-result-2026-10-25-1506-utc--the-table-is-valid-the-selection-stays-at-6-mbits-the-rate-thread-closes):
the state-2 record is accepted and data without a fixed rate is
acknowledged, every frame at the firmware's rate word 0x004b; TX at the
fixed-6 baseline, 45 % below boot C's fixed 54, so 0273 at 0x4c stays the
data path and the rate thread closes (what makes the firmware climb is a
firmware-side question, not a boot). Two chunks kept the log complete.
Next: the AP-loss gate (lifecycle tree at b2b7e693 over the boot-D image;
verifies 0267 and the timeout-debt contract; owner at the access point),
then the completion lever's corrected second attempt if the owner admits
it (drafted and compiled, not in a series).

# Historical: boot C measured (54 Mbit/s acknowledged, TX ×1.9, log cut at the cap); boot D (state 2) prepared on the rebuilt rate series

[§13 result](HIF_TRANSPORT_ANALYSIS.md#boot-c-result-2026-10-25-1314-utc-54-mbits-acknowledged-transmit-19-the-log-cut-at-the-cap)
and the [boot D predeclaration](TX_AUTORATE_RESULT.md#state-2-station-record-boot-second-attempt-predeclared-2026-10-25-the-encoder-admits-state-2):
the fixed rate at 54 is acknowledged; TX per chunk ×1.9, receive inside
the floor, about 1.6 ms per frame remains with the air time removed; the
device log sealed at its cap under the per-frame records, so boot D
measures two chunks per direction. The review amended 0274 (the budget
step still closed the window at the ceiling) and 0271 (line buffer),
retired 0262/0263 for 0275/0276 (the rate series did not apply), and
added 0277 (state 2). Boot D is staged: rate package at `e1e67f78`,
boot2 `df7d6e65…` over `8cd36314…` (full readback verified from Gemian
`52ffff40…`), two chunks per direction, preflight passed, device shut
down, watcher armed; the owner selects boot2. Then the completion lever's
corrected second attempt; the AP-loss gate independent.

# Historical: boot B regressed (0272 retired, 0269 reverted); boot C, the fixed-rate sweep at 54 Mbit/s, is next

[§12 result](HIF_TRANSPORT_ANALYSIS.md#boot-b-result-2026-10-25-1208-utc-a-regression-0272-retired-0269-reverted)
and [§13](HIF_TRANSPORT_ANALYSIS.md#13-boot-c-predeclared-2026-10-25-the-fixed-rate-sweep-6--54-mbits):
retiring at submission removed the only bound on the firmware's air queue;
the credit model is corrected for any second attempt (retire on credit
arrival); the access point sends at 54 Mbit/s to this station. Boot C:
0273 rate code 0x4c on the admitted tree with 0270, 0271 and 0274 (the
ceiling stops its count, never the window); fallback 0x49. Then D (state
2); the AP-loss gate independent.

# Historical: boot B predeclared and building (0269–0272: ceiling lift, delivered count, RX rate record, credits-only completion)

[Transport record §12](HIF_TRANSPORT_ANALYSIS.md#12-boot-b-predeclared-2026-10-25-retire-ordinary-data-on-page-credits):
ordinary data goes out without a PID or an MCU status report and is
retired at submission; the comparison is within the session against probe
boot 4 (or an adjacent baseline boot if the owner's hands allow); TX
first, then the four-row table; two attempts at the lever. The fixture
covers the descriptor forms and the vector word. Absence ledger: five
entries. Queue after B: C (rate sweep), D (state 2); AP-loss gate
independent.

# Historical: the probe answered (boot 4): the receive path is not the ceiling; boot B (credits-only completion) is next, with the diagnostic ceiling lifted in the same build

[§11](HIF_TRANSPORT_ANALYSIS.md#probe-boot-4-2026-10-25-1139-utc-the-readings-graded-correctly):
UDP 10/20 Mbit/s delivered with zero loss, RTT 7–8 ms at rest and 40–130
loaded, window ample; TX 3.7–4.1 and RX 14.5–15.8 device-side in this
session (±40 % session variance; the comparison rule is now
within-session). The verdict line was the native-diag's 8,192 queued-frame
ceiling closing the data window under the probe's datagrams. Next build:
lift that ceiling for the measurement lifetime, the delivered-frame count
on the data-end line, the received-rate record, and boot B's change (no
MCU status report for ordinary data, completion on page credits). The
probe block now ends with its own status line; a missing rate is recorded
missing. Queue after B: C (rate sweep), D (state 2); AP-loss gate
independent.

# Historical: probe boot 3 void (command bound; real base 433 bytes), device recovered through the reviewed path; boot 4 staged with the probe after the chunks, the exact-base preflight, the device-block test and the recovering watcher

[§11](HIF_TRANSPORT_ANALYSIS.md#probe-boot-3-2026-10-25-voided-before-the-measurement-recovered-through-the-reviewed-path):
the helper refused its own command bound (4101 bytes); the leaf waited; the
session host refused export and recovery together; the reviewed
preservation and return recovered the device (nothing killed, changed-ID
Gemian 37bc58e9…). Recovery is unbundled at the watcher (300 s wall clock,
automatic reviewed return). The six fixes and the device-block offline
test are in; the UDP, ping and interval readings are still owed to boot 4.
The queue after it stands: B, C, D, the AP-loss gate independent.

# Historical: probe boot 3 staged behind the preflight gate; the owner's queue is B (credits-only completion), C (rate sweep), D (state 2), AP-loss gate independent

[§11](HIF_TRANSPORT_ANALYSIS.md#before-probe-boot-3-the-two-faults-named-the-gate-on-the-rendered-run-the-queue):
the two faults are named (the swept flag; the dead counter trio on a path
the tree never enters, while the receive leg itself delivered), the
preflight gate reads the rendered run and refuses boot 2's, and boot 3
adds the laptop's pings at rest and in-chunk and the interval samples.
Next build (logging only): the delivered-frame count on the data-end line
and the received-rate record. The absence ledger has four entries.

# Historical: probe boots 1 and 2 lost to the harness (unbound host, renamed flag); third same-image run staged with the plan asserted

[§11](HIF_TRANSPORT_ANALYSIS.md#probe-boot-2-2026-10-25-a-graded-repeat-the-probe-ran-disabled-by-the-staging):
boot 2 is a graded TCP repeat (2.67 / 6.99) with the probe disabled by a
renamed environment flag in the derived staging script. The staging now
asserts the plan and the device script before the install. The ping and
UDP readings are still owed; boot 1's TCP samples stand.

# Historical: probe boot 1 half ran (TCP samples valid, ping/UDP void by injection order); same-image re-run staged

[§11](HIF_TRANSPORT_ANALYSIS.md#probe-boot-1-2026-10-25-the-tcp-samples-came-the-ping-and-the-udp-bursts-did-not):
the device's advertised window is ample and the in-chunk TCP round-trip
time is 61–102 ms (a queue), not 4 ms; the ping and UDP readings are owed
to the re-run (the probe block was inserted after the host placeholder
was substituted; fixed, guarded). A fourth row joins the table: the
access point's legacy downlink rate to a station that advertises no HT.

# Historical: the owner's order after boot 4; the receive probe is staged

Owner decisions (2026-10-25): 0268's admission reverted (neutral;
precedent), the proposal kept behind its option; the receive probe
approved as a mechanism measurement with three readings in one boot
([transport record §11](HIF_TRANSPORT_ANALYSIS.md#11-receive-probe-predeclared-2026-10-25-is-the-receive-number-clocked-by-the-transmit-path));
the state-2 encoder attempt approved as one boot after the probe, closing
the rate thread on its result; the AP-loss gate independent, scheduled
when the owner is at the access point; the completion-latency answer from
source is in §10; the standing audit has three questions.

# Historical: 0268 measured (boot 4): neutral, kept; the receive number may be clocked by transmit latency

[Transport record §10](HIF_TRANSPORT_ANALYSIS.md#boot-4-of-0268-2026-10-25-the-measurement--the-register-work-was-not-the-receive-cost-either):
TX 2.64 in band, debt 0, failures 0; receive 6.37 host-side with 12,754
frames through the block and the aggregates. Register work was not the
receive cost. The transmit completion rate during the receive chunks sits
at the TCP acknowledgement rate, so an acknowledgement-free receive chunk
(UDP) or a round-trip measurement is proposed before the interrupt; the
owner decides the protocol change. Owner decision still owed on the
state-2 attempt. The AP-loss gate is where a failed join's accounting is
verified.

# Historical: 0268 boot 3 named the abnormal interrupt; cause was our WHCR write; boot 4 is the one measurement boot

[Transport record §10](HIF_TRANSPORT_ANALYSIS.md#boot-3-of-0268-2026-10-25-the-guards-words-name-the-abnormal-interrupt-the-cause-is-our-own-whcr-write):
the guard's words excluded three of the four sources and confirmed the
device's abnormal interrupt; the vendor's init clears WHCR bit 16 (RX
enhancement) and our enable set it. 0268 now confirms WHCR by reading and
never writes it; the block's WHISR is not copied (counts merged, done bit
synthesised, block-carried abnormal recorded and fatal); the join-replay
fixture passes. Budget: boot 4 measures (TX first), a refusal there
reverts the admission to per-frame and the study goes to source. Owner
decision still owed on the state-2 attempt.

# Historical: 0268 boot 2 reached EAPOL message 2, then the join guard refused (-EIO, debt 0); guard record added, boot 3 staged

[Transport record §10](HIF_TRANSPORT_ANALYSIS.md#boot-2-of-0268-2026-10-25-the-credits-came-the-join-guard-refused-at-the-second-eapol-message):
the credit merge delivered every credit; the stop is one of four -EIO
sources the log cannot tell apart, and the join guard now records the
words it saw. Boot 3 reads TX first (2.6–2.8 band, debt 0, failures 0)
before any receive row applies. Standing rule for every predeclaration
from now on: three questions answered from source, no boot: reachability
(which function performs the bus write; what earlier can refuse or consume
it), ownership (which registers the new code reads destructively, who
else reads or writes them, what they now see) and, for every register the
new code writes, what the vendor writes there, or that it writes nothing
(absence is the evidence: WHCR never written, WHISR never copied, state 2
never sent through a refused encoder). Owner decision still owed
on the state-2 attempt (last of the rate thread, after batching, if yes).
The AP-loss gate is where a failed join's accounting (0267, the timeout
contract) is verified.

# Historical: 0268 boot 1 stopped at the credit wait (block read consumed the TX counts); amended 0268 builds

[Transport record §10](HIF_TRANSPORT_ANALYSIS.md#boot-1-of-0268-2026-10-25-the-join-stopped-at-its-credit-wait-the-block-read-had-consumed-the-tx-release-counts):
the receive side worked through authentication, the credit path never saw
the counts the block had consumed. The amended proposal merges them into
the TX status acquisition, never poisons on what the block says, and adds
two branch rows; boot 2 is the same measurement. Queue after it: the
owner-confirmed state-2 encoder attempt (explicitly last of the rate
thread, if confirmed), then the AP-loss gate.

# Historical: receive batching (0268) predeclared and building; the page-release fix rides with it

Offline items done since the state-2 refusal: 0267 (a refused join
command releases its page reservation), the console-injection guard, the
second pruning increment (192 files), and 0268 (receive by the enhanced
status block and one aggregated read per queue, host fixture passing).
Next boot: the lifecycle profile with 0267 and 0268, predeclared in the
[transport record §10](HIF_TRANSPORT_ANALYSIS.md#10-receive-batching-boot-predeclared-2026-10-25).
The owner decides separately whether the encoder's admission of station
state 2 is tried once as the last rate attempt.

# Historical: state-2 boot inconclusive (join refused); page-debt fix, batching, pruning, guard next

[Autorate record](TX_AUTORATE_RESULT.md#state-2-station-record-boot-inconclusive-join-refused-0266-retired-2026-10-24):
our own encoder refused station state 2 (-22, `mt6797_join_station_payload`),
the join stopped before any data phase, and 0266 is retired; the vendor
uses the same command and record for every state, so only the state order
differs. The owner decides whether the encoder's admission is tried once
as the last rate attempt. Next, offline while nothing runs: release the
page reservation of a refused join command (the stop line reads `debt=2`),
the receive-batching proposal (the next throughput boot), the second
pruning increment, and the guard on the console injection. Device
returned to Gemian `93ff170a…`.

# Historical: the state-2 station-record candidate is installed and armed; the owner boots it

Rate profile `93a9f000` (0262, 0263 for this boot only, 0266) composed
from the package's tree, installed on boot2 (`bf9bd805…` over `51faa318…`,
written from Gemian `84dfc8eb…`, full readback verified), device shut
down, watcher armed, console indicator enabled (not evidence). Branch
table: [autorate record](TX_AUTORATE_RESULT.md#state-2-station-record-boot-predeclared-2026-10-24).

# Historical: the state-2 station-record boot is predeclared and building

[Autorate record](TX_AUTORATE_RESULT.md#state-2-station-record-boot-predeclared-2026-10-24):
0266 sends the station record at state 2 after authentication, the
smallest difference from the vendor's record sequence, on the re-created
rate profile (0262 record, 0263 unforced data rate for this boot only).
Branch table in the record. The AP-loss gate waits for the owner at the
access point; the interrupt-driven receive is the transport step after.

# Historical: both DMA directions booted and kept; the poll structure is the receive ceiling

[Transport record §9](HIF_TRANSPORT_ANALYSIS.md#9-receive-direction-dma-boot-result-2026-10-24--engaged-intact-and-not-the-ceiling):
receive DMA engaged (8,510 moves in, 3,870 out, zero failures, data
intact) and neither rate moved (TX 2.63, RX 6.67 Mbit/s), so the per-frame
poll structure is the receive ceiling and the interrupt with the
enhanced-status read is the next transport step. Both directions stay
admitted (lower CPU, zero failures; counter: one receive chunk at 9.64).
The console indicator wrote its five stage blocks (30 lines, no error),
not evidence. Device returned to Gemian `84dfc8eb…`. Queue: the AP-loss
gate (0254) with loss defined for a tree without a host keep-alive, the
station-record rate inputs (branch 3 of the rate table), then the
interrupt-driven receive.

# Historical: receive-DMA candidate installed and armed; the owner boots it

The lifecycle profile with `CONFIG_MT6797_HIF_DMA_RX=y` (`fdf4c6b1`) is
composed from the package's tree, installed on boot2 (`51faa318…` over
`695a8f88…`, written from Gemian `14da9b9e…`, full readback verified), the
device shut down and the watcher armed; the console progress indicator is
enabled for this run (opt-in, not evidence). Predeclaration:
[transport record §8](HIF_TRANSPORT_ANALYSIS.md#8-receive-direction-dma-boot-predeclared-2026-10-24).

# Historical: pass rate is not the mechanism; receive DMA is the next boot

[Receive record](RX_REBASELINE_RESULT.md#pass-rate-boot-result-2026-10-24--neither-direction-moved-the-polled-read-is-the-ceiling):
with one data submission per pass neither direction moved (TX 2.55, RX
7.16 Mbit/s; 5,011 passes per second, 0.034 frames per pass), so the
polled read is the receive ceiling; 0265 retired, 0264 kept. The display
probe found fbcon bound and the tty0 write landing (not evidence). Next
boot, predeclared in the [transport record §8](HIF_TRANSPORT_ANALYSIS.md#8-receive-direction-dma-boot-predeclared-2026-10-24):
the lifecycle fragment admits the receive direction. Device returned to
Gemian `14da9b9e…`.

# Historical: pass-rate candidate installed and armed; the owner boots it

The lifecycle profile with 0264 (pass census) and 0265 (one data
submission per pass) is built (`3fd31bdd`), composed from the package's
tree, installed on boot2 (`695a8f88…` over `bb9b9389…`, written from
Gemian `28318e8b…`, full readback verified), the device shut down and the
watcher armed. Headline and branch table in the
[receive record](RX_REBASELINE_RESULT.md#pass-rate-boot-predeclared-2026-10-24-pass-rate-not-pass-order);
the fbcon display probe rides on this boot, not graded.

# Historical: the unforced rate is named (zero: an empty rate table); pruning pass next

[Autorate record](TX_AUTORATE_RESULT.md#rate-visibility-boot-result-2026-10-24--branch-3-an-empty-rate-table):
every ordinary data frame sent without a fixed rate carried the firmware
rate word `0x0000` (the CCK 1 Mbit/s code, undecodable on 5 GHz) while
the fixed-rate control frames carried `0x004b`; branch 3 of the table,
the station record's rate inputs are the lever, predeclared when its turn
comes. 0263 retired, 0262 kept. Device returned to Gemian `28318e8b…`.
The [pruning pass](PRUNING_2026-10-24.md) retired the answered
measurement profiles. The pass-rate boot is predeclared
([record](RX_REBASELINE_RESULT.md#pass-rate-boot-predeclared-2026-10-24-pass-rate-not-pass-order)):
0264 census, 0265 cap set to one in the lifecycle fragment, the fbcon
display check riding on it; then receive DMA, the AP-loss gate with loss
defined under host keep-alives, and the station-record rate inputs.

# Historical: rate-visibility candidate installed and armed; the owner boots it

The owner classified the three extra booted-tree categories as boot-loader
writes; the device-tree chain is closed in both directions. The
rate-visibility candidate (profile `mt6797-a53-wifi-rate`, `91629f5b`,
boot2 `bb9b9389…` over `a0bbc52e…`, written from Gemian `c0fe3443…`, full
readback verified) is installed, the device shut down, the watcher armed.
Headline and branch table: [autorate record](TX_AUTORATE_RESULT.md#rate-visibility-boot-predeclared-2026-10-24-runs-after-the-equivalence-boot).
After it: the pruning pass (inventory drafted), then the pass-rate boot,
receive DMA, and the AP-loss gate with loss defined under host keep-alives.

# Historical: the chain is closed on the device; the rate-visibility boot waits on one classification

[Provenance record](DEVICE_TREE_PROVENANCE.md#closing-the-chain-on-the-device-result-2026-10-24):
the same equivalence image booted again with the harness reading
`/sys/firmware/fdt` back; every measured item passed (285/285, DMA
attached, TX 2.67, RX 7.54 Mbit/s) and the booted tree equals the build
except for boot-loader writes, three categories of which (reserved-memory
blocks, the Android firmware node, the SCP status) were not in the
predeclared allowance. The owner classifies that before boot2 is
overwritten by the rate-visibility candidate, which is built (`91629f5b`)
and derived. Device returned to Gemian `c0fe3443…`.

# Historical: equivalence boot passed; the rate-visibility boot is next

[Provenance record](DEVICE_TREE_PROVENANCE.md#equivalence-boot-passed-2026-10-24):
the candidate built from the committed series alone (0261, tree from the
package, RAM root declared) booted as the inherited tree did: common init
285/285, the DMA attach record as boot 2, TX 2.63 and RX 6.77 Mbit/s,
inside the seen variance. The series' results stand on a tree anyone can
rebuild; composers take the tree from the package from here on. Device
returned to Gemian `0e50a29d…`. Next: the rate-visibility boot on profile
`mt6797-a53-wifi-rate` (0262 rate record, 0263 unforced data rate) with
its [branch table](TX_AUTORATE_RESULT.md#rate-visibility-boot-predeclared-2026-10-24-runs-after-the-equivalence-boot);
then the pass-rate boot; then receive DMA.

# Historical: equivalence boot building; rate-visibility boot predeclared behind it

The lifecycle profile with 0261 is built (`18be24e3`); the equivalence
candidate (`02cd8b1e…`, boot2 `a0bbc52e…` over `b9afec4d…`, written from
Gemian `af51145e…`, full readback verified, device shut down, watcher
armed) takes its board tree from the package through
[`hosts/candidate_inputs.py`](hosts/candidate_inputs.py) (the RAM root
declared as the one inherited artefact, the parent's tree checked
equivalent). After it: the rate-visibility boot on profile
`mt6797-a53-wifi-rate` (0262 rate record, 0263 unforced data rate), with
its branch table in the [autorate record](TX_AUTORATE_RESULT.md#rate-visibility-boot-predeclared-2026-10-24-runs-after-the-equivalence-boot);
then the pass-rate boot; then receive DMA. The transmit-DMA question is
closed ([transport record §7](HIF_TRANSPORT_ANALYSIS.md#7-conclusion-the-transmit-data-copy-is-not-the-bottleneck)).

# Historical: the service tree (0261) reproduces the booted device tree; equivalence boot next

[Provenance record](DEVICE_TREE_PROVENANCE.md): the tree every Wi-Fi run
booted since 2026-10-17 is identified (`25ab60f4…`, a mid-August
serviceability tree edited in place by the July and October experiments),
and proposal 0261 reproduces it from source: zero nodes and zero
properties differ from the boot-2 tree, only phandle numbering. Next: build
the lifecycle profile with 0261, compose a candidate from the package's own
service tree (composers no longer copy a parent's tree), and run the
predeclared equivalence boot; then the rate-visibility boot, the pass-rate
boot, and receive DMA on the reproducible tree.

# Historical: DMA series paused after boot 2; device-tree reproducibility first

Owner direction (2026-10-24): no further DMA candidate is installed until
the device tree the Wi-Fi runs boot can be regenerated from committed
inputs. Order: identify the inherited tree and its origin exactly; add
the DTS change that reproduces it; build from committed inputs alone and
account for any delta; one equivalence boot (identity and notes, firmware
start, common init 285/285, TX/RX within the seen variance); then one
boot that makes the unforced rate visible (TX-done rate field restored
for one measurement, 0255 variant with fixed-rate management as the
control); then one boot measuring passes per second with data
submissions capped at one per pass; then the receive-direction DMA on the
reproducible tree. The receive-direction fragment line is reverted until
then; the transmit direction stays admitted, as booted.

# Historical: transmit DMA passed on boot 2; the receive-direction build is next

[Transport record §6](HIF_TRANSPORT_ANALYSIS.md#6-transmit-dma-boot-1-2026-10-24-a-composition-defect-not-a-driver-result):
boot 2 (`9d276157`, boot2 `b9afec4d…`, mainline `6227a6ba…`, returned to
Gemian `af51145e…`) attached the channel (`attached=1 selector=0x11403200
addr2=1 tx=1 rx=0`) and moved all 3,712 data frames by DMA with zero
failures and the completion flag set before the first poll; TX 2.69 and
RX 7.04 Mbit/s stay in the baseline band as predeclared. The transmit
direction's addressing, programming and completion handling are
established; nothing about receive or throughput is. Next build: the
lifecycle fragment admits the receive direction
(`CONFIG_MT6797_HIF_DMA_RX=y`) and 0260 is amended to log the skipped
attach case; the device tree stays the inherited tree with the channel
(composer parent: the boot-2 candidate). Predeclaration in the record.
Scalars:
[`results/transport-dma-runtime-scalars.json`](results/transport-dma-runtime-scalars.json).

# Historical: transmit-DMA boot 1 never attached (device tree); boot 2 installed and armed

[Transport record §6](HIF_TRANSPORT_ANALYSIS.md#6-transmit-dma-boot-1-2026-10-24-a-composition-defect-not-a-driver-result):
boot 1 (`9d276157`, boot2 `42b6e52b…`, mainline `bc582fa7…`) ran the
protocol with a complete log and reproduced the baseline (TX 2.62, RX 6.91
Mbit/s), but the candidate composer had built the image with the parent
candidate's `board.dtb`, which has no `wifi-hif-dma` entry, so the channel
was never attached (`HIF DMA transfers: tx=0 rx=0`). Nothing about the DMA
programming is established. The same check found that every Wi-Fi boot
since 2026-10-17 has used one inherited device tree that no build
reproduces and that carries three `consys` properties absent from every
DTS patch; reconciling the series with the booted tree is a roadmap item.
Boot 2 is staged with the only change being that tree plus the channel
entry: candidate `ced3a0f3…`, boot2 `b9afec4d…` over `42b6e52b…`, written
from Gemian `af1b8d18…`, full readback verified, device shut down, watcher
armed; predeclaration as for boot 1. Device returned to Gemian
`af1b8d18…` after boot 1. Scalars:
[`results/transport-dma-runtime-scalars.json`](results/transport-dma-runtime-scalars.json).

# Historical: the transmit-DMA boot is installed and armed; the owner boots it

Proposals 0258–0260 (AP-DMA channel 0 for the HIF data ports, transmit
direction admitted by the lifecycle profile) are built as `9d276157`,
composed, bound, reviewed and installed on boot2 (`42b6e52b…` over
`0663f1a9…`, written from Gemian `04d5197a…`, full readback verified);
the device is shut down and the watcher waits for the USB endpoint. The
boot runs the five-chunk one-lifetime protocol. Predeclared: the attach
record names the channel and the selector; every ordinary data frame of
at least 64 bytes goes out by DMA with zero failures; transmit and
receive rates unchanged (transmit is air-bound, receive still PIO). A
pass clears the channel's addressing and programming for the receive
direction (one build option, the next boot); DMA failures or data frames
no longer acknowledged while management frames are stop that path until
the address-extension semantics are resolved. The host fixture for the
transfer passes (`tests/run-hif-dma-test.py`). The keep-alive patch is
rebased on the DMA tree and held.

# Historical: the transport is the ceiling; see the structural analysis

[Structural analysis](HIF_TRANSPORT_ANALYSIS.md): the receive path is a
word-at-a-time PIO poll from the same worker that transmits (about 400
bus operations per frame), where the vendor driver takes an interrupt,
reads per-queue frame counts and lengths in one enhanced status read, and
moves the bytes with the AP DMA engine in one aggregated read per burst;
the sealed logs (device receive rate per chunk, CPU idle, no loss) and a
fresh vendor control (45 / 38.5 Mbit/s) agree that the worker, not the
air, is the receive ceiling. Transmit is capped by the forced 6 Mbit/s
rate; the station record and BSS info match the vendor's legacy-only
shape field by field, so the unforced-rate failure is upstream of the
host inputs except for QoS/HT declaration. The idle-link loss is not a
record difference either. Next: transport first (interrupt, enhanced
status, aggregated DMA reads), then QoS as the rate variable, the
keep-alive workaround, the lifecycle gates.

# Historical: RX-fix negative (0256 retired); the receive mechanism is unidentified

[RX re-baseline record](RX_REBASELINE_RESULT.md#rx-fix-boot-0256-retired-the-order-inside-the-pass-is-not-the-mechanism):
serving the receive port before submission engaged on 1,586 passes and
changed nothing (RX 7.23 host-side, 11.3–12.7 device-side; TX 3.27–3.38
per chunk). The logs show the receive direction submits at most one
acknowledgment per pass, so neither 0236 change can engage there, its
page budget is host-only, and 0243/0247 add no per-frame work; every
segment is received once. The 16–18 → 11–12 Mbit/s per-chunk receive
drop since the pipelining boot has no identified mechanism. Device
returned to changed-boot Gemian `04d5197a-9d8f-46b3-beab-d08c52cda99e`;
the 0256 image is still on boot2 and will be replaced.

Next: the owner's call between receive-path instrumentation on the same
image (frames per pass, read time, pass cadence) and a boot of the
pre-pipelining station tree plus 0236 alone; the capped-submission variant
cannot engage in the receive direction. Then the host-side keep-alive
(null-data admission, a workaround with a stated cost), the three-cycle
lifecycle boot, the access-point-loss boot on 0254 with its predeclared
meaning of loss while keep-alives are sent.

# Historical: rate-2 negative (0255 retired); the RX-cost fix is the next boot

[Rate-2](TX_AUTORATE_RESULT.md): with the vendor's own data descriptor (no
fixed-rate bit, zero rate word) every ordinary data frame still completed
with status 3 while every fixed-rate frame completed with status 0, so the
block is in what the firmware derives from the station record, not the
descriptor; 0255 retired. Device returned to changed-boot Gemian
`78b5c75b-5a8b-4598-9b7e-61acbf0f35e9`; the 0255 image is still on boot2
and will be replaced by the next candidate.

Next, one variable per boot: (1) the RX-cost fix: serve the receive port
before submission in the pipelining pass (depth, page budget, credit model
and admission untouched), both directions against 6.99 / 3.198; if RX does
not recover, cap submissions per pass as the second variant; (2) the
host-side keep-alive (a narrowly admitted null-data frame in mac80211's own
keep-alive shape), a workaround with a stated cost; (3) the three-cycle
lifecycle boot; (4) the access-point-loss boot on 0254, whose
predeclaration must say what a lost access point means while the host is
sending keep-alives.

# Historical: RX re-baseline measured; the rate boot (0255) is next

[RX re-baseline](RX_REBASELINE_RESULT.md): on the installed lifecycle image,
five chunks both directions, one lifetime, RX 6.99 Mbit/s host-side and
10.5–12.0 device-side per chunk, TX 2.76 (chunks 3.16–3.49). The receive
level since pipelining (7.0–7.6 / 10.5–14 on four boots) against 9.9–10.0
/ 16–18 before it is reproducible: pipelining cost about 30 % RX; the link
is not the explanation; cycle 2's 5.54 stays one unexplained low run.
Device returned to changed-boot Gemian
`c9fa4427-c705-4ad2-8426-1b26d205b0e9`. Boot 10's idle loss is recorded as
a finding: idle, the link is lost after about six minutes; a host-side
keep-alive is a separate queued variable.

Next: the rate boot, proposal 0255 (build `4a37c041`), then the RX-cost
experiment (bound submissions per pass when the receive port has pending
frames), the three-cycle lifecycle boot, the access-point-loss boot.

# Historical: lifecycle boot 10 refused by the host harness; RX re-baseline next

[Lifecycle result](LIFECYCLE_RESULT.md): boot 10 (lifecycle tree + 0254,
boot2 `87d7b532…`, three planned cycles) measured nothing: the retained
parser behind the helper admits two cycles at most and exited before any
exchange; fixed in the harness. While the leaf waited, the firmware
reported an air-class connection loss after 367 s idle and the driver took
the loss path cleanly (data end, cleanup, re-arm); whether that is the
access point's inactivity timer or a missing keep-alive is open. Device
returned to changed-boot Gemian `605bbbd1-7efb-4f95-b329-aba26c1a08f5`;
the 0254 image remains installed.

Next, one variable per boot: (1) RX re-baseline, the five-chunk protocol
both directions, one lifetime, on the installed lifecycle image, to answer
whether pipelining cost receive throughput (10.01 → 7.63 → 7.11 → 5.54
across boots) or the link varies; (2) rate, proposal 0255 (ordinary data
descriptors with no fixed rate and a zero rate word, as the vendor data
path builds them; 0242 had left the rate code without the enable bit)
against 3.198 Mbit/s; (3) the three-cycle lifecycle boot; (4) the
access-point-loss boot on 0254.

# Historical: lifecycle boot 9 sealed two lifetimes in one complete log

[Lifecycle result](LIFECYCLE_RESULT.md): on the lifecycle-7 image (boot2
`10a1b156…`) with two chunks per direction, boot `b4be0086…` ran two
complete station lifetimes with the driver's re-arm between them (cycle 1
TX 2.86 / RX 7.11, cycle 2 TX 2.48 / RX 5.54 Mbit/s), the sealed log is
complete (1.41 MB) and the classifier passes all nine gates. The plan's
second-lifetime item is closed. Device returned to changed-boot Gemian
`c73da941-e073-4de7-9edb-4ca8df2122c9`; the lifecycle-7 image remains
installed.

Next: the access-point-loss test needs a driver change first. The driver
admits one scan per lifetime and fail-stops a lifetime whose scan mac80211
does not follow with a join within ten seconds, so the first scan after a
loss would end the boot; proposal 0254 (build `d838628f`) retires the idle
scan's BSS, hands back the lifetime count and re-opens the scan instead,
and answers a scan request during a live scan with a quiet -EBUSY. That
image is installed on boot2 (`87d7b532…`, predecessor `10a1b156…`,
written from Gemian `c73da941…`). Lifecycle boot 10 runs it with three
supplicant-driven lifetimes and one chunk per direction (so three
lifetimes fit the logger limit): it answers whether a third lifetime is
admitted and whether 0254 is inert on the normal path. Then lifecycle
boot 11, the loss test proper (cycle 1 ends by the owner cutting AP
power, the driver's loss report, idle scans while the AP is away, a
second measured lifetime after it returns), then general operation.

# Historical: lifecycle boot 8 measured two lifetimes; a complete log is still owed

[Lifecycle result](LIFECYCLE_RESULT.md): both cycles passed on the host
(cycle 1 TX 2.46 / RX 5.59, cycle 2 TX 1.68 / RX 3.91 Mbit/s) and the
device ran two lifetimes with the re-arm between them, but the device
logger's 2 MiB limit cut the sealed log inside lifetime 2's data phase,
so the classifier cannot see that lifetime's teardown. Device returned to
changed-boot Gemian `d2f7adf3-339e-49af-878d-fc741bdad1cd`; the
lifecycle-7 image (boot2 `10a1b156…`) remains installed.

Next: a larger logger limit (or demoted per-frame records) for lifecycle
runs, one confirming boot of the same image with a complete sealed log,
then the AP-off loss test.

# Historical: lifecycle boot 7 ran two lifetimes on the device; harness bounds next

[Lifecycle result](LIFECYCLE_RESULT.md): with 0248–0253 the driver
re-armed after its first lifetime and ran a complete second one (scan,
grant, join, keys, data phase with DHCP and pings, teardown), then
re-armed again. The host's cycle-2 measurement did not run because the
per-cycle exchange must begin within 5 s of the PM credit clock, which
the second cycle missed by about 6 s, and the classifier expects exactly
one re-arm. Both are harness contracts. Device returned to changed-boot
Gemian `ca90fb06-5313-4e55-9b75-e7d4b65d97c5`; the lifecycle-7 image
(boot2 `10a1b156…`) is the installed predecessor.

Next: widen the second cycle's admission bound and accept the trailing
re-arm in the harness, re-run the same image for the measured second
lifetime, then the AP-off loss test.

# Historical: lifecycle boot 6 stopped on an expired data slot; 0253 next

[Lifecycle result](LIFECYCLE_RESULT.md): on the weakest link of the
series a data frame produced no TX status within its 750 ms slot
deadline and the worker ended the lifetime twelve seconds into the data
phase, before any re-arm gate was reached. 0253 retires an expired slot
as a lost frame (reported unacknowledged, counted with the consecutive
failures that end the data phase). Device returned to changed-boot Gemian
`e55151bd-490f-44f8-bbfe-26ffb2937f65`; the lifecycle-6 image (boot2
`96bf3ce7…`) is the installed predecessor.

Next boot: lifecycle-7 (lifecycle tree + 0253) under the two-cycle
harness, then the AP-off loss test.

# Historical: lifecycle boot 5 refused the re-arm as a PID wrap; 0252 next

[Lifecycle result](LIFECYCLE_RESULT.md): with 0251 both key removals were
seen and the re-arm was requested, but the readiness check refused it as
a wrap because the join PID counter, synced from the cyclic data PID
pool, stood at 82; boots 3 and 4 had passed that clause by luck. 0252
drops the clause. Device returned to changed-boot Gemian
`9b35a4fa-ef15-4ac0-a276-298a887a6f2f`; the lifecycle-5 image (boot2
`33e1f785…`) is the installed predecessor.

Next boot: lifecycle-6 (lifecycle tree + 0252) under the two-cycle
harness, then the AP-off loss test.

# Historical: lifecycle boot 4 joined its second lifetime; a late key removal closed it; 0251 next

[Lifecycle result](LIFECYCLE_RESULT.md): with 0250 the second lifetime
scanned, joined, associated and activated, then its handshake failed
because mac80211's second key removal landed 170 µs after the re-arm had
reset the epoch and closed the new receive path. 0251 defers the re-arm
until both key removals have been seen. Device returned to changed-boot
Gemian `3f113be8-5bf7-457a-a6eb-29637d099d00`; the lifecycle-4 image
(boot2 `e65967a1…`) is the installed predecessor.

Next boot: lifecycle-5 (lifecycle tree + 0251) under the two-cycle
harness, then the AP-off loss test.

# Historical: lifecycle boot 3 re-armed; second scan refused a notice; 0250 next

[Lifecycle result](LIFECYCLE_RESULT.md): with 0249 the re-arm fired and
the second lifetime began, but its scan was refused when the firmware's
BSS absence/presence notice (id 0x11) arrived during the scan: the scan
consumer treats any unknown event as a protocol fault. 0250 admits that
notice in the scan path, as 0243/0247 did for the join path. Device
returned to changed-boot Gemian `cd90a4fb-d0d6-464d-b635-cb75b0f61aca`;
the lifecycle-3 image (boot2 `2bd8396d…`) is the installed predecessor.

Next boot: lifecycle-4 (lifecycle tree + 0250) under the two-cycle
harness, then the AP-off loss test.

# Historical: lifecycle boots 1 and 2 ran one lifetime each; 0249 next

[Lifecycle result](LIFECYCLE_RESULT.md): boot 2 (0248) repeated boot 1:
cycle 1 passed, then no re-arm record of any kind. The cause is the
key-removal callback's synchronous cancel of the join worker 11 ms after
the stage-3 terminal, which discards the re-arm pass the terminal had just
queued while its pending flag stays set. 0249 re-queues the pass after
that cancel. Device returned to changed-boot Gemian
`c5c2c830-6bc4-48b1-8841-aa81f53c2383`; the lifecycle-2 image (boot2
`76adce93…`) is the installed predecessor.

Next boot: lifecycle-3 (lifecycle tree + 0249) under the two-cycle
harness, then the AP-off loss test.

# Historical: lifecycle boot 1 ran one lifetime; re-arm never requested; 0248 next

[Lifecycle result](LIFECYCLE_RESULT.md): cycle 1 passed in full (TX 3.11,
RX 6.60 Mbit/s, teardown complete, 0241's loss-reason record present),
then the driver never queued the re-arm pass: the station-removal callback
still gated it on the stable epoch being off and on the old two-lifetime
cap, and 0240 had unlocked only the worker's site, which runs no pass
after a retired terminal. Proposal 0248 fixes the callback. Device
returned to changed-boot Gemian `af877fc7-8235-4b32-b57e-08e6360c9c15`;
the lifecycle image (boot2 `10978b3c…`) is the installed predecessor.

Next boot: lifecycle-2 (lifecycle tree + 0248) under the same two-cycle
harness, then the AP-off loss test.

# Historical: autorate negative and retired; lifecycle (two lifetimes) next

[Autorate result](TX_AUTORATE_RESULT.md): with the descriptor's fixed-rate
bit cleared, no ordinary data frame was acknowledged (four DHCP discovers,
TX status 3 each) while every fixed-rate frame in the same lifetime
succeeded; the teardown completed. 0242 and its profile are retired; the
rate lever moves to the station record's transmit parameters, to be read
against the vendor driver before another boot. Device returned to
changed-boot Gemian `c977624f-203f-487f-a31e-8d0125ffe654`; the autorate
image (boot2 `08a930e8…`) is the installed predecessor of the lifecycle
image.

Next boot: lifecycle (pipelining tree + 0240, 0241, 0243; two lifetimes
in one boot under the two-cycle host harness), then the AP-off loss test.

# Historical: pipelining measured TX ×2.6; autorate next

[Pipelining result](TX_PIPELINING_RESULT.md): submitting every admissible
data frame per worker pass took TX from 1.225 to 3.198 Mbit/s (chunks
within 4 %), median completion gap 0.61 ms; RX 7.63 against 10.01, not
attributed on one run. The teardown completed with 0243/0247 in the tree
(absence notice admitted after the credit; no refusal). Device returned to
changed-boot Gemian `f0e12505-a599-410e-9319-a5e2f9f69bb5`; the pipelining
image (boot2 `ec96eb96…`) is the installed predecessor of autorate.

Next boot: autorate (pipelining tree + 0242, firmware-selected rate for
ordinary data frames), then lifecycle. Key reuse, rekey and reconnect
remain disabled until the lifecycle boot.

# Historical: flow-control measured negative and retired; pipelining next

[Flow-control result](TX_FLOW_CONTROL_RESULT.md): holding the mac80211
queue (0235) lost a fifth to a quarter in both directions (TX 0.922,
RX 8.10 Mbit/s against 1.225 / 10.01 on station-3) and its teardown
fail-stopped when a BSS absence notice arrived before the stage-2 credit.
0235 and its profile are retired; 0236 is rebased onto the station tree;
0243 (notices outside the window are counted) joins every measurement
series; 0247 removes the last content refusal and logs a refused body.
Device returned to changed-boot Gemian
`54cfeeb8-c0d8-4b0d-a016-d8d74844de1b`; the flow-control image
(boot2 `8d52e5c3…`) is the installed predecessor of the next candidate.

Next boot: pipelining (station tree + 0236 + 0243 + 0247), then autorate,
lifecycle. Key reuse, rekey and reconnect remain disabled until the
lifecycle boot.

# Historical: station-3 completed its teardown; flow-control next

[Station result](TX_STATION_RESULT.md): station-3 (0245, 0246, 8 MiB ring)
repeated the throughput (TX 1.225 Mbit/s, RX 10.01 Mbit/s, median gap
1.16 ms) and completed the whole close: standard disconnect, host
acknowledgment accepted, PM abort, deauthentication delivered, cleanup
stages, key removals, slots retired, native return to changed-boot Gemian
`4ad62c4b-e0a1-4575-b9ac-23d85ab3c30d`. The single build arm is the
foundation for the measurement boots that follow.

Next boot: flow-control (station tree + its series), then pipelining,
autorate, lifecycle. Key reuse, rekey and reconnect remain disabled until
the lifecycle boot.

# Historical: single arm measured neutral; station-3 next with 0245 and 0246

[Station result](TX_STATION_RESULT.md): the consolidated single build arm
matches or beats the tree it came from (TX 1.192 Mbit/s, RX 9.85 Mbit/s,
median completion gap 1.11 ms). Station-1 never reached Wi-Fi (leaf read a
removed parameter, fixed by 0239). Station-2 ended early on two host-chosen
limits: the 1 MiB kernel ring wrapped past the leaf's data-window marker
(single-arm profiles now boot with an 8 MiB ring; 0246 demotes the two
per-frame slot lines) and the 4,096-pass lifetime quota ended the lifetime
before any teardown command (0245 removes it). Device returned to
changed-boot Gemian `135292c1-d711-46a4-855f-2ed92b3ff6c7`. No retry.

Next boot: station-3 (station profile + 0245 + 0246 + 8 MiB ring), expected
to repeat the throughput and complete the teardown with the host
acknowledgment accepted; then flow-control, pipelining, autorate, lifecycle.
Key reuse, rekey and reconnect remain disabled until the lifecycle boot.

# Historical: quiet-console measured; single-arm station candidate next

[Quiet-console result](TX_QUIET_CONSOLE_RESULT.md): with the driver unchanged
and only the serial console quieted, the median gap between TX completions
fell from 8.2 ms to 1.05 ms and the 12–25 ms population almost vanished;
TX 1.044 Mbit/s (+19 %), RX 8.02 Mbit/s. The remaining TX limit is the data
queue freeing the ninth frame unsent (proposal 0235 next). The run exposed a
teardown defect: a receive record framed for the other monitor state right
after the data-end monitor-control disable fail-stopped the lifetime before
any teardown command; proposal 0238 drops such records after data end.
The session host refused export (quiescence query exit 63); a separate
reviewed preservation sealed the complete log and returned the device to
changed-boot Gemian `d2d47ea1-90df-4845-9e8c-8ac1b1dff2b0`. No retry.

Next boots, one variable each, all on the retained kernel release string:
`mt6797-a53-wifi-station` (0234 single build arm + 0237 proven monitor
control + 0238; expected: same throughput as quiet-console, teardown
completes), then pipelining (+0236), then
`mt6797-a53-wifi-pipelining` (+0236). Key reuse, rekey and reconnect remain
disabled. Earlier handoffs below are historical and consumed.

# Historical: progress-aware yield installed; physical boot2 pending

[Depth-four result](TX_DEPTH_RESULT.md): TX 0.506 Mbit/s, RX 7.061 Mbit/s,
idle 84.3% / 77.3%, peak four owners, whole-ledger cleanup and status-0
transmitted deauth. Reviewed return independently confirmed changed-boot Gemian.
Consumed, no retry. Its measured TX gap clusters are approximately 4.2/31.8 ms.

[Yield comparison](TX_YIELD_COMPARISON.md): patch 0233 resets the no-progress
guard on successful frame submission or matched completion retirement. After
32 no-progress immediate iterations, pending work requests 1 ms; genuinely idle
work retains 20 ms. Existing HZ=250 means a one-jiffy nominal 4 ms short yield.
Depth four, fixed-rate descriptor, ledger, PID attribution, deadlines,
admission, management and key ownership remain unchanged. Actual-source
fixtures, ASAN/UBSAN, strict checkpatch and repository checks pass.

Validated build `1a4f291e` has byte-identical configuration to depth four.
Full boot2 `8014a0dd67c5cf5641ef4134fa5412bba971a4c93c095d48c60f02a95051ccae`
was written/synced/flushed and fully read back with matching SHA-256. Gemian
clean shutdown confirmed unreachable. Both offline constructors pass using
the genuine receipt; candidate and sealed host hashes verified at this
physical-handoff stage. No yield measurement has run; one attempt unconsumed.

Runtime `artifacts/wifi-throughput-yield-1`. After owner boot2 selection,
root launches `artifacts/wifi-tx-yield-work/hosts/throughput-run.py` with that
runtime and `--execute` exactly once, using Python 3.13. Live identity precedes
firmware start; five 1 s/1 MiB chunks per direction, prompt standard disconnect,
seal/export and reviewed return. Compute first-class gap histograms with
`summarize-throughput-completion-gaps.py` using the matching within-chunk filter.
Falsifiable TX target 2.5–3 Mbit/s; report partial/unmet result honestly.

Root retains device custody and final records; harness and analysis delegated.
No retry, rate change, DMA, rekey or protected re-arm. Reconnect closed,
safeguards dormant. Rate adaptation remains a separate following pass.

# Historical handoff: baseline 2 measured; bounded TX pump comparison

[Baseline 2 result](THROUGHPUT_BASELINE_2_RESULT.md): TX five chunks,
0.205740 Mbit/s, 87.525% aggregate idle, 959 completions/four nonzero.
RX unmeasured: inherited regular-file limit; offline streaming counter and
preflight fix pass. Prompt standard disconnect, whole-ledger stage 3 and
status-0 reserved deauth passed. Sealed evidence and independent changed-boot
Gemian confirmed. Baselines 1/2 and P2E-D1/D2 consumed, no repeat.

[Pump comparison](TX_PUMP_COMPARISON.md): patch 0231 adds bounded immediate
scheduling for pending work, idle/guard backoff 20 ms, at most 32 consecutive
immediate iterations. No depth, ledger, PID, deadline or admission change.
Default off except the new measurement profile. Validated Buildbox build
23745fe9 differs in config only by pump=y; RAM/DT unchanged. Final protocol:
five 1 s/1 MiB-cap chunks per direction, 100 ms gaps, nc data and SSH control;
2 MiB logger unchanged. Thirteen host fixtures and four retained-BusyBox
loopback cases pass. Exact candidate/readback and real receipt checks must
precede the one physical pump boot. DMA deferred; reconnect closed.

# Historical handoff: invalid baseline recorded; corrected run prepared offline

[Baseline 1](THROUGHPUT_BASELINE_RESULT.md) is invalid (SSH idle policy); no
rate claim. The independent first connection-loss teardown did not retire its
ledger. The [offline audit](LOSS_PATH_TEARDOWN_AUDIT.md) reproduces a driver
waiter candidate against actual installed source; firmware dropping group
removal is unproved because the host stopped before its credit bound expired.

[Corrected baseline 2](THROUGHPUT_BASELINE_2_PREDECLARATION.md): five 10 s/1 MiB
chunks per direction, chunk progress plus independent SSH keepalives, direction
CPU/netdev snapshots, prompt single EOS/quiescence-guarded standard disconnect,
honest whole-ledger/delivery verdict, seal and reviewed return. Ten measurement
fixtures and the actual-source waiter fixture pass; actual capture/session
constructors and installed-image input validation pass offline. One new boot
authorized by the owner's correction, no rebuild/image change; physical boot2
selection remains required. No retry of baseline 1 or either P2E run.
Reconnect closed, safeguards dormant; TX DMA still held on its contract.

# Historical handoff: PIO baseline consumed; returned to Gemian

[Baseline result](THROUGHPUT_BASELINE_RESULT.md): one unchanged-image boot,
join/DHCP/three pings/authentication passed. TX was interrupted by the retained
SSH server's 30-second idle policy: 842312 received bytes in 31.067 s,
invalid stalled transfer; no rate claim; RX and CPU idle unavailable. Missing EOS withheld the
standard disconnect. Later connection-loss teardown transmitted reserved
deauth status 0 but stopped on group-removal credit debt (-110); no whole-ledger
stage 3. Evidence sealed and independently rehashed; reviewed return and
independent changed-boot Gemian confirmation passed. No retry, build or image
change. The boot allowance is consumed; no further device action queued.
Reconnect remains closed, safeguards dormant. TX DMA remains refused on the
[unresolved transfer contract](DMA_TRANSFER_CONTRACT.md). Earlier handoffs below
are history, not an active test queue.

# Historical handoff: PIO baseline prepared; physical boot2 selection pending

[Predeclared throughput baseline](THROUGHPUT_BASELINE_PREDECLARATION.md): one
fresh boot, unchanged installed `3da69187` / boot2 `5f63e2d32fc0...`; join,
DHCP/three pings/SSH, device TX then RX up to 60 s each, software CPU/netdev
boundary counters, one EOS-guarded standard disconnect, whole-ledger stage 3,
sealed export/regression and reviewed return. Offline fixtures/constructors pass;
full installed-partition checksum verified read-only. No image change or build.
Prepared runtime: `artifacts/wifi-throughput-baseline-1`. One attempt only.

Reconnect is closed as a limitation, not a pending task. Do not reopen without
owner decision; 0229/0230 stay dormant. [DMA transfer contract](DMA_TRANSFER_CONTRACT.md)
requires refusal on unresolved bit-32 routing, ownership and error quiescence;
TX DMA implementation and comparison boot are held. RX DMA remains separate.
The baseline consumes the standing allowance only when executed; no baseline
result is claimed before the physical boot. P2E-D1/D2 remain consumed.
Earlier handoffs below are history, not an active test queue.

# Current handoff: probe pass closed; single-lifetime fallback and DMA/throughput next

[Probe-path result and authorized fallback](OBSERVABLE_RECONNECT_DECISION.md):
actual source rejects protected QoS-null in the native encoder; the sole internal
reserved owner blocks later data/deauth and reports completion as deauth. New
mechanisms would be required, so the one-pass timebox is closed. No admission
change, rebuild, install or boot. Retain the single-lifetime baseline; 0229/0230
stay dormant. No further reconnect design or WMT lifecycle work is pending.
The next Wi-Fi project is DMA/throughput under the roadmap. The one-boot
allowance remains unconsumed; P2E-D1/D2 remain consumed. Earlier handoffs are
history, not an active test queue.

# Current handoff: negative credit boundary; provider re-probe unavailable

[Offline boundary audit results](FIRMWARE_RESTART_BOUNDARY.md): released pages
precede key events by 5.059/1.079 ms; no credit/drain retirement proof exists.
No firmware stop/off counterpart is implemented. MAC `.stop` is host-only and
"firmware stopped" is a retained-state log. Provider re-probe was evaluated
first and refuses the retained `bound` owner; the built-in provider has no
remove lifecycle and suppresses bind attributes. NIC cycling keeps firmware
running and is not a boundary. New WMT stop/off work needs an explicit owner
decision and has not started. No available boundary today, no restart run
predeclared, no command, rebuild or boot. Reuse/rekey/re-arm stay refused;
0229/0230 remain dormant. The one-boot allowance remains unconsumed.
Earlier checkpoints below are historical.

# Current handoff: dormant host prerequisites; firmware decision pending

[Two offline tracks](TWO_LIFETIME_OFFLINE_TRACKS.md): 0229/0230 add unconsumed,
default-off host fence and PN-epoch helpers. Actual-source fixtures pass; no
admission or descriptor-provenance capability is added. The owner is producing
the four-handler event/credit, timer-cancellation and queue-flush evidence table.
Until it resolves, re-arm stays refused. No commands, build, installation or
boot; the one-boot allowance remains unconsumed. P2E-D1/D2 remain consumed.
Earlier checkpoints below remain history, not an active physical handoff.

# Current handoff: two-lifetime offline gate held before build

[Incomplete offline admission](TWO_LIFETIME_PREDECLARATION.md): actual-source
fixtures reproduce untagged key-event and old-descriptor attribution gaps if
protected reuse is enabled without a producer-retirement boundary. No production
re-arm, kernel build, candidate, installation or device action occurred. The
installed kernel remains `3da69187`; any eventual candidate needs a rebuild with
0228. No boot allowance is consumed and no physical selection is pending.
Reconnect remains open. P2E-D1/D2 remain consumed; do not repeat them.

# Current handoff: P2E-D2 complete; no further P2E boot

[Recorded result and offline follow-up](SESSION_0202_PLAN.md#p2e-d2-consumed--600-second-gate-pass-delivery-transmitted-cleanup-pass):
gate600s PASS, delivery status 0 TRANSMITTED, guarded disconnect refused by the
host interval, cleanup stage 3 whole ledger PASS. D1 and D2 are consumed; never
repeat either. Installed kernel/image are unchanged. The next device item is
an owner decision. [Second-lifetime prerequisites](SECOND_LIFETIME_PREREQUISITES.md)
remain offline. Earlier handoffs below are history, not a pending boot queue.

## Current: owner paused all work — status checkpoint

All implementation, builds and device work are paused at the owner’s request.
No device action or physical boot handoff is pending. Earlier handoffs below
are historical and consumed; do not execute them as current instructions.
P2E-1 stopped on host orchestration before Wi-Fi was reached. Its evidence is
preserved and the reviewed return independently confirmed changed-boot Gemian
`0d88c2d5-b21e-47fe-bf39-c95e896f724a`.

The fail-closed launcher correction is committed and Linux-validated; no further
attempt has run. Ten-minute received-traffic acceptance and same-boot reconnect
remain unproven. Key reuse, rekey and protected reconnect remain disabled.
Unrelated restored research is excluded from this status checkpoint.

---

## Latest: P2E-1 consumed — host launch failure, return confirmed

[One result row and analysis](SESSION_0202_PLAN.md#p2e-1-consumed--outer-launch-failure-and-late-start-refusal)
and [scalars](results/p2e-runtime-scalars.json) record the admitted attempt.
The added identity reader failed locally on a missing output directory; the
outer shell continued instead of failing closed. Bootstrap completed under the
capture's independent identity checks, but the leaf refused its existing
whole-second start limit before scan or any protected lifetime. SSH was never
reached. This is a host result, not evidence against the driver or a P2E pass.

All 61 seal entries, 1,978 contiguous log records, host quiescence and regression
verified before the original reviewed return. A separate authenticated check
confirmed changed-boot Gemian. No manual abort, retry or second recovery ran.

`laptop-run-ccmp-p2e.py` now replaces the ad hoc launch: create the identity
output first, fail closed on any acquisition/identity error, pass only the
fresh boot ID to the helper before bootstrap, and invoke the original failure
session once if capture refuses. It retains the original whole-second <=50
guard and every transport/data deadline. Local launcher tests and an actual
offline constructor fixture pass. Clean pushed input `c37baf06` passed all ten
launcher tests on Linux with no skips, including the actual retained collector
and a local child. The full Linux repository check passed. The constructor used
a historical receipt as an offline fixture only; it establishes no live readiness.
See the [launcher validation record](results/p2e-launcher-validation.json).
No new device attempt or physical handoff is admitted by this checkpoint.

---

## Earlier: P2E host-only preparation — before device admission

The owner authorized the separate [P2E evidence successor](SESSION_0202_PLAN.md#p2e-host-evidence-successor--preparation-admitted-execution-held).
Its reader retains all 602 planned arrival timestamps plus one excess-arrival
sentinel, and its refused-disconnect record includes the already acquired
PM-relative offset and unchanged bounds. The consumed P2 source and evidence
remain intact. P2E uses fresh `capture-ccmp-p2e` and `session-ccmp-p2e` paths,
the unchanged P2 image/leaf/classifier, and the existing custody and recovery
contracts. No new kernel, installation or device run is admitted.

[Validation](results/p2e-host-validation.json) on clean pushed input `e59f9370`
passed all 31 client tests on Linux with no skips, including real pipes beyond
244 arrivals, all 602 planned timestamps, fragmentation, excess arrivals,
partial timeout retention, PTY custody and eight actual generated guard-boundary
subcases. The original reader's 244-entry defect reproduces independently.
Routing/custody fixtures select the exact new helper, keep both 900-second log
decoders and preserve refusal on unknown local/remote owners. Repository checks
passed locally and on the clean Linux checkout.

This is host preparation, not a hardware pass or a live handoff. No kernel or
image was rebuilt, no installation or device operation ran, and no P2E runtime
receipt exists. A later execution needs its own admission, current device
identity, guarded installation/readback of the unchanged P2 image, real receipt
preparation and owner physical boot selection. Do not reuse an earlier boot
selection or start a P2E session while execution is paused.

Key reuse, rekey and protected reconnect remain disabled pending the separate
firmware queued-RX/key-retirement barrier. The ten-minute gate is still unproven.

---

## Latest: P2 consumed — host-limited duration; healthy cleanup and return

See the [single result row/analysis](SESSION_0202_PLAN.md) and
[scalars](results/p2-runtime-scalars.json). P2 authenticated SSH and retained
602 valid raw chunks over a 601-second remote schedule, but its host receiver
kept only 244 timestamp entries. The required >=600-second host receive span
and continuity are unproven. All initial/59 periodic pings passed; no device
duration failure was measured. The later helper abort refused at its interval
guard, exit 49; the exact rejected offset was not retained.

The unchanged leaf wall ended data at 718.184 seconds. Whole-ledger stage 3,
zero debt and deauth ACK passed separately; all 75 seal entries and 4,992
contiguous log records independently verified. The original reviewed return
and separate authenticated changed-boot Gemian check passed. No device work
or retry remains pending for this consumed run.

Next, follow the owner's separate private collection task before another
Wi-Fi lifecycle test. Keep its static admission, candidate, boot and evidence
separate. A later P2 successor needs the real-runner timestamp cap corrected
and tested beyond 244 chunks; it is not implemented by this result checkpoint.
Key reuse, rekey and same-boot reconnect remain disabled; ten-minute acceptance
and maintained Wi-Fi remain incomplete.

---

## Latest: P2 installed — new physical boot2 handoff pending

P2 source `1bbcaad8` passed the relevant Linux actual-source helper, leaf,
verdict, loader/binding and installer checks, including the final cold-start
boundary. The reviewed installer verified the predecessor, wrote boot2,
required matching full-partition readback and confirmed clean shutdown.
Complete actual offline host preparation passed with the scoped 900-second
log contract. No P2 capture or session has run; earlier boot selections are
consumed.

The [P2 predeclaration](SESSION_0202_PLAN.md) requires >=600 seconds of received
authenticated SSH, 59 periodic probes and standard disconnect requested at
PM +604..608 seconds. The validated kernel is unchanged; only the USB script
and bounded observer differ from P1D's RAM root. Verify those live hashes,
kernel notes, a fresh boot UUID, uptime and active logger before the one
capture/session. The leaf refuses starts after whole-second uptime 50 and
reserves >=130 seconds for quiescence/export/sealing. A late start is a host
admission result; do not silently retry it.

A new owner-operated physical boot2 selection with USB connected is pending.
After P2 testing and preservation/return, proceed with the separately requested
private collection task before the next Wi-Fi lifecycle test. Its design and
admission remain separate. Key reuse, rekey and reconnect remain disabled;
full maintained-Wi-Fi acceptance remains incomplete.

---

## Latest: P1D passed — ten-minute host-envelope preparation next

P1D's [row/analysis](SESSION_0202_PLAN.md) and
[scalars](results/p1d-runtime-scalars.json) record the full admitted gate:
121.136 seconds received SSH, all initial/periodic pings, 167 completed PID
reuses, prompt standard disconnect and whole-ledger stage 3 with deauth ACK.
The post-client snapshot took 0.602 seconds. All 75 seal entries and 3,283
contiguous records independently verified. The original harness and a separate
authenticated check confirmed changed-boot Gemian after one reviewed return.
No P1D device operation remains pending.

Next is >=600 seconds of received SSH and standard disconnect. Audit in the
existing session plan identifies necessary host limits, including the USB
server's 360-second hard connection cap and the boot-started logger's
600-second deadline/exact verifier. Prepare those coherently before a new
image/boot. Reuse the validated kernel: measured driver counts project below
its current caps; no driver deadline or cap change is justified. There is no
ten-minute candidate or physical handoff yet. Key reuse, rekey, same-boot
reconnect, supported ordinary crypto and minimal board acceptance remain open.

---

## Latest: P1D prepared — new physical boot2 handoff pending

P1H's [row and analysis](SESSION_0202_PLAN.md) and
[scalars](results/p1h-runtime-scalars.json) are committed at `c1a100cb`.
The >=120-second received SSH gate passed; its prompt-disconnect gate failed
on a half-second host snapshot timeout. It later reached clean whole-ledger
teardown at the admitted leaf wall, with 167 completed ordinary PID reuses.

P1D host input `2da1f41b` corrects only that software snapshot envelope and
bounded terminal-wait USB progress. All 22 helper tests and actual leaf/gate
fixtures passed on clean Linux; syntax, ShellCheck, retained-source/binding
and repository checks passed. The kernel/package/profile and boot artifacts
are unchanged. The reviewed guard verified the matching full partition,
skipped writing, preserved a separate deployment seal and confirmed clean
shutdown. Complete actual offline host preparation passed.

One new owner-operated physical boot2 selection with USB connected is now
pending. No P1D device session has run; earlier selections are consumed.
Require a fresh UUID and the exact P1 kernel-notes identity before the one
capture and one session. This run still requires >=120 seconds of received
SSH and a prompt standard disconnect under the unchanged time/ownership
gates. Only after that gate passes proceed toward 600 seconds. Key reuse,
rekey and reconnect remain disabled; full usable-Wi-Fi acceptance is incomplete.

---

## Latest: P1H consumed — SSH duration passed; host control gate failed

See the [single row](SESSION_0202_PLAN.md) and
[scalars](results/p1h-runtime-scalars.json). SSH exited 0 with 243 chunks
received across 121.090 seconds; initial 3/3 and periodic 11/11 pings passed.
The next first failure was the source-pinned 0.5-second post-client USB
snapshot. Without a verified open-window snapshot the helper correctly sent
no disconnect. The full planned session remains FAIL.

The original host refused recovery while a child remained live. After the
admitted leaf wall, independent read-only observations confirmed quiescence.
Eventual supplicant teardown ended data at 298.704 seconds with deauth ACK,
whole-ledger stage 3, no debt and 167 completed ordinary PID reuses. All 90 seal
entries/3,283 contiguous records verified before one reviewed recovery. A
separate authenticated check confirmed changed-boot Gemian. No retry ran.

Next: correct only the host snapshot envelope and bounded terminal-wait USB
progress, retaining all driver/firmware/control-time gates. Validate the actual
host paths, then prepare a separate fresh boot handoff. The 120-second stream
is demonstrated; prompt standard disconnect remains the failed gate. No
600-second or same-boot reconnect claim is established.

---

## Latest: P1H ready; waiting for a new physical boot2 selection

The P1 result is committed at `24f9ba08`. The corrected host envelope and
its exact pins are pushed at `15d4cf5e`, with separate P1H deployment evidence
at `5cfb7b24`. The Linux actual-leaf/progress and binding checks, syntax,
ShellCheck, local retained-source/config fixtures and repository checks passed.
No kernel changed or rebuilt: boot artifacts and full boot2 checksum are
byte-identical to the installed P1 image. The guard verified that match,
skipped writing and confirmed clean shutdown; offline host preparation passed.

One new owner-operated boot2 selection with USB connected to the custodian
is pending. P1's earlier reply is consumed. There has been no P1H device test.
Require a fresh UUID, exact kernel-notes identity, one capture and one session.
The test still requires >=120 seconds of received SSH traffic, completed PID
reuse and standard disconnect. Stop at any earlier first failure, preserve it
and retain independent duration/network/cleanup verdicts. No private firmware
mechanism or offset-avoidance rule is inferred.

---

## Latest: P1 consumed; host maximum-duration defect

P1's [single table row](SESSION_0202_PLAN.md) and
[scalars](results/p1-runtime-scalars.json) supersede earlier pending handoffs.
It authenticated and received 116 ticks across 57.563 seconds, then the
server's retained `-M 60` limit closed SSH. The 120-second gate failed.
Standard early disconnect reached whole-ledger stage 3 with reserved PID 127
acknowledged at PM +64.189 s. Ordinary PID reuse was measured: 32 completed
reuses, all 158 allocations completed. Six periodic probes passed through
PM +60 s; the other five were not reached. No HIF refusal or monitor-loss event.

The original seal/recovery gate correctly refused a nonzero supplicant count.
After bounded read-only classification, a preservation-only continuation
revalidated child quiescence and all evidence before one reviewed recovery.
All 89 seal entries and 2,740 contiguous records verified. An independent
check confirmed changed-boot Gemian. There is no pending device operation.

Next: correct the host listener maximum-duration limit and USB progress
envelope on the unchanged installed P1 image, with focused actual-leaf tests,
then make a new explicit physical boot2 handoff for a separate 120-second run.
Do not count P1 as a duration pass or retry it silently. The exact +63-second
comparison remains unexecuted; offset correlations establish no timing rule.
Key reuse, rekey, reconnect and ten-minute acceptance remain unproven/disabled.

---

# Wi-Fi resume checkpoint — INCOMPLETE

**P1 installed and prepared; waiting for a new physical boot2 selection.**
Kernel input `71c4b4a8`, bindings `2ec08e59`, final host test `7dc1d496`.
[Current handoff](SESSION_0202_PLAN.md#p1-handoff-ready--physical-boot2-selection-pending).
All Linux source/host checks, twenty client cases including real PTY, the single
kernel build, package/composition validation, guarded installation/full readback,
clean shutdown and fresh host preparation pass. Full boot2 checksum
`f19d4e27bd24fc38b091c8847440c051f83e92da3972865125ae4c0a0589e998`;
[actual receipt](results/ccmp-stable-monitor-candidate-p1.json).
No P1 capture/session or result exists. Require a fresh mainline boot UUID and
exact 84-byte kernel notes
`b0213c37e6080b8b334f73842ca3162390cdfeecb29d8eb93bd41d2c2bf9b160`
before the one admitted run. Do not reuse the consumed I50 physical reply.
The P1 hypothesis is sustained initial-key traffic with completed ordinary-PID
reuse and standard disconnect: 243 absolute half-second chunks schedule 121 s,
requiring at least 120 s of live client receipt span, eleven periodic probes,
verified remote/local quiescence and whole-ledger/ACK cleanup. First failures,
including an early host abort, remain separate; no shorter-duration pass or
wire-generation/key-retirement inference. Full Wi-Fi acceptance is unfinished.

**I50 consumed once: duration/network/acknowledged cleanup PASS; SSH NOT REACHED.**
Boot `e8a4c5ca-1fda-42ad-a0f7-1b68e99c08f7`, kernel `00f351eb`, bindings
`eca5e7dd`, handoff `6908713d`. [One row and analysis](SESSION_0202_PLAN.md#i50-consumed--acknowledged-idle-tail-teardown-ssh-not-reached),
[one scalars file](results/i50-runtime-scalars.json). Data budget 50.005 s,
initial 3/3 and periodic 4/4 replies, release credit and whole-ledger stage 3
pass. Reserved deauth ACK followed a measured 10.099-second data-completion
idle gap; this weakens idle-only causation without identifying a mechanism.
The host helper refused the I50 namespace before client/TCP; no SSH result or
host ACK exists. The exact child-CLI guard is reproduced offline. The immutable
full-session verdict remains false. All 62 seals, 2,134 contiguous records,
eight available cycle frames, quiescence/regression and reviewed return verify.
Independent Gemian `0ad152bc-0456-4298-82d2-eb50d09ada81`. No pending physical
action or unchanged I50 retry. The narrow host admission correction and its
seven actual-main cases pass from clean pushed inputs on Linux.
[Connected-lifetime/PID/accounting/monitoring source](SESSION_0202_PLAN.md#connected-source-prepared--build-input-validation-pending)
has passed clean Linux source fixtures and the required kernel build.
[The real P1 package/candidate and host protocol](SESSION_0202_PLAN.md#p1-built-and-composed--complete-host-validation-before-deployment)
are composed and now pass clean Linux host checks, guarded deployment/full
readback/shutdown and fresh preparation, as recorded in the current handoff
at the top. No physical P1 selection has been consumed yet. Key reuse/rekey/reconnect remain
disabled and full Wi-Fi acceptance remains incomplete.

**S1 consumed once: controlled core disconnect and 20-second SSH stream PASS.**
Unchanged GTK8 image, boot `cff2c4f8-466d-406b-a7ad-d9f1e8bfee1e`; host inputs
`2a197328`, handoff `f12da769`. [One row and analysis](SESSION_0202_PLAN.md#s1-consumed--ssh-stream-and-standard-disconnect-pass),
[one scalars file](results/s1-runtime-scalars.json). DHCP, initial 3/3 and
post-release periodic 5/5 pings pass. Fresh authenticated SSH produced five
chunks spanning 20.450 seconds across the +6.252 s channel-release credit;
client exit 0, no stderr. Standard disconnect accepted near PM +55.6 s ended
data with reason `disconnect`, elapsed 55.502 s. This planned stop is not a
full 60-second duration pass. PM abort, acknowledged deauth and all remaining
cleanup commands completed; whole-ledger stage 3, zero debt, local disables 0.
No HIF refusal, capacity stop or 0x13 event. Owned-beacon admissions were stale;
no continuous-beacon claim. All 75 seals / 2,202 contiguous records, one-cycle
export, remote/local/device quiescence, regression and one reviewed return
verify. Independently confirmed Gemian `9dac50f6-816c-4c08-981d-79535cb56f69`.
No physical action or S1 retry is pending. No S1 kernel build/change occurred.

The I50 preparation/handoff and S1 successor plans below are consumed history;
use the current I50 result at the top. The connected-lifetime source archives are prepared but unbuilt; longer-window
admission still needs the source and host gates above.

**GTK8 consumed once: finite capability, post-release protected traffic,
60-second duration and whole-ledger host cleanup PASS.** Boot
`a996ec5e-fc20-49d3-a160-2ed321e3e156`, kernel `8792a406`, bindings `49ff0b1c`,
handoff `b9555ddf`.
[One row and analysis](SESSION_0202_PLAN.md#gtk8-consumed--protected-traffic-beyond-the-join-privilege),
[one scalars file](results/gtk8-runtime-scalars.json).

The 9,000 ms join privilege was submitted for release at PM +6.275 s and
credited at +6.300 s (25.016 ms, no deadline extension). All five periodic
probes replied beyond that credit and the original reported grant horizon;
owned successful data completions continued through PM +50.296 s. The window
ended by budget at 60,009 ms. DHCP, three initial pings and SSH exit 0 in
1.397 s passed. SSH authenticated **before** release and closed; no maintained
post-release authenticated stream is claimed. Checked PTK/GTK 42/231, GTK ARP
handoffs 106, withheld 0. No HIF refusal, capacity stop, pre-budget AP loss or
0x13 event. Standard scan acceptance remains open.

PM abort credited first; reserved deauth PID 40 still missed 750 ms and later
returned status 5 during removals. No ACK or invented refund. The ledger
returned whole at station removal; cleanup skipped a second channel abort and
credited BSS-off at floor zero. Host stage 3, zero debt, local key disables
status 0. This is host cleanup success, not acknowledged deauth or independent
firmware key/queued-RX retirement. Owned-beacon admissions were 21 total/20
since PM, last age 58.114 s; do not infer continuous beacon delivery or RF loss.

All 71 seals and 2,186 contiguous records, complete one-cycle export,
helper/device quiescence, regression and one reviewed return verify.
Independently confirmed Gemian `4f0120ad-fa64-462a-82d3-c2c3f9b0a30e`.
Two read-only identity invocations preceded the one capture/session: the first
used the SSH helper incorrectly and exited nonzero; the corrected stdin
invocation verified identity. No radio/session retry. No live device process
is pending for GTK8, which is consumed; S1 is also consumed as recorded above.

The S1 preparation/handoff above is historical and consumed; use the current
S1 result at the top for the next source decision.

Prior GTK7 result follows as history; its successor below is now consumed.

**GTK7 consumed once: capability and 60-second low-traffic duration PASS;
whole-ledger cleanup stage 3 reached, deauthentication still unacknowledged.**
Boot `138674d4-2aff-4ff5-ad75-a0670d432b36`, source `8aed6b61`, tooling
`cd1a81ef`, handoff `1cfeb81e`.
[One row and analysis](SESSION_0202_PLAN.md#gtk7-consumed--whole-ledger-cleanup-with-late-deauthentication),
[one scalars file](results/gtk7-runtime-scalars.json).

Data ended by budget at 60,011 ms. DHCP, initial three replies, SSH exit 0 in
1.618 s and all five periodic numeric-router probes passed. Checked PTK/GTK
41/238; GTK ARP handoffs 107, withheld 0; no named HIF refusal or 0x13 event.
Every owned TX completion and cleanup command timestamp is exported relative
to the 0x16 credit. No continuous SSH-traffic claim is made. Standard scan
acceptance remains open; the passive-scan classifier reports no standard BSS.

PM abort credited **before** reserved deauth. PID 41 still missed 750 ms and
was retired with one page debt, without ACK/refund. Removals proceeded under
the existing 100 ms bounds. The ledger returned whole during station removal;
late retired completion status 5 followed. Channel abort/BSS-off credited at
floor zero; healthy stage 3, `deauth=0`, both local disables status 0. This is
whole-ledger cleanup with an unacknowledged frame, not a bounded-debt terminal
or timely deauth success. PM-abort-first did not cure the missing completion;
periodic traffic also changed, so unique causal attribution is unavailable.

Owned-beacon admissions at data end: total 21, since PM 20, last age 58.162 s.
Do not claim continuous beacon delivery or infer RF loss from this counter;
phase-1 type-7 total 110 is not an owned-beacon count. All five periodic pings
replied, so the predeclared fixed-offset host-TX failure trigger did not occur.

All 71 seals, 2,185 contiguous kmsg records, complete one-cycle export,
helper/device quiescence and A53 regression verify. One reviewed return and
independent Gemian identity confirm `78b701cf-cb65-4283-bc32-dbe7dadb5497`.
GTK7 has no live device process or retry pending and is consumed; the new
GTK8 physical handoff is recorded above.
A default-off [connected-channel comparison](SESSION_0202_PLAN.md#after-gtk7--bounded-connected-channel-ownership-comparison)
is prepared under 0217: a nine-second join grant released during the unchanged
60-second window, original command/frame/tail limits, periodic traffic and
GTK7 teardown. Local and Linux actual-source/option-off/HIF fixtures and the required
Buildbox build pass at `8792a406`; [GTK8 package/host bindings](SESSION_0202_PLAN.md#gtk8-validated-package--host-binding-validation-pending)
are prepared from the validated package. Five host fixtures and the
strict post-release verdict pass locally and on Linux. Guarded installation
and offline host preparation now pass; physical GTK8 selection is pending
as recorded above. No GTK8 hardware observation is claimed. Two/ten minutes of authenticated SSH traffic and same-boot reusable
lifetimes remain unproved.

Keep 0x16 before keys, counter-only 0210/fatal event refusal, connection-monitor
flag, no nullfunc, existing frame/command deadlines and resource caps. No PID
or key reuse, rekey or reconnect. Keep publications on `main`; preserve public
measurements and exclude firmware-RE explanations/private source identities.

Earlier GTK6 command-path credit with one retained page and its whole-ledger
stop remain recorded in the [prior analysis](SESSION_0202_PLAN.md#gtk6-consumed--command-path-credit-with-a-retained-page)
and [scalars](results/gtk6-runtime-scalars.json). Do not repeat it unchanged.

GTK1's prior ERANGE is classified and its [0205 correction](../../patches/proposals/0205-wifi-mt6797-retain-the-validated-channel-grant-horizon.patch)
is proved to permit the requested data budget in GTK2. GTK1 had both keys
submitted/credited before refusal and lacked healthy cleanup; it did not test
GTK/network/SSH. Earlier intermittent SSH silence remains unclassified. D3 and
GTK2 both resolved an initially absent neighbor without proving how.

The [reviewer reassessment](SESSION_0202_PLAN.md#reviewer-reassessment-before-further-implementation-or-any-build)
corrects the all-`0xc200` premise: C11's 32 eligible groups required `0xc000`.
Expanded 2,718 actual-source cases and eleven paired-helper cases pass locally
and on Linux from clean pushed input `f45b7645`. The owner adopted group-first
preparation. The independent 60-second window and permanent standard client
stderr/netstat retention passed locally and on Linux at `5b92d39a`.
The strict initial-GTK context/checker is implemented under the
[predeclared source contract](MAC80211_GROUP_RX_CONTRACT.md#predeclared-initial-gtk-preparation).
Its actual-source fixtures pass locally and on Linux from clean pushed input
`4bde0dbf`, including canonical overlay compatibility and seven standard-client
cases. See the source contract for scope and deliberate checkpatch exclusions.
No hardware GTK acceptance or SSH-cause proof is claimed. Preserve strict
PN/integrity/ownership requirements.
0202 remains separate and unbuilt. The owner resumed regular builds/tests;
0203/0204/0205 ran as GTK2 and the admitted capacity successor is built. Keep one scalars
file and one table row per future run; no per-run result documents. No -48
adjustment, longer transaction deadlines, rekey, reuse or reconnect.

Prior framing result: [D2](SSH_D2_RESULT.md) consumed once on unchanged C10.
Port 0 advertised 94, staged descriptor 142; complete advertised PIO transfer
then equality refusal/poison/no-copy. Fault at ENABLE_PENDING, branch 4/-71,
23.238 ms after data-phase log, not a timeout. DHCP/pings/SSH and all local
queries were not reached. Healthy cleanup failed; one page debt retained.
Seal/quiescence/A53 regression and changed-boot Gemian independently verified.
C10 remains installed but consumed; no physical selection is pending.

The [bounded RX contract review](D2_RX_CONTRACT_REVIEW.md) verifies exact C10
source, TX-only arm quiescence and retained pre-arm WHISR 0x2. Public gen3 mapping
suggests an RX indication; this is not a FIFO/producer fence. New enable-time
+48 differs from historical close-time -48. The actual-source regression now
covers 94/142 on both ports, valid 94 and I/O faults; local ASan/UBSan passed.
No host framing correction is proved. The [follow-up source review/proposal](RX_FORMAT_OWNERSHIP_SUCCESSOR.md)
selects one fixed-format ownership comparison: initialize before scan-ready,
retain the format for the firmware instance, keep data-window/crypto gates.
Exact C10 EAPOL headers passed 48 existing cases on Linux with ASan/UBSan.
The [0202 prototype](FIXED_RX_FORMAT_PREPARATION.md) is implemented and passes
1482 ASan/UBSan cases plus RX/option-off comparisons locally and on Linux.
The separate approved 0203 window patch passes actual-source boundary/parity
checks. Final strict patch review has only the intentional missing DCO sign-off.
The old A/B plan is superseded: no further ARP-pair boot. Initial GTK plus the
independent window is next; no kernel build or execution is admitted.

The [three-run C10 baseline](CCMP10_BASELINE.md) remains SSH 2/3, all its finite
transport/network/host-cleanup windows passed. [D1](SSH_D1_RESULT.md) passed
without reproducing failure. Exact earlier TCP/KEX/auth failure stage remains
unknown; D2 does not classify it. [C11](CCMP11_RESULT.md) did not enable GTK.

Keep equality, complete transfer, poison/no-copy; no -48 adjustment, longer
transport deadline, speculative register or unrelated callback RE. GTK delivery
remains disabled on tested images; the default-off prototype is unbuilt. Rekey,
reuse and reconnect stay disabled. Staged 60 s / 2 min / 10 min and full
Wi-Fi acceptance remain incomplete. The pause record below is historical.

Historical pause boundary. The owner explicitly resumed implementation on
2026-10-17; see the [completion successor](CCMP_COMPLETION_SUCCESSOR.md) for
the new source/evidence review and candidate gates. The frozen C5 result and
old launch commands below remain consumed, not repeatable instructions.

**Owner stopped work after the single CCMP5 test and reviewed return. This
checkpoint authorizes nothing beyond preserving the record.** No driver work,
tests/builds, analysis execution, candidate selection or device action resumes
automatically. No unchanged C5 retry. No next candidate or fix is decided.

## Read these records, not the old launch commands

1. [CCMP5 result](CCMP5_RESULT.md): earlier -110/branch1 timeout, one checked
   Ethernet queue, no DHCP lease/SSH/full pass, no observed HIF refusal. Exact
   frozen kernel/profile/package/receipt/tool/deployment/boot identities and
   evidence seals are there; the deployment's full checksum is custodian-verified
   supplemental metadata, not a copied deployment record or new live inspection.
2. [CCMP5 preparation](CCMP5_PREPARATION.md): package/composition/receipt pins
   and tooling bindings; historical instructions are consumed, not a new run.
3. [0195 controlled comparison](RUNTIME_NO_POST_PROPOSAL.md): exact source,
   patch/body, two MAC entry points, preserved boot-reader post metadata and
   boot-drain invariants, focused actual-source tests and causal limits.
4. [C4 result](CCMP4_RESULT.md) and [C3 result](CCMP3_RESULT.md): finite WPA2/
   DHCP/one-ping progress, no SSH ACK/full pass, later post-CLOSED gap48. C4's
   staged0x4000 is an untrusted hint, not a certified packet/producer identity.

Latest executed tooling is `0f70e74bcd0d1fcafa4b47f8e94996e04cedc65a`; immutable
kernel input is `ea1fc0056738453a6e0d76cbea1d82db7ebbea48`; source85d1d621.
This documentation checkpoint does not require another kernel build. Candidate,
receipts, completed tools and prior evidence remain unchanged.

## Preserved state and boundaries

- Last confirmed current OS: Gemian3.18.41+/aarch64, changed boot
  `d09f829e-2a7e-4b5f-a240-b718c63f26ff`. Boot2 retains full C5
  `776cccbe841af9e36ccf981f19ec30456c61b819c6fa3d113dcd59c59533b812`.
- One capture/session, one reviewed return, helper/device children quiescent,
  full log preserved and63-entry seal verified by the custodian. See result for
  exact hashes and independent-verification scope. No pending retry is owed.
- Previously proposed bounded analysis remains **UNEXECUTED / HOLD**; it is not
  an approved next action. No new output or producer mechanism is established.
- Maintained Wi-Fi is incomplete: normal-mode per-frame PN/integrity/replay,
  key-epoch retirement/GTK/rekey/reuse, transport/resource/lifetime reliability
  and clean-profile ten-minute acceptance are unresolved. See the existing
  [support matrix](../../docs/HARDWARE_SUPPORT.md) and
  [roadmap](../../docs/ROADMAP.md); this checkpoint does not promote support.

## Next decision, only after an explicit owner resume

First review the **recorded earlier timeout and the read-sequence comparison**:
what stopped branch1 before the C3/C4 comparison point, which required evidence
is actually present, and which explanations remain unproved. Absence of a later
refusal cannot discriminate a repair when the trial terminates earlier. That
decision is not an instruction to boot, build, scan, add observers, relax RX or
retry C5. Resolve scope and review a concrete next proposal before new effects.

Keep one custodian for any eventually admitted device work; retained identities
are not fresh live checks. All safety/boot2/evidence/finite-budget/one-return
rules remain mandatory. Until the owner resumes: **HOLD**.
