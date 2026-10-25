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
| 1 | WMM: four mac80211 queues, a `conf_tx` operation, the WMM element admitted in the association; the backpressure stop/wake across the four queues | host only | — | a legacy-rate boot: the join and both lifetimes as before, the association response's WMM parameters accepted, the ledger whole |
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
