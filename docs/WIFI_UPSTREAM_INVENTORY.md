# MT6797 Wi-Fi — upstream inventory (draft)

Offline inventory, 2026-10-25, of what the experiment tree would become as an
upstream series. No device, no build. It is a draft started in parallel with the
HT work (owner's order) because HT changes the same areas the upstream boundary
is about: the association admission, QoS, CCMP and the transmit framing. Those
rows are marked **moving** and are re-read when the HT chain lands.

Source: the `mt6797-a53-wifi-lifecycle` profile's series
(`patches/series-a53-wifi-lifecycle`) and the lifecycle fragment. Priorities stay
in the [roadmap](ROADMAP.md); measured support in
[hardware support](HARDWARE_SUPPORT.md).

## The tree today

- 259 proposals in the profile: 179 touch `drivers/net/wireless/mediatek/mt6797`
  (58 source files, `mac.c` 7,189 lines), 88 the connectivity owner under
  `drivers/soc/mediatek` (consys, WMT, BTIF, HIF ownership and AP-DMA).
- 29 Kconfig options in the driver's `Kconfig`, 31 proposals that add one.
- 125 `dev_info` sites in `mac.c` (2 `dev_dbg`), none in `hif.c`; 131 strings
  carry the experiment's `one-shot` prefix.
- Hard-coded radio facts: the receive status uses 5200 MHz (6 sites) and the
  join is bound to channel 40 (24 literals in `mac.c`).

## The coherent driver

| Layer | Where | Upstream form |
|---|---|---|
| Connectivity owner (consys power, WMT, BTIF, CONN sleep, HIF ownership) | `drivers/soc/mediatek` | its own series, with a DT binding; already the shared owner for Bluetooth |
| HIF transport (PIO, credits/TC ledger, AP-DMA data ports) | `hif.c`, `hif_*.h`, `ordinary-transfer.c`, 0260 | one transport layer; the PIO path as fallback, DMA as the data path |
| Command layer (normal commands, events, sequence and credit rules) | `normal_command.h`, `hif_command.h`, `join-commands.h`, `join-events.h` | one command/event module with the contract document as the design note |
| Firmware loader (MTKE parser, image plan, request_firmware) | `firmware-prepare.c`, `mtke.c`, `image-*.c` | request_firmware path; the firmware licence is a separate question |
| mac80211 driver (scan, join, keys, data path, lifecycle) | `mac.c`, `join-*.h`, `ccmp-*.h`, `eapol-rx.h`, `data-rx.h` | the driver proper; the experiment's one-shot structure becomes mac80211-driven state |

## Kconfig options

| Becomes ordinary code (no option) | Becomes a constant | Drops out (experiment or measurement) |
|---|---|---|
| `HIF_CORE` (the driver, tristate), `MAC80211`, `PASSIVE_SCAN`, `STATION_JOIN`, `CCMP_STABLE_EPOCH`, `CCMP_INITIAL_GTK`, `CCMP_CONNECTED_LIFETIME`, `CCMP_TX_PID_REUSE`, `CCMP_TX_PUMP`, `DATA_CREDIT_RETIRE`, `TX_BACKPRESSURE`, `HIF_DMA_TX`, `HIF_DMA_RX`, `HIF_TC4_RECONCILE` (to confirm), `WMM_QOS_DATA` (**moving**) | `CCMP_TX_DEPTH` (12), `DATA_TX_QUEUE_FRAMES` (64) | `HIF_TX_STATUS_PROBE`, `SCAN_TUNING_SAMPLE`, `NATIVE_DELIVERY_DIAG`, `CCMP_MASK_CONTROL`, `CCMP_60S_WINDOW`, `CCMP_CHANNEL_RELEASE`, `CCMP_50S_IDLE`, `CCMP_LIFETIME_PREREQUISITES`, `HIF_RX_BATCH` (retired), `RX_RATE_RECORD`, `TX_DONE_RATE_RECORD`, `TX_PER_FRAME_RECORD`, `TX_REPORT_SAMPLE`, `DATA_PHASE_SERIES`, `DATA_FIXED_RATE_CODE`, `WMM_QOS_RECORDS` |

The middle column is a measured setting today (boots M and N); upstream it is a
constant with its reason in a comment, or a module parameter only if a second
board needs another value.

## What drops out besides the options

- **The private sealed logger** and everything sized for it: the bounded per-frame
  records, the data-end summary lines, the byte budgets. Upstream keeps state in
  debugfs and events in tracepoints (below).
- **The fixed rate** (0273, OFDM 54 Mbit/s): replaced by the firmware's rate
  control with HT (**moving**; the firmware stayed at rate-table entry 0 when the
  rate was left to it, boot D).
- **The single traffic class**: all data on TC1 (AC_BE). QoS with four access
  categories needs the TC mapping per AC (**moving**, HT phase).
- **The bounded lifetimes**: the one-shot join, the two-lifetime cap and the
  data-phase budgets become mac80211-driven connect/disconnect with watchdogs.
- **Channel 40 and 5200 MHz**: channel and band from `chandef`, `rx_status.freq`
  from the descriptor (plan Phase 3).

## printk to tracepoints

Of the 125 `dev_info` sites, three kinds:

- **lifetime transitions** (join, association, keys, teardown, firmware ready or
  stopped): stay `dev_info`, or `dev_dbg` where they are per-lifetime chatter;
- **per-event and per-frame records** (EAPOL admission and header, receive gaps,
  credit retire samples, the rate records): tracepoints;
- **data-end summaries and counters** (backpressure, credit retire, QoS counts, the
  per-second series): debugfs files read on demand.

The measurement harness parses kmsg lines today, so this change moves the
instrument: it waits until the HT chain's measurement freeze ends.

## Gates before any submission

- **Authorship and certification.** Of the 259 proposals, 36 are authored as the
  owner; the rest carry placeholder experiment or agent identities, and 3 carry a
  `Signed-off-by`. Upstream needs the true author and a truthful DCO for every
  patch; nothing here invents one. The series will be re-authored from the
  consolidated driver, not submitted patch by patch.
- **Vendor-derived facts.** Command and record layouts follow the public gen3
  vendor headers (`CMD_UPDATE_STA_RECORD_T`, `CMD_SET_BSS_INFO`); the code is
  independently written. Each such layout gets its public source named in the
  commit message.
- **Firmware.** Loading through `request_firmware`; redistribution rights for the
  firmware image are a separate question and not assumed.
- **Review.** The subsystem's normal review (linux-wireless, linux-mediatek, DT
  bindings) after the consolidation, never before.
