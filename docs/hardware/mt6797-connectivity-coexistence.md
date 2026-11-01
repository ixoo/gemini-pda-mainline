# MT6797 connectivity coexistence

This document describes how Bluetooth and Wi-Fi share the 2.4 GHz medium on the
Gemini, and how the LTE modem participates. It separates what the host
configures, what the CONSYS firmware decides, and what is not established.

The Bluetooth transport itself is in
[MT6797 Bluetooth and Bluetooth audio](mt6797-bluetooth.md); the Wi-Fi platform
and firmware are in [MT6797 integrated Wi-Fi](mt6797-wifi.md). The source and
firmware evidence for this document is the
[coexistence reverse-engineering record](../../experiments/2026-11-01-mt6797-connectivity-coexistence-re/README.md).

## What is shared and what is not

| Resource | Wi-Fi | Bluetooth | Shared? |
| --- | --- | --- | --- |
| Radio band | 2.4 and 5 GHz | 2.4 GHz only | 2.4 GHz air is shared |
| RF/antenna path | CONSYS front end | CONSYS front end | internal; external topology not established |
| Firmware | `WIFI_RAM_CODE_6797` | ROM patch (`ROMv3_patch_*`) | one chip, separate images |
| Host data transport | WLAN HIF (AHB/DMA window) | BTIF + STP task 0 | no |
| Host control path | WMT task 4 (with BT/GPS) | WMT task 4 | yes |
| Power sequence | WMT common on | WMT common on | yes |
| 3.3 V rail | `VCN33_WIFI` | `VCN33_BT` | separate LDOs |
| 1.8 V rail | `VCN18` | `VCN18` | yes |
| Coexistence policy | WMT messages | WMT messages | yes |

Both radios are functions of the same CONSYS owner. Turning one on does not
power the other: each function has its own WMT function-control command and its
own PA LDO, but both depend on the one common power-on that loads the ROM patch,
runs RF calibration and sends the coexistence configuration. The two host data
transports are independent; only the WMT control channel is common.

The board file and retained evidence describe no external coexistence switch,
antenna-select GPIO or PTA wiring. Any antenna/front-end sharing is therefore
internal to the CONSYS package. Whether the Gemini has a physically separate BT
antenna cannot be settled from the retained material; the only exposed knob is
the WMT antenna-mode byte described below.

## Who decides

The host does not schedule the air. It configures policy once, and the
connectivity firmware arbitrates at packet and slot granularity:

- The **Wi-Fi firmware** contains the BT/Wi-Fi coexistence logic. Its retained
  strings include a `CONFIG_COEX_SETTING: BT = …, LTE = …, PTA: …` message, a
  `REPORT_BT_PROFILE` message whose enumerated values are Bluetooth link types
  (`NONE`, `SCO`, `ESCO`, `A2DP`, `HID`, `Multi HID`, `LINK_CONNECTED`, `PAGE`,
  `INQUIRY`), PTA and internal-arbiter counters (`RW(PTA)` / `RW(ARB)`),
  TDM grants (`TDM REQ scheme`, `TDM REQ Wi-Fi time`, `LTE time`, `TDM Elapse`),
  block-ack deletion, and per-BSS rate limits.
- The **connectivity ROM patch** owns the WMT task and the LTE messaging. Its
  strings report BT and Wi-Fi operating frequencies to the modem and the modem's
  frequency/band/activity to the radios, plus timing parameters
  (`tdm_req_leadtime`, `g_bt_802_11_rx_timeout`, `Bg_bt_820_11_rx_leadtime`).
- The **host Bluetooth stack** is not involved. No vendor BT library or HCI
  command sends an explicit coexistence profile; the controller infers the
  link type (SCO, eSCO, A2DP, HID, inquiry, page) from the HCI traffic and link
  state, and the report is generated inside CONSYS.

Nothing in the host source exposes an air-time split, a slot mask or a channel
avoidance map to configure.

## The host-visible configuration

All coexistence configuration is WMT opcode `0x10` on task 4, with a one-byte
message id. The messages observed in the vendor source are:

| Id | Message | Consumer | Sent on this board |
| --- | --- | --- | --- |
| `0x01` | `coex_wmt` | firmware | yes, one byte: antenna mode |
| `0x02` | `coex_bt` | firmware | no, compiled out |
| `0x03` | `coex_wifi` | firmware | no, compiled out |
| `0x04` | `coex_ext_pta` | firmware | no, compiled out |
| `0x05` | `coex_misc` | firmware | no, compiled out |
| `0x00` | LTE IDC passthrough | firmware | runtime, when the modem sends state |
| `0x0d` | LTE external component | firmware | yes, `0` |
| `0x11` | LTE coex filter spec | firmware | yes, 69-byte table |
| `0x12` | LTE frequency index table | firmware | yes, 33-byte table |
| `0x13` | LTE unsafe channels | firmware | yes, `0` |
| `0x14` | TDM request antenna-select count | firmware | only in another vendor table |
| `0x15` | LTE project flag | firmware | not in the selected table |
| `0x21` | "is LTE L branch" | firmware | yes, `1` |

Two details correct an earlier assumption:

- **The BT/Wi-Fi RSSI and power tables are not used here.**
  `CFG_SUBSYS_COEX_NEED` is `0` in this tree, so the `coex_bt`, `coex_wifi`,
  `coex_ext_pta` and `coex_misc` commands are compiled out. The only
  antenna-side policy the host sends is the one-byte antenna mode.
- **The LTE tables are sent.** `CONFIG_MTK_CONN_LTE_IDC_SUPPORT` defaults to `y`
  and the Gemini defconfigs do not disable it, so `CFG_WMT_LTE_COEX_HANDLING`
  and the filter-mode path are enabled. For chip `0x0279` the vendor selects
  table 2: external component `0`, filter spec, frequency index table, unsafe
  channels and the L-branch flag. The mainline common-init already replicates
  these five commands.

The antenna mode comes from `WMT_SOC.cfg` key `coex_wmt_ant_mode`, which is `1`
in the retained 80-byte file. The vendor source only forwards the byte; it
defines no enum. A public third-party description of the same MTK config key
calls `1` a single/shared antenna, and the presence of port-2 PTA handling in
the Wi-Fi firmware is consistent with BT and Wi-Fi sharing a 2.4 GHz path, but
the exact meaning is not established from vendor code.

Configuration ordering is fixed by the common power-on: the LTE coexistence
tables are sent after ROM patch load and before the calibration rails go on,
then, after RF calibration and with both PA rails off, the host sends the
antenna-mode command. Mainline's common-init step table places them in the same
positions (steps 274-278 and 284), and one runtime completed 285 of 285 steps
with the matching events.

## The LTE/modem path

The modem is a third radio on the same chipset and permanently co-located, so
LTE participates even when the user only cares about BT and Wi-Fi. The vendor
uses the IPC/CCCI "IDC" bridge:

- The modem reports its state to the connection subsystem:
  `LTE_DEFAULT_PARAM`, `LTE_OPER_FREQ_PARAM` (frequency, band, bandwidth),
  `WIFI_MAX_PWR`, `LTE_TX_IND` (TX on/off), `LTE_CONNECTION_STATUS`,
  `PIN_TYPE`, `LTE_HW_INTERFACE`.
- The connection subsystem reports back:
  `WIFIBT_OPER_DEFAULT_PARAM`, `WIFIBT_OPER_FREQ` (BT and Wi-Fi frequencies),
  `WIFIBT_FREQ_IDX_TABLE`, `WIFIBT_PROFILE` (the BT profile), and
  `LTE_TX_ALLOW`.
- On the host, messages from CONSYS arrive on STP task 8 (`COEX_TASK_INDX`) and
  are forwarded to the modem by `wmt_idc`; messages from the modem are wrapped
  as WMT opcode `0x10`, message id `0x00`, flag byte, payload, and sent on
  task 4.

This is why the ROM patch logs BT and Wi-Fi operating frequencies: the modem
needs to know where the WLAN and BT radios are so its own scheduler and TX
blanking can avoid them. The reverse direction is consistent with the
firmware's "safe channel" lists, which the vendor Wi-Fi driver receives; the
exact dependence of those lists on the modem's reported frequency is not
established from source.

## How the air is actually shared

The mechanisms, from the firmware vocabulary and the standard behaviour of the
two protocols:

1. **Profile-aware arbitration.** The Wi-Fi firmware receives the BT link
   profile. SCO uses reserved slots on a fixed cadence (HV1 every 2 slots, HV2
   every 4, HV3 every 6) and eSCO uses reserved windows with retransmission, so
   both are latency-critical; A2DP is bulk ACL and can yield and retransmit; HID
   and inquiry/page are low-duty or latency-sensitive. The arbitration policy
   differs per profile.
2. **Internal arbitration or PTA.** The firmware accounts grants through its
   internal arbiter (`ARB`) and/or a packet-traffic-arbitration interface
   (`PTA`). Both counters exist in the Wi-Fi firmware; which one this board uses
   is not established. When a grant is not enough, the firmware falls back to
   time division.
3. **TDM grants.** The firmware can grant Wi-Fi and LTE fixed windows
   (`TDM REQ scheme`, Wi-Fi time, LTE time) and logs elapsed TDM time. This is
   the mechanism that keeps LTE voice/data and Wi-Fi from starving each other.
4. **Wi-Fi-side adaptation.** To fit around BT, the Wi-Fi firmware can delete
   block-ack agreements (shorter A-MPDU bursts), request high-priority PTA
   service, time-slice scans, cap transmit power when LTE requests it, and use
   the LTE "safe channel" lists. It also reports a per-BSS PHY rate limit to the
   host, which the vendor driver applies before rate selection.
5. **BT-side behaviour.** The controller keeps its slot timing and adaptive
   frequency hopping. AFH is what avoids the Wi-Fi channel inside the BT hop
   sequence; the host stack has no visibility into the map. Whether the
   coexistence block feeds the AFH map on this platform is not established.
6. **Band dependence.** All of this matters only when Wi-Fi is on 2.4 GHz. On a
   5 GHz association the BT band is clear and the arbiter has no air to share;
   only a shared front end or receive-chain desense could still couple them.

Practical consequences on this device:

- With Wi-Fi on 2.4 GHz, a BT SCO call or A2DP stream will reduce Wi-Fi
  throughput and increase latency, and heavy Wi-Fi traffic can degrade BT audio.
  The firmware hides the mechanism but the air time is real.
- With Wi-Fi on 5 GHz, BT audio and Wi-Fi traffic should interfere much less.
  This is the configuration to prefer for concurrent use.
- Coexistence does not change pairing, discovery or the HCI transport; it only
  affects throughput, latency and audio quality.

## What each software stack does today

| Piece | Vendor Gemian | Current mainline |
| --- | --- | --- |
| Antenna mode + LTE tables at power-on | sent by WMT | sent by the one-shot common-init |
| Runtime LTE IDC bridge | `wmt_idc` over CCCI | none |
| Per-BSS rate-limit event | consumed and applied | not implemented |
| LTE safe-channel event | consumed and stored | not implemented |
| BT profile report | generated in firmware | generated in firmware (same firmware) |
| Host air-time policy | none | none |

Because the policy lives in firmware, a mainline boot that sends the common-init
configuration already gets the same arbitration defaults as the vendor stack.
What it does not get is the host's adaptive reaction (rate limiting, safe
channels). Whether the firmware needs that reaction for good behaviour, or only
uses it as an optimisation, is unknown; it is the main open question for
concurrent mainline operation.

## Open questions

- Is the 2.4 GHz antenna shared between BT and Wi-Fi on this board? The config
  byte and the port-2 PTA support suggest so, but no schematic or vendor enum
  proves it.
- Does the board use the internal arbiter, PTA, or both?
- What are the actual TDM windows and grant priorities per BT profile?
- Does the firmware feed the BT AFH map from Wi-Fi channel information?
- Must the host consume the per-BSS rate-limit and safe-channel events, or are
  they advisory?
- How do mainline throughput and BT audio behave with both radios active at
  2.4 GHz versus 5 GHz? No experiment has measured this yet.

## Evidence

- Vendor source at `59e00a9144d782e148332009a835b99c43382467`:
  `wmt_ic_soc.c` (coex tables, antenna mode, selected LTE table),
  `wmt_conf.c` (`WMT_SOC.cfg` keys), `wmt_core.c` (`0x10`/IDC path),
  `wmt_idc.c`/`wmt_idc.h` (message ids, task 8), `stp_exp.h`
  (`COEX_TASK_INDX`, `WMT_IDC_SUPPORT`), `nic_cmd_event.c` (rate limit, safe
  channels), `nic_tx.c` (rate-limit application).
- Firmware: `WIFI_RAM_CODE_6797` (coexistence messages and logs),
  `ROMv3_patch_1_*` (LTE/WMT messages), `WMT_SOC.cfg`.
- Runtime: one 285/285 common-init boot
  ([runtime 3](../../experiments/2026-10-06-mt6797-wifi-common-init/RUNTIME_3.md)).
