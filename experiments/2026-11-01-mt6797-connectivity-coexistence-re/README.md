# Experiment: MT6797 Wi-Fi, Bluetooth and LTE coexistence reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-connectivity-coexistence-re` |
| Status | `completed` (offline source and firmware review; no device access) |
| Subsystem | MT6797 CONSYS coexistence: WMT configuration, Wi-Fi firmware arbitration, LTE IDC |
| Device variant | Planet Computers Gemini PDA, MT6797X, CONSYS `0x0279` |
| Date(s) | 2026-11-01 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Connectivity documentation; no implementation |

## Question

The Bluetooth and Wi-Fi records each cover their own transport. This study asks
how the two radios, and the co-located LTE modem, share one connectivity
subsystem and one 2.4 GHz medium:

1. Which resources do they share, and which are separate?
2. What does the host configure, and what does the firmware decide?
3. Which messages carry the coexistence state, in which direction?
4. What is demonstrated, and what is inferred or unknown?

No code, patch, candidate or device state is changed.

## Provenance and environment

Vendor source was cloned sparsely (no blobs) at Gemian
`gemini-linux-kernel-3.18` commit
`59e00a9144d782e148332009a835b99c43382467` inside the RE VM, read only. Private
firmware strings came from the retained 2019 vendor set. No vendor source or
firmware is copied into this repository.

| File | SHA-256 |
| --- | --- |
| `drivers/misc/mediatek/connectivity/common/common_main/core/wmt_ic_soc.c` | `22d98e9e5f0c9c3cae36a3099e57315ed7808524239a061bf9ab0cf97379e66f` |
| `drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c` | `e9f438c5c6033f0bf831347c69d656ec917b3e705648d3d27fb1b27409334f1e` |
| `drivers/misc/mediatek/connectivity/common/common_main/core/wmt_conf.c` | `25a9b92f28ebfd1e37f5988406849b7cfcd91569886f8ef34044d2a9fe954361` |
| `drivers/misc/mediatek/connectivity/common/common_main/include/stp_exp.h` | `9c1daca8fa5e30468865d42fb778bf070ac09e0adebf6735852631d5dc89ec42` |
| `drivers/misc/mediatek/connectivity/common/common_main/linux/wmt_idc.c` | `2b169b764916dbcafdbfc3c221af149e280f6d868c04d08bdd7198d9137dc523` |
| `drivers/misc/mediatek/connectivity/common/common_main/linux/include/wmt_idc.h` | `0a80bc55e5a3b2fc8b1df589c55618c786b924a9ed2313797572fb4e8cc45371` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_cmd_event.c` | `cc61d706a4013126c1b3a60021c370590fd5b8c3df2114a1a3a99148fe27dd8f` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_tx.c` | `1f479d41bab8e2b5bba68eb6514f3e977559d31d97c39c7833f3dc9f111cd1ed` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_cmd_event.h` | `93c8d67b1bc039a8db5b635e5a00975f2b9e408f4ab1bc8a384f5db49bf00a3a` |
| `drivers/misc/mediatek/connectivity/Kconfig` | `285fd2994b14dc55b9ea2769be54936e40b068cd32f25a26bb310e1b7ab7e0cc` |
| `drivers/misc/mediatek/connectivity/Makefile` | `bcb9f2545c5a95cc16af92e90e59d2f975853b6a5c7a657a15a5bf8a46cc7b2c` |

Firmware hashes are the published ones in
[firmware](../2026-07-11-gemian-firmware-inventory/README.md): `ROMv3_patch_1_0`
`450c2b09…`, `ROMv3_patch_1_1` `5732c073…`, `WIFI_RAM_CODE_6797` `a69383d7…`,
`WMT_SOC.cfg` `f4a59b62…`.

## Method

- Source reading of the WMT configuration, power-on order, the IDC bridge and
  the Wi-Fi event handling.
- Message-id enumeration from the vendor enums and command arrays.
- String analysis of the retained Wi-Fi firmware and ROM patches to identify
  the firmware-side coexistence vocabulary. Strings are cited as protocol
  facts; no content is copied.
- Cross-check against the already documented mainline common-init step table
  and its one runtime result.

## Findings

### F1. One chip, two firmware images, three host interfaces

CONSYS contains the BT baseband (ROM plus the `ROMv3_patch_*` images) and the
Wi-Fi MAC (`WIFI_RAM_CODE_6797`). The host reaches them over separate data
transports (BTIF/STP for BT, the WLAN HIF window for Wi-Fi) but a single control
transport (WMT task 4) and a single common power-on. The 3.3 V rails are
separate (`VCN33_BT`, `VCN33_WIFI`); 1.8 V `VCN18` is shared. No external
coexistence switch or PTA wiring is described in the board files.

### F2. The host configures only the antenna mode at 2.4 GHz

`wmt_stp_init_coex()` sends the `coex_wmt` command
`01 10 02 00 01 <ant_mode>` using `coex_wmt_ant_mode` from `WMT_SOC.cfg`
(retained value `1`). The legacy per-subsystem RSSI/power tables (`coex_bt`,
`coex_wifi`, `coex_ext_pta`, `coex_misc`) are compiled out because
`CFG_SUBSYS_COEX_NEED` is `0` in this tree. There is no host API for air-time
allocation, slot masks or channel avoidance.

### F3. The LTE filter tables are sent on this board

`CONFIG_MTK_CONN_LTE_IDC_SUPPORT` is `default y` in the connectivity Kconfig and
no Gemini defconfig disables it, so `WMT_IDC_SUPPORT=1`,
`CFG_WMT_LTE_COEX_HANDLING=1` and the filter-mode path are active. For chip
`0x0279` the vendor selects `set_wifi_lte_coex_table_2`: external component
`0x0d`, filter spec `0x11` (69 bytes), frequency index table `0x12` (33 bytes),
unsafe channels `0x13` (`0`), and the L-branch flag `0x21` (`1`). The table is
sent before the calibration rails are switched on. Mainline's common-init
replicates these five commands at steps 274-278.

### F4. The antenna-mode command is sent after calibration

The vendor order is: patch download, LTE table, PA rails on, RF calibration,
PA rails off, `coex_wmt` antenna mode, co-clock. Mainline's step 284 matches
the antenna-mode position and its one runtime accepted the exact event.

### F5. LTE participates through an IDC bridge with named messages

The modem and the connectivity subsystem exchange typed messages through the
CCI/IPC bridge. Modem-to-connectivity messages include default parameters,
operating frequency/band/bandwidth, Wi-Fi max TX power, LTE TX on/off,
connection status and hardware interface. Connectivity-to-modem messages include
Wi-Fi/BT default parameters, Wi-Fi/BT operating frequency, the frequency index
table, the BT/Wi-Fi profile, and LTE TX allow. In the kernel, firmware-to-modem
traffic arrives on STP task 8 (`COEX_TASK_INDX`) and is forwarded by `wmt_idc`;
modem-to-firmware traffic is wrapped as WMT opcode `0x10`, message id `0x00`,
flag byte and payload on task 4.

### F6. The Wi-Fi firmware is the air-time arbiter

`WIFI_RAM_CODE_6797` contains the coexistence machinery and its log strings:
`CONFIG_COEX_SETTING: BT = …, LTE = …, PTA: …`, `REPORT_BT_PROFILE` with the
values `NONE`, `SCO`, `ESCO`, `A2DP`, `HID`, `Multi HID`, `LINK_CONNECTED`,
`PAGE`, `INQUIRY`, PTA and internal-arbiter counters (`RW(PTA)`, `RW(ARB)`),
three-radio and scan arbitration state, TDM requests and elapsed time, block-ack
deletion, and per-BSS rate limiting. The BT ROM patch has no arbiter vocabulary;
it carries the WMT/LTE frequency and timing messages instead. The profile report
is therefore generated inside CONSYS from the BT link state; no host component
sends it.

### F7. The Wi-Fi driver consumes two firmware reactions

The vendor Wi-Fi driver applies the per-BSS PHY rate limit from the
`UPDATE_FW_INFO` event (`au4PhyRateLimit`) before rate selection, and stores the
LTE safe-channel bitmaps from the LTE safe-channel event. Both are firmware
outputs of the coexistence decision. The driver does not send BT state back.

### F8. Mainline implements the configuration, not the reactions

The current mainline series sends the antenna mode and the selected LTE table in
the one-shot common-init, which is the same policy input the vendor stack sends.
It does not implement the IDC bridge, the rate-limit event, or the safe-channel
event. The firmware is therefore expected to arbitrate with its defaults, but
the host does not adapt as the vendor driver does.

## Interpretation

Coexistence on this platform is a firmware problem with a small host
configuration surface. The host supplies the antenna topology hint and the LTE
filter tables once, and the modem supplies its frequency and activity at
runtime; everything else, including the per-profile policy, TDM grants, PTA/ARB
decisions and the resulting Wi-Fi rate limits, runs inside CONSYS. The BT host
stack never learns that Wi-Fi exists.

Two consequences follow. First, a mainline system that runs both radios is not
missing a scheduling driver; it is missing only the optional host reactions
(rate limit, safe channels). Second, real-world behaviour (throughput, audio
quality) depends on firmware policy that is not readable from source, so it has
to be measured, not derived.

## Limitations

- No device was contacted; no concurrent BT/Wi-Fi/LTE run was measured.
- The antenna topology (shared vs separate 2.4 GHz path) is not established.
  The config byte `1` and the port-2 PTA code are consistent with sharing but
  do not prove it; the vendor source defines no enum.
- Which grant mechanism the board uses (internal ARB, PTA, or both) is unknown.
- Firmware internals are inferred from message and log vocabulary, not from
  disassembly of the arbitration algorithm.
- The actual built `.config` was not read from the device; the IDC conclusion
  rests on the Kconfig default and the unmodified defconfigs.
- Whether the host reactions are required for correct behaviour is unknown.

## Consequences

- The durable reference is
  [MT6797 connectivity coexistence](../../docs/hardware/mt6797-connectivity-coexistence.md).
- Concurrent mainline work should first measure 2.4 GHz versus 5 GHz behaviour
  with BT idle, SCO and A2DP while Wi-Fi transfers; the existing Wi-Fi harness
  can produce the throughput side.
- If the measurements show a firmware-imposed penalty, implementing the
  rate-limit and safe-channel events is a bounded, standard-driver-friendly next
  step; the IDC/LTE bridge is a separate, larger boundary.
- No repository patch, profile or device state is proposed by this record.
