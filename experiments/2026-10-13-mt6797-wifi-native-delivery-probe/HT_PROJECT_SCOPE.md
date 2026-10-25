# HT (802.11n) on the station path — project scope

Scope record, 2026-10-25. A written project with its dependencies, not a
boot candidate: nothing here is staged, and each item is its own
reviewable change with its own predeclared boot.

## Why this is the throughput question now

At the fixed 54 Mbit/s legacy rate the air carries about 2,590
1,518-byte frames a second (about 386 µs each with the preamble, SIFS,
acknowledgement, DIFS and average backoff), about 30 Mbit/s of TCP
goodput. Transmit reached 22.7–24.1 Mbit/s at depth 12 (boot M), 77 % of
that, and the depth model's asymptote (35.7) lies above it: no host-side
change to the legacy path can pass the air. The vendor's own driver
reached 45.1 Mbit/s of transmit on this device (vendor control 2 in
[the throughput series](THROUGHPUT_SERIES_RESULT.md)). The record is in
[HIF §§20–24](HIF_TRANSPORT_ANALYSIS.md#24-boot-n-predeclared-2026-10-25-depth-16-and-the-receive-streams-state).

## Where the driver stands

- The 5 GHz band (`band_5g`) advertises legacy rates only: no HT
  capability, no VHT.
- The association admission refuses an association request carrying an
  HT capability, VHT capability or WMM element (`mt6797_join_*`
  admission in `mac.c`: "No HT/VHT, fast-transition or WMM negotiation").
- One mac80211 queue (`hw->queues = 1` with the station join); the
  transmit admission accepts only non-QoS protected data (frame control
  0x4108) and the two control-port EAPOL frames.
- The data descriptor carries a fixed legacy rate code (0273, 0x4c); the
  state-2 station record (0277) is accepted, but the firmware stays at
  rate-table entry 0 when the rate is left to it, an open question.

## The work, in dependency order

mac80211 negotiates HT only when WMM is in use (`ieee80211_determine_our_sta_mode`:
"WMM/QoS not supported, limiting to legacy"), and WMM needs four hardware
queues and a `conf_tx` operation. So the first association that can carry HT
also carries WMM, and its data becomes QoS data: the data path changes with
the first step. (Corrected 2026-10-25 from an earlier order that put HT
association before QoS.)

| # | Change | Side | Depends on | Proven by |
|---|---|---|---|---|
| 1 | WMM: four mac80211 queues, a `conf_tx` operation, the WMM element admitted in the association, and the BSS and station records' QoS declaration (`ucIsQBSS`, `ucIsQoS`), on which the firmware's QoS framing and AAD follow; boot O ([0284](../../patches/proposals/0284-wifi-mt6797-negotiate-WMM-and-carry-data-as-QoS-data-at-the-legacy-rate.patch)) | host, and the two record fields | — | a legacy-rate boot: the join and both lifetimes as before, the association response's WMM parameters accepted, the ledger whole |
| 2 | QoS data in the transmit admission (subtype 8, the 26-byte header with its QoS control field) and in its Ethernet II conversion; received QoS data likewise | host, the descriptor unchanged | 1 | the same boot: data acknowledged on the air at the fixed 0x4c, the throughput row unchanged within noise |
| 3 | HT capability on 5 GHz (HT20, MCS 0–7 for 1×1, conservative A-MPDU parameters, no short GI) and the HT capability element admitted in the association (and the HT operation in the response) | host only | 1, 2 | the received-rate record (0271): the access point's frames to this station in HT modes rather than legacy OFDM |
| 4 | The station record's PHY type set, MCS set and HT capability fields from the peer's HT capabilities | firmware-facing | 3 | the firmware's rate word leaving 0x4c for an HT MCS on the sampled reports (0281) |
| 5 | Block-ack for A-MPDU: transmit sessions (`ampdu_action`), the firmware's aggregation, receive reordering in mac80211 | firmware-facing | 4 | aggregates in the sampled reports, transmit above the 30 Mbit/s legacy ceiling |

Items 1–3 are host-only, but items 1 and 2 change the data path, so they
are proven together on a legacy-rate boot before item 3 asks for HT. The
question whether this access point speaks HT to this device is already
answered by the vendor's driver (45.1 Mbit/s of transmit through it, above
the legacy ceiling); item 3's boot answers whether it speaks HT to ours.
Items 4–5 need the firmware's interfaces for the station record and
aggregation, read and reviewed under the same rules as the existing
commands.

**The first concrete obstacle (2026-10-25).** It was not aggregation but the
access category of the handshake frames: the access point sends its
EAPOL-Key on TID 6 (AC_VO) once WMM is negotiated, and the gate refused
the descriptor's TID (boots O and P). The same detail will recur in
roaming, in 802.1X and with any access point that puts EAPOL on AC_VO.
The second (boot Q) was the downlink data admission: with WMM the access
point sends all data as QoS, and the receive checks admitted only TID 0
with QoS control 0. Both obstacles are QoS-layout consequences, and both
will recur in roaming and 802.1X. The third (boot R) was the same kind:
the transmit admission allowed only TID 0 while mac80211 picks the TID
from the frame, and a group LLC-mismatch class (`0xc200`) surfaced at
the receive check. The first three obstacles were all access-category
or frame-layout consequences, none of them aggregation.
Boot S restored the data path under WMM and measured it (17.2 / 17.6
Mbit/s at the legacy rate; WMM cost no measurable throughput). The fourth
obstacle is the receive replay counter: one for all TIDs, where CCMP
needs one per TID. It is a prerequisite for HT, not a detour, because
aggregation and block-ack are per TID too (boot T, 0292).

**Two HT routes, predeclared separately.**

| Route | Needs | Predicted |
|---|---|---|
| fixed MCS, no aggregation | HT capability in the wiphy; the HT element in the association; then the MCS in the descriptor's existing fixed-rate field (`TX_MODE_HT_MM \| MCS7` = `0x87`, `wlan_def.h`) | whether this access point uses HT rates toward this station, for one boot and no aggregation work |
| block-ack and A-MPDU | per-TID PN (0292), `ampdu_action`, `AMPDU_AGGREGATION`, per-frame rate and HT-flag reporting, the firmware's block-ack commands | about +100 %; this is the project |

The cheap route starts host-side only: advertise HT with WMM negotiated,
keep the fixed `0x4c` descriptor and the records non-QoS, and read the
receive rate record for HT modes. If the access point starts sending HT
rates to this station, the next piece is the descriptor's MCS and the
station record's PHY and MCS fields. If it stays legacy, HT buys nothing
here and the throughput work closes at about 23/19 Mbit/s.

**Watch in that boot.** Advertising HT may make the access point
aggregate its downlink. If the receive refusals change shape (new
status bits, larger frames, A-MPDU sub-frames with more than one per
buffer), stop and read them before any throughput claim. That is the
difference between "HT is available" and "HT is available and we cannot
receive it".

**Two host contracts become ours once HT begins**, because this driver
delivers frames natively:

- reporting each received frame's rate and HT flags to mac80211, today
  logged in the rate record but not reported (`RX_FLAG_NO_SIGNAL_VAL`, no
  rate);
- implementing `ampdu_action` per TID (today a stub that refuses).

**The descriptor's A-MPDU bits are not air aggregation.** Status bits 14
and 15 (`RX_STATUS_AMPDU_SUB_FRAME`, `RX_STATUS_AMPDU_FORMAT`) are set on
every ordinary accepted frame (`0xc000`), legacy boots included. They
describe how the frame was delivered through the receive buffer, not an
802.11 A-MPDU, and are no evidence that the access point aggregates to
this station. Whether block-ack and A-MPDU are gated on HT in the
firmware, and what it does with the BSS and station QoS records, are
item 5's questions, one bounded firmware session each, later; nothing on
the path to a working WMM data path needs them.

## Boundaries

- The admitted lifecycle tree (depth 12, the 64-frame queue, credit
  retire) stays the baseline every HT boot is read against.
- One change per boot, each with its own predeclaration; the safety
  counters (`expired`, `pid_faults`, `left_pages`, `dropped_full`,
  `tx_failed`) and the verdict stay as they are.
- 40 MHz, VHT (80 MHz, 802.11ac) and short GI are later steps, not part
  of this scope.
- Independent of this project: the access-point vanish-and-return test,
  the one remaining robustness item.
