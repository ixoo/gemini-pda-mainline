# Experiment: Gemini Bluetooth path reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-bluetooth-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | MT6797 CONSYS Bluetooth: WMT function control, STP BT task, BTIF transport, VCN33-BT, power saving, HCI vendor initialization, BD address, SCO/CVSD audio |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, CONSYS chip ID `0x0279`, WMT `MT279` ROM `E1`, patch `20180307`) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | [#25](https://github.com/ixoo/gemini-pda-mainline/issues/25) (M6 connectivity) |

## Question

What does the stock software actually do to bring Bluetooth up on the
Gemini, what travels over the wire, and how much of the mainline MediaTek
Bluetooth code can carry it? The roadmap's
[Bluetooth-then-GNSS step](../../docs/ROADMAP.md#after-wi-fi-remaining-driver-gaps)
assumed "a `hci_dev` over the shared BTIF/STP channel reusing `btmtk`
helpers" and a first runtime test of "one HCI reset and version read". This
record checks that shape against the pinned vendor source, Gemian's own
BlueZ driver and the Linux 7.1.3 tree, separates verified facts from
hypotheses, and ranks the hypotheses by the device test that decides them. It
changes no patch, profile, candidate or device state.

It reuses, and does not repeat, the Wi-Fi findings that Bluetooth shares:
the [Wi-Fi audit](../2026-10-03-mt6797-wifi-audit/README.md) (common
power-on order), its [full-STP framing note](../2026-10-03-mt6797-wifi-audit/FULL_STP.md),
[BTIF mandatory-mode review](../2026-10-03-mt6797-wifi-audit/BTIF_MANDATORY.md)
and [ROM applicability review](../2026-10-03-mt6797-wifi-audit/ROM_APPLICABILITY.md),
the observed mainline [default WMT query](../2026-10-03-mt6797-wmt-default-query/results/runtime-2.json)
and [mode negotiation](../2026-10-03-mt6797-wmt-negotiate/results/runtime-1.json)
round trips, and the [GPS record](../2026-10-04-gemini-gps-re/README.md),
whose fact F5 (STP task bits) and AFE-block finding apply to Bluetooth
unchanged.

## Inputs

Vendor connectivity citations are public GPL files at
`lineage-geminipda/android_kernel_planet_mt6797` commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`, the revision the Wi-Fi audit
pinned. Every Bluetooth-relevant file cited from it was hashed against the
Gemian v8 source commit `59e00a9144d782e148332009a835b99c43382467`:
`stp_chrdev_bt.c`, `wmt_func.c`, `wmt_core.c`, `psm_core.c`, `stp_btif.c`,
`btif_plat.c` and `mtk_wcn_consys_hw.c` are byte-identical; `stp_core.c`
differs only in the parser braces the full-STP note already records. Gemian's
BlueZ driver (`drv_bt/`) exists only in the Gemian tree and is cited at that
commit. Mainline citations are Linux `7.1.3` as pinned in
`kernel/manifest.json`. Exact URLs, sizes and SHA-256 values are in
[`source-inputs.json`](source-inputs.json). No vendor source, firmware,
configuration file or private capture is copied into this repository;
command bytes, opcodes and register offsets are cited as protocol facts.

One licensing caveat applies to the Gemian BlueZ driver (fact F15): its
header is a MediaTek confidential/proprietary statement while its trailer
declares `MODULE_LICENSE("GPL")`. It is treated here as evidence of what the
stock Gemini does on the wire, not as reusable code.

## Part 1: verified facts

### Bluetooth is a WMT function, not a separate device

- **F1. Bluetooth is one of the CONSYS WMT functions, numbered 0.**
  `WMTDRV_TYPE_BT = 0`, `FM = 1`, `GPS = 2`, `WIFI = 3`, `WMT = 4`
  ([`wmt_exp.h` lines 112–127](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/include/wmt_exp.h#L112-L127)).
  The STP task that carries its traffic is `BT_TASK_INDX = 0` (GPS 2, Wi-Fi 3,
  WMT 4, STP 5, nine tasks in total;
  [`stp_exp.h` lines 45–55](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/include/stp_exp.h#L45-L55)).
  There is no Bluetooth register block, interrupt, reset line or GPIO on the
  AP side: the vendor `mt6797.dtsi` has no Bluetooth node at all, only the
  shared `consys@18070000`, `btif@1100c000` and the two AP-DMA channels
  ([lines 2350–2360, 2511–2517, 3759–3773](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/arch/arm64/boot/dts/mt6797.dtsi#L3759-L3773)).
  The board DTS adds nothing for Bluetooth.
- **F2. Bluetooth-on is the five-byte WMT function-control command with the
  BT PA LDO switched on first.** `wmt_func_bt_on()` runs
  `WMT_CTRL_SOC_PALDO_CTRL(BT_PALDO, PALDO_ON)`, then
  `wmt_core_func_ctrl_cmd(WMTDRV_TYPE_BT, TRUE)`; on failure it switches the
  LDO back off and triggers a firmware assert
  ([`wmt_func.c` lines 293–331](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_func.c#L293-L331)).
  `wmt_core_func_ctrl_cmd()` builds type `CMD`, opcode `OPCODE_FUNC_CTRL = 6`,
  SDU `[type, on/off]`, so the wire bytes are `01 06 02 00 00 01` for BT on
  and `01 06 02 00 00 00` for BT off, and it waits for a five-byte event
  `02 06 01 00 00`
  ([`wmt_core.c` lines 395–480](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c#L395-L480);
  header and opcode in [`wmt_core.h` lines 85–87, 349](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/include/wmt_core.h#L349)).
  BT-off reverses the order: function-control off, then PA LDO off
  (lines 333–370). The same function-control opcode with type 2 is the GPS-on
  the GPS record documents; mainline `btmtk.h` names it `BTMTK_WMT_FUNC_CTRL = 0x6`
  (F19).
- **F3. The BT PA LDO is the MT6351 `VCN33_BT` regulator at 3.3 V, and it is
  separate from the Wi-Fi one on this platform.** `mtk_wcn_consys_hw_bt_paldo_ctrl()`
  does `regulator_set_voltage(reg_VCN33_BT, 3300000, 3300000)` and
  `regulator_enable()`; off is `regulator_disable()`
  ([`mtk_wcn_consys_hw.c` lines 897–935](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L897-L935);
  handle from `regulator_get(&pdev->dev, "vcn33_bt")`, line 254, matching
  `vcn33_bt-supply` on the consys node). `CONSYS_BT_WIFI_SHARE_V33` is 0
  and `CONSYS_PMIC_CTRL_ENABLE` is 1
  ([header lines 39–40](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/include/mtk_wcn_consys_hw.h#L39-L40)),
  so the shared-counter variant is compiled out. The local
  [VCN33 contract](../2026-09-08-mt6351-mfd-upstream-preparation/VCN33.md)
  already notes that one voltage selector serves both LDOs. The common
  power-on also switches both PA LDOs on around RF calibration and off again
  afterwards
  ([`wmt_ic_soc.c` lines 1168–1186](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_ic_soc.c#L1168-L1186)),
  which the Wi-Fi audit's finding 2 records.
- **F4. Function-on triggers the whole common power-on if WMT is not already
  on.** `opfunc_func_on()` checks `eDrvStatus[WMTDRV_TYPE_WMT]` and calls
  `opfunc_pwr_on()` first, which is the sequence the Wi-Fi audit mapped
  (hardware power, BTIF open, STP mode negotiation, ROM patch download, RF
  calibration, coexistence)
  ([`wmt_core.c` lines 1134–1177](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c#L1134-L1177)).
  Bluetooth has no firmware of its own: the two retained `ROMv3_patch_*`
  files are the only patch inputs and the ROM applicability review attributes
  both to the installed pair. Bluetooth-specific firmware configuration is
  limited to the `coex_bt` WMT command (`01 10 0B 00 02 ...`, six bytes filled
  from `WMT_SOC.cfg` keys `coex_bt_rssi_*`/`coex_bt_pwr_*`) in the
  coexistence table
  ([`wmt_ic_soc.c` lines 156–166, 837–846, 1827–1832](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_ic_soc.c#L837-L846)),
  plus the shared antenna setting `coex_wmt_ant_mode=1` already read from
  the live configuration
  ([config summary](../2026-07-12-connectivity-wmt-recovery/results/wmt-config-summary.txt)).
  The CONSYS AFE block at `0x180b6000` that the GPS record found written by
  the common power-on covers the Bluetooth receive registers too; it is not
  repeated here.

### What travels over STP for Bluetooth

- **F5. The BT task carries plain H:4 HCI packets, unmodified.** The vendor
  Bluedroid character device writes the user buffer straight into
  `mtk_wcn_stp_send_data(o_buf, count, BT_TASK_INDX)` and reads with
  `mtk_wcn_stp_receive_data(i_buf, count, BT_TASK_INDX)`
  ([`stp_chrdev_bt.c` lines 175–215, 222–315](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/bt/stp_chrdev_bt.c#L175-L215)).
  The STP core recognizes HCI Reset on the way out (`01 03 0c 00`) and its
  Command Complete on the way in (`04 0e 04 01 03 0c 00`) purely for timing
  logs
  ([`stp_core.c` lines 1319–1325, 2683–2688](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/stp_core.c#L2683-L2688)),
  which confirms the H:4 indicator byte is part of the payload. Per-packet
  size is bounded by the chrdev's 2048-byte buffers (line 73).
- **F6. The STP frame around it is the full-mode frame the Wi-Fi work already
  decoded, with task 0 in header byte 1.** TX builds
  `header[1] = (type << 4) | (length >> 8)` and RX parses `(byte & 0x70) >> 4`
  ([`stp_core.c` lines 1126, 1158, 1743, 2083](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/stp_core.c#L1126)),
  so a Bluetooth frame has `0x0n` where WMT has `0x4n` and GPS `0x2n`. The
  sequence/ACK bits, length-sum header checksum and CRC-16 trailer are those
  of the [full-STP note](../2026-10-03-mt6797-wifi-audit/FULL_STP.md). BTIF
  full mode is `MTKSTP_BTIF_FULL_MODE` in the supported-protocol mask
  ([`stp_core.h` line 89](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/include/stp_core.h#L89);
  `mtk_wcn_stp_is_btif_fullset_mode()`, `stp_core.c` lines 3090–3096).
- **F7. The STP core has two delivery paths for BT frames, selected by a
  "bluez" flag.** With `mtk_wcn_stp_set_bluez(1)` an in-order BT frame is
  handed to the registered `mtk_wcn_sys_if_rx()` callback directly and ACKed,
  bypassing the ring buffer; otherwise it is queued to `ring[0]` and the BT
  event callback wakes the chrdev reader
  ([`stp_core.c` lines 1286–1330, 3313–3322](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/stp_core.c#L1286-L1330)).
  Bluedroid's `/dev/stpbt` uses the ring (`BT_open` calls `set_bluez(0)`,
  lines 375–410); Gemian's BlueZ driver uses the direct path (F15).
- **F8. Bluetooth traffic drives the chip's sleep/wake protocol, and the wake
  is a BTIF register pulse, not a byte.** Every non-WMT send passes through
  the power-saving monitor: if the chip is asleep the data is held and WMT is
  asked to wake it
  ([`stp_core.c` lines 2596–2680](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/stp_core.c#L2596-L2680)).
  Sleep is the WMT command `01 03 01 00 01` (event `02 03 02 00 00 01`) after
  `STP_PSM_IDLE_TIME_SLEEP = 30` ms idle
  ([`wmt_core.c` lines 167–174, 1399–1459](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c#L167-L174);
  [`psm_core.h` lines 63–65](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/include/psm_core.h#L63-L65)).
  In BTIF full-set mode the wake is `WMT_CTRL_SOC_WAKEUP_CONSYS`
  (lines 1460–1467), which reaches `hal_btif_raise_wak_sig()`: clear the
  `BTIF_WAK` bit, wait 64–96 µs (longer than one 32 kHz period), set it again
  ([`btif_plat.c` lines 1088–1110](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/btif/common/btif_plat.c#L1088-L1110);
  path via [`stp_btif.c` lines 197–212](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/linux/stp_btif.c#L197-L212)
  and [`mtk_btif_exp.c` lines 358–373](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/btif/common/mtk_btif_exp.c#L358-L373)),
  followed by the wake event `02 03 02 00 00 03`. The single-byte `0xFF` wake
  is the SDIO/UART variant only. Power saving is enabled by default
  (`gPsEnable` gates `mtk_wcn_stp_psm_enable(gPsIdleTime)`,
  [`wmt_lib.c` lines 85, 643–649](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_lib.c#L643-L649)),
  and the BT stack can turn it off through `COMBO_IOCTL_BT_SET_PSM`
  (`stp_chrdev_bt.c` lines 60, 342–348). The
  [BTIF mandatory-mode review](../2026-10-03-mt6797-wifi-audit/BTIF_MANDATORY.md#revision-matched-resources-and-wake-boundary)
  already concluded that the first fresh-power exchange needs no wake pulse;
  this fact only adds when the pulse becomes necessary.
- **F9. Whole-chip reset reaches the Bluetooth stack as a synthesized HCI
  Hardware Error event.** The chrdev registers a WMT reset-message callback;
  after `WMTRSTMSG_RESET_END` the next read returns `04 10 01 00` once and
  then blocks until reopen
  ([`stp_chrdev_bt.c` lines 90, 96–130, 230–260](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/bt/stp_chrdev_bt.c#L230-L260)).
  Close sends BT function-control off (lines 412–426). Observed on Gemian:
  `hci_stp_close` called `wmt_func_bt_off`, releasing the BT vote, and the
  later WLAN-off reached common power-off
  ([trace receipt](../2026-09-26-gemian-wifi-reference/results/trace-shared-off-v8-1.json)).

### Transport hardware

- **F10. BTIF is the only AP-side Bluetooth transport, and it is active in
  Gemian.** Vendor DT: `btif@1100c000` (`0x1000`, SPI 130 level-low, clocks
  `INFRA_BTIF` and `INFRA_AP_DMA`), `btif_tx@11000a00` (SPI 116) and
  `btif_rx@11000a80` (SPI 117), each `0x80`
  ([`mt6797.dtsi` lines 2350–2360, 2511–2517](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/arch/arm64/boot/dts/mt6797.dtsi#L2511-L2517)).
  The 2026-07-14 live capture shows `mtk_btif` bound with TX/RX DMA interrupt
  counts growing between two reads (44 983/25 764 after 38 880/21 806)
  ([repeat capture lines 31–59](../2026-07-12-connectivity-wmt-recovery/results/live-connectivity-repeat-20260714.txt)).
  `CONFIG_MTK_BTIF=y`, `CONFIG_MTK_COMBO=y`, `CONFIG_MTK_COMBO_CHIP_CONSYS_6797=y`
  and `CONFIG_MTK_COMBO_BT=y` are set
  ([defconfig lines 242–251](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/arch/arm64/configs/aeon6797_6m_n_defconfig#L242-L251)).
  The register, FIFO (16 TX / 8 RX bytes), PIO and DMA contract is in the
  [BTIF mandatory-mode review](../2026-10-03-mt6797-wifi-audit/BTIF_MANDATORY.md)
  and is not repeated.
- **F11. The vendor Android defconfig builds no kernel Bluetooth stack.**
  `CONFIG_BT` does not appear in `aeon6797_6m_n_defconfig` (only the
  `CONFIG_MTK_COMBO_BT` chrdev), so the stock Android path is Bluedroid in
  userspace over `/dev/stpbt` (major 192, class `stpbt`;
  [`stp_chrdev_bt.c` lines 36–37, 460–463](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/bt/stp_chrdev_bt.c#L36-L37)).
  The Android vendor libraries that drive it (`libbluetooth_mtk.so` and
  relatives) are in the retained image
  ([userspace summary line 16](../2026-07-12-connectivity-wmt-recovery/results/userspace-summary.txt))
  and are proprietary; their HCI initialization is not readable from this
  repository. The Kconfig in the lineage tree declares a second symbol,
  `MTK_COMBO_BT_HCI` "MediaTek Combo Chip BlueZ driver" (lines 219–236),
  but that tree has neither the `drv_bt/` directory nor a Makefile line for it.

### Gemian's BlueZ driver: the one stock-like HCI path that is readable

- **F12. Gemian runs an in-kernel BlueZ HCI device over STP.** The Gemian
  tree adds `drivers/misc/mediatek/connectivity/drv_bt/` built as
  `hci_stp.o` under `CONFIG_MTK_COMBO_BT_HCI`
  ([`connectivity/Makefile` lines 31–33](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/Makefile#L31-L33),
  [`drv_bt/Makefile`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/drv_bt/Makefile)).
  The 2026-09-26 v8 reference boot had `hci0 UP RUNNING` and its function
  trace recorded `hci_stp_open -> wmt_func_bt_on` and
  `hci_stp_close -> wmt_func_bt_off`
  ([trace receipt](../2026-09-26-gemian-wifi-reference/results/trace-shared-off-v8-1.json)),
  so this driver, not `/dev/stpbt`, is what the Gemian desktop uses.
- **F13. Its HCI device is `HCI_UART` bus with open/close/flush/send only;
  initialization runs inside open.** `hci_stp_init()` allocates one
  `hci_dev`, sets `bus = HCI_UART`, the four callbacks and
  `HCI_QUIRK_RESET_ON_CLOSE`, and registers it
  ([`hci_stp.c` lines 1489–1537](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/drv_bt/linux/hci_stp.c#L1489-L1537)).
  `hci_stp_open()` calls `mtk_wcn_wmt_func_on(WMTDRV_TYPE_BT)` (F2, F4),
  requires `mtk_wcn_stp_is_ready()`, runs the vendor init script (F14), then
  registers the direct RX callback, sets the bluez flag (F7) and
  `HCI_RUNNING`; failure turns BT off again
  ([lines 1273–1340](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/drv_bt/linux/hci_stp.c#L1273-L1340)).
  Send prepends nothing: the H:4 type byte is already `bt_cb(skb)->pkt_type`
  and the frame goes to `mtk_wcn_stp_send_data(skb->data, skb->len, BT_TASK_INDX)`
  from a transmit thread (`HCI_STP_TX = HCI_STP_TX_THRD`, header line 86;
  send at lines 601, 726). Receive is a hand-written H:4 state machine
  (`stp_rx_event_cb_directly`, lines 1059–1215), the same job
  `h4_recv_buf()` does upstream
  ([`hci_uart.h` line 165](https://github.com/gregkh/linux/blob/v7.1.3/drivers/bluetooth/hci_uart.h#L165)).
  Close clears `HCI_RUNNING`, waits for a pending reset, unregisters the
  callbacks, clears the bluez flag and sends BT off (lines 1380–1416).
- **F14. The selected vendor init script is six HCI commands, all vendor
  opcodes except Reset, sent before BlueZ sees the device.** The active
  `init_table[]` (the `#else` branch, lines 233–243) is: Read BD_ADDR
  (`01 09 10 00`), Set BD_ADDR (`0xFC1A`, 6 bytes), Set Radio (`0xFC79`,
  6 bytes), Set TX power offset (`0xFC93`, 3 bytes), Set Sleep (`0xFC7A`,
  7 bytes), HCI Reset
  ([`hci_stp.c` lines 113–201, 233–243](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/drv_bt/linux/hci_stp.c#L233-L243)).
  Each command waits for an exact Command Complete, 100 ms per command and
  600 ms for Reset (`hci_stp.h` lines 112–113). The parameters come from a
  `btradio_conf_data` read from `/data/BT.cfg`, else `/data/bluetooth/BT.cfg`,
  else compiled defaults, which the driver then writes back as the internal
  file (lines 105–106, 361–420, 831–990). The default radio bytes are
  `07 80 00 06 05 07`, sleep `03 40 1F 40 1F 00 04`, TX offset `FF FF FF`
  ([`bt_conf.h` lines 36–44](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/drv_bt/include/bt_conf.h#L36-L44)).
  A larger 23-command table (link-key type, unit key, encryption, PCM codec,
  OSC/LPO, PTA, de-sense, sleep-control register writes) is compiled out
  (lines 205–231); its comment attributes the active list to the vendor's
  Android `radiomod.c` for MT6630-class chips.
- **F15. The BD address is read from the controller first and only written if
  it is not the placeholder.** The default configured address is
  `00:00:46:02:79:01` (`bt_conf.h` line 38). When the stored address equals
  it, the driver issues Read BD_ADDR and uses the controller's eFUSE value;
  if that is also the placeholder, random generation is compiled out
  (`BD_ADDR_AUTOGEN (0)`, `hci_stp.h` line 98) and the placeholder is written
  back with `0xFC1A` (lines 831–990, 943). Consequence: whether this Gemini
  has a unique factory address is decided by the controller's eFUSE, which no
  retained capture records (H6). Upstream `btmtk_set_bdaddr()` uses the same
  `0xfc1a` opcode
  ([`btmtk.c` lines 369–385](https://github.com/gregkh/linux/blob/v7.1.3/drivers/bluetooth/btmtk.c#L369-L385)).
  Licensing: `hci_stp.c` opens with MediaTek's confidential/proprietary
  statement (lines 1–36) and ends with `MODULE_LICENSE("GPL")`; the source is
  therefore cited for behavior only.
- **F16. Bluetooth SCO audio does not go through HCI on this platform.** The
  vendor DT describes `btcvsd@10001000` with `mediatek,audio_bt_cvsd`,
  offsets `<0xf00 0x800 0xfd0 0xfd4 0xfd8>` (INFRA MISC, `conn_bt_cvsd_mask`,
  CVSD MCU read/write, packet indicator), windows at `0x10001000`
  (infracfg), `0x18000000` (CONSYS "PKV") and `0x18080000` (CONSYS SRAM
  bank 2), and SPI 286
  ([`mt6797.dtsi` lines 822–830](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/arch/arm64/boot/dts/mt6797.dtsi#L822-L830)).
  Voice samples are exchanged through CONSYS shared SRAM, which is why the
  compiled-out PCM/codec HCI commands in F14 are "not used" on this board.

### Mainline 7.1.3 and this repository

- **F17. Mainline already drives a MediaTek BTIF as a 16550 and a built-in
  CONSYS Bluetooth core over it, for MT7622.** `8250_of.c` matches
  `mediatek,mtk-btif` to `PORT_MTK_BTIF`
  ([lines 349–350](https://github.com/gregkh/linux/blob/v7.1.3/drivers/tty/serial/8250/8250_of.c#L349-L350)),
  defined as a 16-byte-FIFO 16550 variant
  ([`8250_port.c` lines 265–272](https://github.com/gregkh/linux/blob/v7.1.3/drivers/tty/serial/8250/8250_port.c#L265-L272),
  [`serial_core.h` line 214](https://github.com/gregkh/linux/blob/v7.1.3/include/uapi/linux/serial_core.h#L214)).
  `mt7622.dtsi` has `btif: serial@1100c000` (`reg-shift = <2>`,
  `reg-io-width = <4>`) with a `bluetooth { compatible = "mediatek,mt7622-bluetooth"; }`
  serdev child
  ([lines 526–545](https://github.com/gregkh/linux/blob/v7.1.3/arch/arm64/boot/dts/mediatek/mt7622.dtsi#L526-L545);
  [binding](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/net/bluetooth/mediatek,mt7622-bluetooth.yaml)).
  The same physical base as the Gemini's BTIF, and the BTIF offsets the
  mandatory-mode review recorded (data `+0x00`, interrupt enable `+0x04`,
  IIR/FIFO control `+0x08`, line status `+0x14`) are the 16550 layout at
  `reg-shift = <2>`. Mainline `mt6797.dtsi` has no BTIF node, while
  `CLK_INFRA_BTIF` (30) and `CLK_INFRA_AP_DMA` (46) exist
  ([`mt6797-clk.h` lines 150, 166](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/clock/mt6797-clk.h#L150)).
- **F18. `btmtkuart` implements STP framing with the sequence, ACK and CRC
  fields fixed at zero.** Its header is `prefix 0x80`, big-endian
  `dlen` with the task in the top nibble (`type = 0`), `cs = 0`, and a
  two-byte zero trailer; the receiver accepts any frame whose first byte is
  `0x80` and length is at most 2048
  ([`btmtkuart.c` lines 44–48, 296–340, 726–760](https://github.com/gregkh/linux/blob/v7.1.3/drivers/bluetooth/btmtkuart.c#L726-L760)),
  then feeds the payload to `h4_recv_buf()`. Against F6 this is the full-mode
  frame with `seq = ack = 0`, no header checksum and no CRC, which the MT7622
  firmware tolerates ("MT7622 doesn't care about checksum value"). Whether
  the MT6797 ROM accepts it is not established (H3).
- **F19. `btmtkuart` and `btmtk` do WMT over HCI, not over an STP WMT task.**
  Every WMT operation is wrapped in HCI vendor command `0xfc6f` with a
  `btmtk_wmt_hdr {dir, op, dlen, flag}`; the opcodes match the vendor's
  (`PATCH_DWNLD 0x1`, `WAKEUP 0x3`, `HIF 0x4`, `FUNC_CTRL 0x6`, `RST 0x7`,
  `SEMAPHORE 0x17`)
  ([`btmtk.h` lines 49–74](https://github.com/gregkh/linux/blob/v7.1.3/drivers/bluetooth/btmtk.h#L49-L74);
  [`btmtk.c` line 662](https://github.com/gregkh/linux/blob/v7.1.3/drivers/bluetooth/btmtk.c#L662)).
  `btmtkuart_setup()` sends wake-up, queries the firmware semaphore,
  downloads the patch, sends `FUNC_CTRL` on for BT and the `0xfc7a` sleep
  parameters
  ([lines 589–700](https://github.com/gregkh/linux/blob/v7.1.3/drivers/bluetooth/btmtkuart.c#L589-L700));
  the `hci_dev` gets `set_bdaddr = btmtk_set_bdaddr` and
  `HCI_QUIRK_NON_PERSISTENT_SETUP` (lines 864–877). The match table is
  MT7622/MT7663/MT7668 only (lines 959–977), and the MT7622 entry needs a
  `mediatek/mt7622pr2h.bin` firmware that is not the ROMv3 patch format
  (`btmtk_setup_firmware`, lines 276–360). On the Gemini the vendor never
  sends WMT inside HCI: WMT is STP task 4 and the patch is downloaded there
  before Bluetooth exists (F4). Kconfig: `BT_MTKUART` depends on
  `SERIAL_DEV_BUS` and selects `BT_MTK`
  ([`Kconfig` lines 441–449](https://github.com/gregkh/linux/blob/v7.1.3/drivers/bluetooth/Kconfig#L441-L449)).
- **F20. Mainline has a generic CONSYS CVSD audio driver whose binding
  matches the vendor node shape.** `mtk-btcvsd.c` matches
  `mediatek,mtk-btcvsd-snd`, reads a five-element `mediatek,offset` array
  with exactly the vendor's meaning (infra misc, cvsd mask, MCU read, MCU
  write, packet indicator), maps `reg` 0 as the PKV window and `reg` 1 as
  SRAM bank 2, and takes infracfg through a `mediatek,infracfg` syscon
  phandle
  ([lines 1322–1337, 1345–1356, 1391–1392](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/common/mtk-btcvsd.c#L1345-L1356)).
  The vendor node carries the infracfg window as `reg` 0, so a mainline node
  drops it and shifts the other two.
- **F21. This repository has a working mainline WMT transport but no
  Bluetooth consumer.** The default query and the mandatory set-options/full-mode
  negotiation have each completed one round trip on the device
  ([runtime 2](../2026-10-03-mt6797-wmt-default-query/results/runtime-2.json),
  [runtime 1](../2026-10-03-mt6797-wmt-negotiate/results/runtime-1.json)),
  and the identity capture returned a pre-patch chip reply
  ([CHIP_REPLY.md](../2026-10-03-mt6797-wifi-audit/CHIP_REPLY.md)). All of
  it is one-shot WMT-task diagnostics in proposals 0086–0100: no task-0
  demultiplexing, no `hci_dev`, no ROM patch, no calibration. The Gemini DT
  has no BTIF node and the passive CONSYS owner holds, but never enables,
  the VCN33-BT handle (Wi-Fi audit finding 2;
  [proposal 0025](../../patches/proposals/0025-soc-mediatek-acquire-passive-MT6797-CONSYS-VCN-handl.patch)).

## Part 2: hypotheses, ranked by value per device minute

"Gemian read" is one bounded, read-only inspection of the running stock
kernel over the known-good LAN SSH path under standing authorization;
"mainline boot" is a new reviewed experiment with its own candidate,
hypothesis, decision branches and stop conditions. None is admitted by this
record.

1. **H1. The ROM answers HCI Reset on task 0 after function-control BT-on,
   without a ROM patch or RF calibration.** The BT core and HCI parser live
   in ROM (`MT279 ROM E1`); the patch and calibration fix radio behavior,
   not command handling. If true, Bluetooth transport work can proceed in
   parallel with the Wi-Fi common-init effort instead of waiting behind it,
   and it gives the first positive control of a non-WMT STP task. If false,
   Bluetooth is strictly behind the ROM patch step. Test: a mainline boot that
   extends the existing negotiated full-mode session with, in order, VCN33-BT
   enable at 3.3 V (F3), `01 06 02 00 00 01` on task 4 expecting
   `02 06 01 00 00` (F2), then `01 03 0c 00` on task 0 expecting
   `04 0e 04 01 03 0c 00` (F5), each with a bounded deadline, then BT off and
   VCN33-BT off. Decision branches: both events (H1 true); function-control
   event but no HCI event (BT task delivery or sequencing problem, inspect the
   ACK/seq trace); no function-control event (BT-on needs the patched image,
   H1 false). Confidence: medium. This is the "one HCI reset" the roadmap
   named, made concrete.
2. **H2. The same session can read the controller identity with standard
   HCI, which fixes the mainline driver's version table without any vendor
   command.** After H1's reset, `Read Local Version Information`
   (`01 01 10 00`) and `Read BD_ADDR` (`01 09 10 00`) are plain Bluetooth
   core commands; the vendor init script itself starts with the latter (F14).
   Test: append the two commands to the H1 boot and record HCI/LMP versions,
   manufacturer (expected 70, MediaTek) and the returned address. Confidence:
   high if H1 holds.
3. **H3. The MT6797 ROM does not accept `btmtkuart`-style STP frames (zero
   sequence/ACK/CRC), so `btmtkuart` cannot be bound to the BTIF as-is even
   with an 8250 BTIF node.** F6 says the vendor runs full mode with real
   sequence, checksum and CRC fields after set-options; F18 says `btmtkuart`
   never computes them. Two sub-cases decide the mainline shape: (a) in the
   default (pre set-options) mode the ROM may ignore those fields, in which
   case a BT-only driver could stay in default mode and reuse `btmtkuart`'s
   framing; (b) if the ROM validates CRC in either mode, the mainline driver
   must own the full-mode framing the repository already implements for WMT.
   Test: in the H1 boot, after the positive HCI Reset, send one more HCI Reset
   framed with `seq = ack = 0`, `cs = 0`, zero CRC and record whether an
   event or a NAK/no-response follows. Confidence: medium that (b) holds; the
   repository's full-STP codec exists either way, so this changes reuse, not
   feasibility.
4. **H4. WMT-over-HCI (`0xfc6f`) is not handled by the MT6797 ROM, so
   `btmtk`'s firmware and function-control helpers are not reusable; only
   `btmtk_set_bdaddr` and the H:4 receive helper are.** The vendor never
   sends `0xfc6f` (F19), and its WMT lives on task 4. Test: one `0xfc6f`
   `FUNC_CTRL` query in the H1 boot; a Command Complete or a vendor event
   proves the opposite. Confidence: medium-high that it is unsupported. Either
   way the mainline Bluetooth driver should be a small new `hci_dev` on a
   shared STP-channel API, as the roadmap says, with WMT staying in the
   CONSYS owner.
5. **H5. Bluetooth works with power saving disabled, and the first mainline
   driver should not send the vendor sleep parameters.** The 30 ms sleep is
   initiated by the host (F8); if no `01 03 01 00 01` is ever sent, the chip
   stays awake and no BTIF wake pulse is needed. Sending `0xFC7A` (F14) may
   enable controller-side sleep that then requires the `BTIF_WAK` pulse before
   every transmit. Test: in the H1 boot, wait two seconds after the Reset
   event and send a second Reset without any wake action; a reply confirms the
   chip stayed awake. Confidence: high. Power saving becomes a later task with
   the wake pulse of F8 and the idle timer.
6. **H6. This unit's controller eFUSE holds a unique BD address, so Gemian's
   `hci0` address is factory-assigned rather than the `00:00:46:02:79:01`
   placeholder (F15).** Test: a Gemian read of `hciconfig hci0` or
   `btmgmt info` plus `/data/bluetooth/BT.cfg` and the `[HCI-STP]` kernel log
   lines, all read-only. If the address is the placeholder, mainline must
   supply one (`local-bd-address` DT property path with `btmtk_set_bdaddr`,
   as `btmtkuart` does) and Gemian users already share one address.
   Confidence: medium; MediaTek phones normally program eFUSE, but Planet's
   configuration is unverified.
7. **H7. The vendor radio settings (`0xFC79`, `0xFC93`) are needed for
   acceptable range and TX power but not for a link to form.** They are
   board-level RF trims from `bt_conf.h` defaults or a Gemian `BT.cfg`. Test:
   after H1/H2 succeed, a later mainline boot that pairs and connects a known
   device with and without the two commands, comparing RSSI; needs the
   Wi-Fi-style measurement discipline. Confidence: medium. The values are
   vendor configuration, not copied here; a mainline driver should read them
   from a firmware-style file or DT only with a rights decision.
8. **H8. MT6797 BTIF is register-compatible with the 8250 subset mainline
   uses for MT7622, so a `serial@1100c000` node with `mediatek,mtk-btif`,
   `reg-shift = <2>`, `reg-io-width = <4>`, SPI 130 and `CLK_INFRA_BTIF` would
   probe as a `ttyS` port.** The offsets match (F17); the MediaTek extensions
   (`DMA_EN +0x4c`, wake bit, sleep enable, timeout reset) are outside the
   8250 driver's reach and would need a small platform layer for F8. Test:
   offline first (DT schema, compile), then a mainline boot that only probes
   the port and reads LSR without touching CONSYS; low value until H3
   decides whether a serdev `btmtkuart`-shaped driver is viable at all, so
   this is deferred behind H1–H3.
9. **H9. SCO/HFP audio can reuse `mtk-btcvsd` with a Gemini node derived from
   F16/F20 once BT links work and the AFE record owns the audio side.** Test:
   offline DT and compile only, now; device test after the first ACL link and
   after the [audio record](../2026-10-04-gemini-audio-re/README.md)'s AFE
   step. Confidence: high for the binding fit, unknown for CONSYS firmware
   participation.
10. **H10. Bluetooth coexistence configuration (`coex_bt`, antenna mode 1) is
    only required when Wi-Fi and Bluetooth are active together.** The values
    are private `WMT_SOC.cfg` content. No test now; carry into the Wi-Fi
    common-init owner, which already sends the coexistence table.

## Consequences for the roadmap (no changes applied here)

- The roadmap's Bluetooth shape is confirmed from source: an `hci_dev` over
  an STP task-0 channel, with WMT staying on task 4 in the CONSYS owner.
  `btmtkuart` contributes framing knowledge and `btmtk_set_bdaddr`; its
  WMT-over-HCI path and firmware loader do not apply (F19, H4). Gemian's
  `hci_stp.c` shows the exact behavior to reproduce but is not reusable code
  (F15).
- The first Bluetooth device test (H1 + H2 + H5, one boot) depends only on
  what already runs: the negotiated full-mode session, VCN33-BT and the
  existing deadline machinery. It does not depend on the ROM patch or RF
  calibration, so it can be scheduled before the Wi-Fi common-init owner is
  complete. If it succeeds it also provides the positive control for a
  non-WMT task that the GNSS step needs.
- The BD address decision (H6) is a Gemian read with no risk and should
  precede any mainline driver that registers a public address.
- SCO audio and coexistence are separate later steps with clear mainline
  homes (`mtk-btcvsd`, the coexistence table in common init).

## Validation

Documentation-only change: `./scripts/check-repository` and link checks
apply; no kernel build, DT check or device action was performed. Line
numbers were taken from the exact fetched files recorded in
[`source-inputs.json`](source-inputs.json).

## H6 Gemian read (2026-10-05)

One bounded read-only inspection over the known-good Gemian Wi-Fi SSH path
checked boot ID `c52cec49-a635-45c3-af32-aba3b95b4c1c` and kernel `3.18.41+`
before and after. It read `hci0`'s sysfs address and name and looked for
`/data/BT.cfg`, `/data/bluetooth/BT.cfg` and address-related kernel log lines.
No HCI command, management request or radio action was issued.

Neither configuration file exists, and the kernel log has no matching lines.
Per F15, Gemian's driver therefore started from the compiled placeholder and
issued Read BD_ADDR. The address `hci0` reports is not the placeholder, so
it is the controller's own reply. The value is a device identifier and is
kept in private storage only.

H6 is answered for this unit: the controller supplies a non-placeholder
address, so a first mainline driver does not need to set one. Whether that
address is unique per unit cannot be shown from one device. The controller
may hold a programmed eFUSE value or a ROM-derived default.
