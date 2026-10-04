# Experiment: Gemini GPS/GNSS path reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-gps-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | MT6797 CONSYS GNSS: WMT function control, STP GPS task, LNA pin, VCN28, AFE registers, ROMv3 GNSS patch, vendor GPS userspace |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, CONSYS chip ID `0x0279`, WMT `MT279` ROM `E1`) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | [#25](https://github.com/ixoo/gemini-pda-mainline/issues/25) (M6 connectivity) |

## Question

What does the stock Gemian kernel actually do to turn the GNSS receiver on,
power and configure it, move its data, and produce a position, and what does
that imply for a mainline description? The roadmap's
[Bluetooth-then-GNSS step](../../docs/ROADMAP.md#after-wi-fi-remaining-driver-gaps)
assumed "a `gnss` device fed by the STP GPS task plus the LNA on GPIO69". This
record checks that assumption against the pinned public vendor source and the
pinned Linux 7.1.3 tree, separates verified facts from hypotheses, and ranks
the hypotheses by how they should be tested. It changes no patch, profile,
candidate or device state.

It reuses, and does not repeat, the Wi-Fi work on the shared CONSYS core: the
[Wi-Fi audit](../2026-10-03-mt6797-wifi-audit/README.md) (WMT common
initialization, ROM patch order, calibration), the
[connectivity recovery](../2026-07-12-connectivity-wmt-recovery/README.md)
(live resources, firmware inventory, userspace audit) and the
[WMT default query](../2026-10-03-mt6797-wmt-default-query/README.md) and
[negotiation](../2026-10-03-mt6797-wmt-negotiate/README.md) runtimes, which are
the only mainline STP traffic so far.

## Inputs

Every vendor citation below is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`, the commit the
[charging record](../2026-10-04-gemini-charging-re/README.md) used. The eight
GPS-relevant files were also fetched from the Planet tree at
`c5b0be85017ad0c599725e8273842efdbecdd88a` (the Wi-Fi audit's pin) and are
byte-identical, so the Wi-Fi audit's line numbers in the shared WMT files
remain valid. Every mainline citation is Linux `7.1.3` as pinned in
`kernel/manifest.json`. Exact URLs, sizes and SHA-256 values are in
[`source-inputs.json`](source-inputs.json). No vendor source, firmware or
private capture is copied into this repository; command bytes, register
offsets and configuration values are cited as facts.

Two caveats apply throughout. First, the public board DTS (`aeon6797_6m_n.dts`)
differs from the live Gemian DTB elsewhere (charging record, fact F2); for GPS
the live capture agrees with the public DTS on every property cited here, so no
public-only value is relied on. Second, the position engine and the daemon that
drive the kernel path are proprietary Android userspace; their behaviour is
inferred from exported symbols and strings already recorded in the
[userspace audit](../2026-07-12-connectivity-wmt-recovery/results/userspace-binary-audit.txt),
not from disassembly performed here.

## Part 1: verified facts

### Software architecture: two character devices, one of them a mailbox

- **F1. The GNSS receiver has no register window, interrupt, clock or
  regulator of its own in the device tree.** `mt6797.dtsi` describes it with
  two property-less pseudo-nodes, `gps { compatible = "mediatek,gps"; }` and
  `gps_emi { compatible = "mediatek,gps_emi-v1"; }`
  ([lines 4088–4094](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L4088-L4094)).
  Every hardware resource GNSS uses belongs to `consys@18070000`
  ([lines 3759–3773](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L3759-L3773):
  four windows, BGF/WDT interrupts, `SCP_SYS_CONN`, VCN18/VCN28/VCN33-BT/VCN33-Wi-Fi)
  and to the BTIF block. The live capture shows the same two nodes bound
  ([2026-07-13 rerun](../2026-07-12-connectivity-wmt-recovery/results/live-connectivity-rerun-20260713.txt)).
- **F2. `/dev/gps` (driver `gps`, compatible `mediatek,gps`) touches no
  hardware; it is a 4 KiB userspace-to-userspace mailbox plus sysfs state.**
  Its hardware hooks are null (`mt3326_gps_hw = { .ext_power_on = NULL, .ext_power_off = NULL }`,
  [`gps.c` lines 164–167](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/gps/gps.c#L164-L167)),
  so `mt3326_gps_power()` only logs (lines 200–251). `write()` copies at most
  4096 bytes into one shared `dat_buf` and `read()` hands them back
  ([lines 111–118, 798–883](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/gps/gps.c#L798-L883)).
  The sysfs files `pwrctl`, `suspend`, `status`, `state`, `pwrsave` and
  `rdelay` (lines 704–721) record the daemon's state machine and restart
  reasons ("TTFF", "monitor", "force", lines 184–195). This is the NMEA hand-off
  path between the vendor position daemon and the Android HAL. Nothing here
  maps to a mainline driver.
- **F3. `/dev/stpgps` (static major 191) is the only kernel path that carries
  GNSS data to and from the chip, and it is a thin STP channel.** `GPS_write()`
  calls `mtk_wcn_stp_send_data(buf, len, GPS_TASK_INDX)` and `GPS_read()` calls
  `mtk_wcn_stp_receive_data(buf, len, GPS_TASK_INDX)`, sleeping on a wait
  queue that the STP core wakes through `GPS_event_cb`
  ([`stp_chrdev_gps.c` lines 136–280, 537–543](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/gps/stp_chrdev_gps.c#L136-L280)).
  There is no framing, parsing or protocol knowledge in the kernel: the payload
  is opaque to it. `GPS_TASK_INDX` is 2
  ([`stp_exp.h` line 47](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/include/stp_exp.h#L47))
  and the per-task receive ring is 16 KiB (`MTKSTP_BUFFER_SIZE`, line 60).
- **F4. Opening `/dev/stpgps` is what powers the receiver; closing it powers it
  down.** `GPS_open()` calls `mtk_wcn_wmt_func_on(WMTDRV_TYPE_GPS)`, registers a
  reset callback, requires `mtk_wcn_stp_is_ready()`, registers the event
  callback for task 2 and takes a wakeup source named `gpswakelock`;
  `GPS_close()` reverses this with `mtk_wcn_wmt_func_off(WMTDRV_TYPE_GPS)`
  ([lines 446–525](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/gps/stp_chrdev_gps.c#L446-L525)).
  `WMTDRV_TYPE_GPS` is 2
  ([`wmt_exp.h` line 115](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/include/wmt_exp.h#L115)).
  The ioctls (lines 47–56, 283–400) only expose chip hardware/firmware
  version, the co-clock flag, a firmware-assert trigger and wakelock
  take/give; no ioctl configures the receiver.
- **F5. The receiver's data path, and the fact that GNSS traffic is multiplexed
  on the same BTIF/STP link as WMT and Bluetooth, are encoded in four header
  bits.** STP full-mode frames carry the task in bits 6:4 of the second header
  byte: TX builds `(type << 4) | (length >> 8)` and RX parses
  `(byte & 0x70) >> 4`
  ([`stp_core.c` lines 1156–1161, 1743, 2754–2759](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/stp_core.c#L2754-L2759)).
  A GPS frame therefore has `0x2n` in that byte, where WMT has `0x4n`. When the
  GPS ring is full the STP core discards the GPS queue instead of back-pressuring
  the peer (`mtk_wcn_stp_flush_rx_queue(GPS_TASK_INDX)`, lines 1373–1383); no
  other task is treated this way.
- **F6. The GPS EMI/"MNL offload" driver is not built and its firmware is not
  present.** `gps_emi.c` would map a 1 MiB region at `gConEmiPhyBase + 1 MiB`,
  protect it as EMI MPU region 20 and copy `/vendor/firmware/MNL.bin` into it on
  ioctl 1
  ([lines 44–47, 77–149](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/gps/gps_emi.c#L77-L149)).
  It is gated by `CONFIG_MTK_GPS_EMI`
  ([`gps/Makefile` lines 30–32](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/gps/Makefile#L30-L32)),
  which the defconfig does not set (it sets `MTK_COMBO`, `CONSYS_6797`,
  `MTK_COMBO_BT/ANT/GPS/WIFI` and `MTK_GPS_SUPPORT`,
  [lines 246–253](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L246-L253)).
  The live device-node list has `/dev/stpgps` and `/dev/gps` but no
  `/dev/gps_emi`, the firmware inventory has no `MNL.bin`, and the Gemian v8
  configuration audit recorded `CONFIG_MTK_GPS_EMI=n`
  ([shared-resource boundary](../2026-09-07-mt6797-wifi-observer-feasibility/results/shared-resource-boundary.json)).
  The rerun's "driver link present" for `soc:gps_emi` is therefore a
  platform-bus enumeration of the pseudo-node, not an active driver; the
  post-reboot capture says "enumerated" for the same node.

### WMT function-on for GPS (what runs when `/dev/stpgps` opens)

- **F7. The first function to open powers CONSYS and runs the whole WMT common
  initialization; GPS gets no shortcut.** `opfunc_func_on()` calls
  `opfunc_pwr_on()` whenever the WMT type itself is not yet `FUNC_ON`, then the
  per-function `func_on`
  ([`wmt_core.c` lines 1168–1176, 1216–1218](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c#L1168-L1176)).
  `opfunc_pwr_on` is the sequence the Wi-Fi audit mapped (hardware power, BTIF
  STP init, mode negotiation, ROM patch download, calibration, coexistence).
  The chip is powered off again only when BT, GPS, FM, Wi-Fi, LPBK, ANT and
  COREDUMP are all `POWER_OFF` (lines 1254–1261, 1355–1362). Consequence: a
  mainline GNSS device cannot be brought up before the Wi-Fi workstream's
  common-init owner exists, exactly as the roadmap assumed, and it must share
  that owner rather than re-power the block.
- **F8. The GPS-specific "on" is one five-byte WMT command.** `wmt_func_gps_on`
  calls `wmt_func_gps_pre_on` (F9) and then `wmt_core_func_ctrl_cmd(WMTDRV_TYPE_GPS, TRUE)`
  ([`wmt_func.c` lines 397–403, 533–570](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_func.c#L533-L570)).
  That command is type `0x01`, opcode `OPCODE_FUNC_CTRL` = 6, SDU length 2,
  flag byte = driver type, parameter = 1 for on / 0 for off, i.e. on the wire
  `01 06 02 00 02 01` for GPS on and `01 06 02 00 02 00` for GPS off; the
  expected event is five bytes, type `0x02`, opcode 6, SDU length 1, status 0
  ([`wmt_core.c` lines 395–497](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c#L395-L497);
  constants at [`wmt_core.h` lines 85–89, 337–338, 349](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/include/wmt_core.h#L337-L349)).
  It is the same opcode the vendor uses for BT and FM; only the flag byte
  differs. A missing event is treated as a firmware fault (lines 437–451).
- **F9. The GPS "pre-control" reduces, on this chip and configuration, to one
  host GPIO write.** `wmt_func_gps_pre_ctrl()` does two things
  ([lines 405–519](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_func.c#L405-L519)):
  (a) GPS/modem sync: `WMT_CTRL_GPS_SYNC_SET` routes to `wmt_plat_gps_sync_ctrl`,
  whose non-legacy-GPIO branch is empty on MT6797
  ([`wmt_plat_alps.c` lines 623–658](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/mt6797/wmt_plat_alps.c#L623-L658)),
  and the chip-side `ic_pin_ctrl(WMT_IC_PIN_GSYNC)` explicitly skips chip ID
  `0x0279` ("mt6797 can not access reg:0x80050078 and no need to do GPS SYNC",
  [`wmt_ic_soc.c` lines 1503–1522](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_ic_soc.c#L1503-L1522));
  (b) LNA: with `wmt_gps_lna_enable = 0` (the retained `WMT_SOC.cfg`,
  [sanitized fields](../2026-07-12-connectivity-wmt-recovery/results/wmt-config-summary.txt))
  it takes the "host pin used for gps lna" branch and issues
  `WMT_CTRL_GPS_LNA_SET` with 1 on, 0 off. The chip-pin branch (`EEDI`/`EEDO`)
  is unreachable here and is anyway a stub on MT6797 (`"TBD!!"`, returns 0,
  `wmt_ic_soc.c` lines 1538–1547).
- **F10. The host LNA control is GPIO69, driven high while GNSS is on and
  returned to the low "init" state when it is off or when CONSYS powers
  down.** `wmt_ctrl_gps_lna_set` maps 1 to `PIN_STA_OUT_H` and 0 to
  `PIN_STA_DEINIT`
  ([`wmt_ctrl.c` lines 1009–1024](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_ctrl.c#L1009-L1024)).
  On MT6797 `wmt_plat_gps_lna_ctrl` selects the consys pinctrl states
  `gps_lna_state_oh` (out high), `gps_lna_state_ol` (out low) or
  `gps_lna_state_init` (init and deinit)
  ([`wmt_plat_alps.c` lines 691–743](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/mt6797/wmt_plat_alps.c#L691-L743)).
  The board DTS defines all three on `PINMUX_GPIO69__FUNC_GPIO69`: init is
  output-low with bias disabled and slew 0, the runtime states are output
  high/low with slew 1
  ([`aeon6797_6m_n.dts` lines 1275–1312](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1275-L1312));
  the live DTB carries the same four state names
  ([runtime summary](../2026-07-12-connectivity-wmt-recovery/results/runtime-summary.txt)).
  CONSYS power-on also puts the pin in the init state and power-off deinits it
  (`mtk_wcn_consys_hw_gpio_ctrl`,
  [`mtk_wcn_consys_hw.c` lines 757–795](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L757-L795)).
  Whether an LNA is physically populated is still not shown by any capture; the
  software contract is "GPIO69 high while GNSS is on". In the local pinctrl
  driver GPIO69 is a plain GPIO with EINT49 and `I2S0_LRCK` as its alternate
  ([patch 0005](../../patches/v7.1.3/0005-pinctrl-mediatek-add-MT6797-EINT-support.patch), pin 69);
  no Gemini DT patch uses it.
- **F11. The "GPS PA LDO" is VCN28, and with this configuration it is handled
  by the common power-on, not by GPS-on.** `wmt_func_gps_on/off` only switch
  `GPS_PALDO` when `co_clock_flag & 0x0f` is non-zero and `wmt_gps_lna_enable`
  is 0 (lines 539–549, 594–605); the retained `WMT_SOC.cfg` has
  `co_clock_flag = 0`, so that branch is dead on this device. `GPS_PALDO` and
  `FM_PALDO` both resolve to `mtk_wcn_consys_hw_vcn28_ctrl`
  ([`wmt_plat_alps.c` lines 877–897](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/mt6797/wmt_plat_alps.c#L877-L897),
  [`mtk_wcn_consys_hw.c` lines 975–1003](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L975-L1003)).
  Instead, because `co_clock_type == 0`, CONSYS power-on itself sets
  `RG_VCN28_ON_CTRL = 1` (hardware control) and enables VCN28 at 2.8 V right
  after VCN18, and power-off clears the control bit and disables it
  ([lines 311–322, 724–733](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L311-L322)).
  This matches the Gemian observations already in the
  [Wi-Fi contract](../../docs/hardware/mt6797-wifi.md) (VCN28 `0x0a0c` mode bit
  following 1→0→1 across a radio cycle) and means VCN28 is a GNSS prerequisite
  that the Wi-Fi power-on must provide anyway. The vendor comment calls VCN28
  the "fm/gps" rail; the co-clock enum names TCXO (0), TSX, DCXO and VCTCXO
  types ([header lines 270–276](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/mt6797/include/mtk_wcn_consys_hw.h#L270-L276)),
  so `co_clock_flag = 0` declares a GNSS TCXO rather than a shared crystal.
- **F12. CONSYS power-on writes the connectivity analog front-end (ANA_WBG/AFE)
  registers, including two GPS receive registers, before releasing the MCU.**
  With `CONSYS_AFE_REG_SETTING = 1`, `mtk_wcn_consys_hw_reg_ctrl(1, ...)` maps
  `0x180B6000 + 0x100` and writes `RCK_01` (`+0x20` = `0x180B0160`),
  `WBG_GPS_01` (`+0x50` = `0xB8925421`), `WBG_GPS_02` (`+0x54` = `0x00006401`),
  the BT RX/TX and WF RX/TX registers, then dumps 64 words
  ([`mtk_wcn_consys_hw.c` lines 451–490](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L451-L490);
  values at [header lines 138–159](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/mt6797/include/mtk_wcn_consys_hw.h#L138-L159)).
  The extra `GPS_SINGLE` write (`+0x14 |= 0x1000`) is under
  `CONFIG_MTK_GPS_REGISTER_SETTING`, which the defconfig does not set. The
  2026-07-12 design record noted this AFE block
  ([design](../2026-07-12-connectivity-wmt-recovery/results/mt6797-connectivity-mainline-design.md#consys-is-the-power-and-firmware-owner));
  no mainline proposal (0001–0100) writes to `0x180b6000` (checked by search of
  `patches/proposals/`). This is a GNSS prerequisite, and it is also an
  unexamined difference in the Wi-Fi receive path; see H2.
- **F13. GPS-on and -off also notify userspace for Bluetooth/Wi-Fi/GPS
  "de-sense".** When GPS turns on while BT or Wi-Fi is on (or vice versa),
  `WMT_CTRL_BGW_DESENSE_CTRL` sends a command number to the WMT launcher
  daemon (`wmt_dev_send_cmd_to_daemon`), and userspace answers with a 14-byte
  de-sense packet through `WMT_IOCTL_SEND_BGW_DS_CMD` (opcode `WMT_OPID_BGW_DS`)
  ([`wmt_func.c` lines 556–563](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_func.c#L556-L563),
  [`wmt_ctrl.c` lines 627–635](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_ctrl.c#L627-L635),
  [`wmt_dev.c` lines 1097–1135](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/linux/wmt_dev.c#L1097-L1135)).
  The packet contents come from the proprietary launcher and are not in the
  public source. Single-radio GNSS tests do not trigger this path.
- **F14. Only four `WMT_SOC.cfg` keys are set on this device, and three of them
  concern GNSS.** The parser accepts a long key list
  ([`wmt_conf.c` lines 95–136](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_conf.c#L95-L136));
  the retained 80-byte file sets `coex_wmt_ant_mode=1`, `wmt_gps_lna_pin=0`,
  `wmt_gps_lna_enable=0`, `co_clock_flag=0`
  ([sanitized fields](../2026-07-12-connectivity-wmt-recovery/results/wmt-config-summary.txt)).
  Everything else, including every coexistence threshold, is left at the
  zero/default value. There is no GNSS-specific trim or calibration input in
  the configuration.

### Firmware

- **F15. GNSS code arrives with the common ROM patch, not with a GPS-specific
  download.** The retained `ROMv3_patch_1_1_hdr.bin` (46472 bytes; 46444 body)
  is the one whose strings include GNSS/geofence/FLP text
  ([runtime summary](../2026-07-12-connectivity-wmt-recovery/results/runtime-summary.txt)),
  and the RE-VM analysis shows it is download sequence 1 of 2 (firmware address
  wire bytes `00 00 0a f0`), ahead of the 210876-byte `ROMv3_patch_1_0_hdr.bin`
  ([ROM patch order](../2026-10-03-mt6797-wifi-audit/ROM_PATCH_ORDER.md)).
  Both are applied by `opfunc_pwr_on` before any function-on (F7). The vendor
  GPS driver loads no file of its own (F6). `WMT_SOC.cfg` is loaded by the WMT
  core through the firmware class (`wmt_conf_read_file`, lines 432–491).
  Redistribution rights for the patches remain unresolved
  ([firmware record](../../docs/hardware/firmware.md)).
- **F16. The receiver protocol on `/dev/stpgps` is MediaTek's binary
  host-to-GNSS-firmware protocol, consumed by the proprietary MNL
  (MediaTek Navigation Library) daemon, not NMEA.** Evidence, all previously
  recorded: the HAL `gps.mt6797.so` exports only `hal2mnl_*`/`gpshal2mnl_*`
  socket calls and no device I/O
  ([userspace audit, `gps.mt6797.so` entries](../2026-07-12-connectivity-wmt-recovery/results/userspace-binary-audit.txt));
  `mtk_agpsd` carries `mnl_to_agps`/`agps_to_mnl` sockets; Gemian's
  connectivity init rules declare `mnld` and `MPED` in the `main` class
  ([startup follow-up](../2026-09-07-mt6797-wifi-observer-feasibility/results/cycle-control-gemian-metadata.json),
  `normal_rules`); and the vendor kernel's `/dev/gps` mailbox exists to pass
  NMEA from a daemon to the HAL (F2). `mnld` itself was not in the vendor-only
  extraction and has not been audited; its payload format is unknown. The
  `gps_emi` "MNL offload" option (F6) shows MediaTek can run MNL inside the
  CONSYS MCU from `MNL.bin`, but this image does not.

### Mainline 7.1.3 and this repository

- **F17. The mainline GNSS core is a raw byte pipe with open/close hooks, which
  is the right shape for this receiver.** `include/linux/gnss.h` defines
  `gnss_operations { open, close, write_raw }`, `gnss_allocate_device`,
  `gnss_register_device` and `gnss_insert_raw`; the core calls `open` on the
  first opener and `close` on the last, forwards `write()` to `write_raw` and
  queues incoming bytes in a kfifo for `read()`
  ([`gnss.h` lines 21–61](https://github.com/gregkh/linux/blob/v7.1.3/include/linux/gnss.h#L21-L61),
  [`core.c` lines 55, 77, 164, 319](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gnss/core.c#L55)).
  `GNSS_TYPE_MTK` exists as a type label. The existing `gnss-mtk` driver is a
  serdev consumer for `globaltop,pa6h` with `vcc`/`vbackup`
  ([`mtk.c`](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gnss/mtk.c)) and
  does not apply; a new driver would implement the three operations over the
  STP GPS channel.
- **F18. The repository's mainline STP implementation only speaks the WMT task.**
  The full-STP transmitter hard-codes `out[1] = 0x40 | (length >> 8)` and the
  receiver rejects any frame whose type bits are not `0x40`
  ([proposal 0092, `wmt-full-stp-tx.h` and `wmt-full-stp.h`](../../patches/proposals/0092-soc-mediatek-compose-bounded-WMT-mode-negotiation.patch),
  patch lines 1002 and 1043). Nothing in 0086–0100 sends `OPCODE_FUNC_CTRL`,
  downloads a ROM patch, drives GPIO69, writes the AFE block (F12) or exposes a
  `gnss` device. The passive CONSYS owner holds a VCN28 regulator handle but no
  profile has enabled the rail in the vendor order
  ([Wi-Fi contract](../../docs/hardware/mt6797-wifi.md)). So today's distance to
  a first GNSS byte is: finish common init (Wi-Fi order step 4), then add a
  task demultiplexer, one function-control exchange, one pinctrl state and a
  `gnss` device.

## Part 2: hypotheses, ranked by value per device minute

Each hypothesis states what would confirm or refute it and the cheapest test.
"Gemian read" means one bounded, read-only inspection of the running stock
kernel over the known-good LAN SSH path, under the existing standing
authorization; "mainline boot" means a new reviewed experiment with its own
candidate, hypothesis and stop conditions. None is admitted by this record.
Every mainline test here presupposes a proven common initialization (ROM
patches applied, calibration run); until then the only GNSS work is offline.

1. **H1. Once common init is proven, GNSS-on is one command and one GPIO, and
   the firmware will stream task-2 frames unsolicited after it.** Prediction
   from F8–F10: after `01 06 02 00 02 01` returns status 0 and GPIO69 goes
   high, frames with `0x2n` in the type byte appear on the BTIF receive path
   without any further host command (the vendor daemon talks to the receiver,
   but the receiver also reports on its own). Refuted if the event returns
   non-zero status or nothing arrives within tens of seconds. Test: a mainline
   boot that, after the common-init owner reports success, selects the
   `gps_lna_state_oh` equivalent, sends the GPS function-on, logs the event,
   counts and retains the first N task-2 frames (size and first bytes only),
   sends function-off and returns GPIO69 low. Decision: frames mean the
   transport and power path are complete and the remaining work is protocol;
   no frames with status 0 means the daemon must send a start command first
   (see H4). Confidence: high for the command, medium for unsolicited output.
2. **H2. The missing AFE register block (F12) matters for GNSS and possibly for
   the Wi-Fi zero-reception problem.** The vendor writes receive-path analog
   values for GPS, BT and Wi-Fi at every power-on, before firmware runs;
   mainline never has. Test, offline first: compare the eleven writes against
   the MT6797 register reference if the owner's documents cover `0x180b6000`,
   then one Gemian read of the 64 dumped words after a stock boot (the vendor
   driver logs them at debug level; a read-only `devmem`-class sample of the
   same window in Gemian is cheaper than enabling logs). On mainline, add the
   writes to the CONSYS power-on in vendor order and re-run the existing
   passive channel-40 scan before any GNSS test. Decision: a nonzero Wi-Fi
   management count after adding them changes the Wi-Fi plan; no change leaves
   them as a GNSS prerequisite only. Confidence: medium that they matter;
   high that mainline omits them. This is the one finding here that should be
   fed to the Wi-Fi order now.
3. **H3. VCN28 at 2.8 V in hardware-control mode is required for GNSS and is
   already satisfied by the vendor-order power-on.** From F11. Test: none
   needed on Gemian (already observed); on mainline, the common-init owner must
   include the VCN28 steps, and the H1 boot should log the regulator state and
   `0x0a0c` before function-on. Refuted only if GNSS frames arrive with VCN28
   off, which would mean the rail feeds something else. Confidence: high.
4. **H4. The receiver needs a start/configuration message from the host before
   it produces measurements, and that message is in the proprietary `mnld`,
   not in any public source.** Supported by F16 (kernel is opaque) and by the
   vendor `GPS_write` retry comment. If H1 shows no unsolicited frames, this is
   the next explanation. Test: a Gemian read-only trace of the first bytes
   written to `/dev/stpgps` and read from it during one stock GNSS session
   (the STP debug packet log or a bounded function trace on
   `mtk_wcn_stp_send_data` with type 2, lengths and first 16 bytes only, no
   payload retention beyond that). This is the single most valuable Gemian
   measurement for GNSS: it gives both the start sequence and the receiver's
   output framing. Confidence: high that a start message exists; unknown
   content.
5. **H5. The receiver output can be turned into positions without the vendor
   daemon only if it is, or can be switched to, NMEA.** MediaTek GNSS firmware
   families expose NMEA on their serial products (`gnss-mtk`, PMTK), and the
   `GNSS_TYPE_MTK` label exists for them; the CONSYS firmware may share that
   stack. If the H4 trace shows ASCII `$G...` sentences, a mainline `gnss`
   device with `GNSS_TYPE_NMEA` is complete and gpsd works; if it shows the
   binary MNL protocol, usable GNSS on mainline needs either the proprietary
   `mnld` (ARM Android binary, same boundary as the Wi-Fi firmware) or a
   protocol reverse-engineering effort out of scope for the roadmap. Test: H4
   decides this with no extra device time. Confidence: low that it is NMEA;
   this is the main risk to the roadmap's "GNSS after Bluetooth" estimate.
6. **H6. GPIO69 drives a real external LNA and matters for fix quality, not for
   receiving frames.** From F10. Test: in the H1 boot, run two bounded captures
   with GPIO69 low and high and compare any signal-quality field once H4/H5 give
   a decoder; before that, a Gemian read of GPIO69 state during a stock session
   (expected high) is the only cheap check. Confidence: medium that an LNA is
   populated (the board DTS states exist only on this board file).
7. **H7. Suspend and power management need no GNSS-specific handling beyond
   what the vendor does: a wakeup source while open and STP sleep handled by
   the common owner.** From F4 and the STP power-saving gate (`stp_core.c`
   lines 1623–1628, which requires BTIF full-set mode). Test: none until a
   `gnss` device exists; then one open/close cycle across a suspend. Confidence:
   high.
8. **H8. The de-sense protocol (F13) can be ignored for single-radio GNSS tests
   and deferred until BT or Wi-Fi coexistence is wanted.** The packet comes from
   the proprietary launcher and is only sent when two radios overlap. Test: none;
   this is a scoping decision. Refuted if GNSS frames stop when Wi-Fi starts on
   mainline. Confidence: medium.

## What this changes in the plan

- The roadmap's step 4 assumption holds for the kernel shape (`gnss` device over
  the STP GPS task plus GPIO69), and the function-on cost is small (F8–F10).
- The hidden cost is userspace: the stock position engine is proprietary (F16).
  The H4 Gemian trace should be scheduled before any mainline GNSS boot because
  it decides whether mainline GNSS ends at raw frames or at positions.
- The AFE register block (F12, H2) is a cross-subsystem finding for the Wi-Fi
  common-init owner and should be reviewed there now; it needs no GNSS work.
- The mainline STP code must be generalized from "WMT task only" to a task
  demultiplexer (F18) before Bluetooth or GNSS can share it.

## Limitations

This review used the repository, its receipts and pinned public vendor and
mainline source. It did not inspect private captures, retained firmware in the
RE VM, the proprietary `mnld`/`libmnl` binaries or the device. F16's claim about
the protocol is an inference from exported symbols, init rules and the vendor
kernel's design, not from a trace; H4 is the test that replaces it with a fact.
The AFE register meanings are not documented in any public source inspected
here. No GNSS fix has ever been observed on this device under either kernel in
this project's records.
