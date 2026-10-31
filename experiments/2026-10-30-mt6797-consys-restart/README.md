# Experiment: restarting the MT6797 Wi-Fi firmware within one boot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-30-mt6797-consys-restart` |
| Status | `planned`: design for owner review; nothing implemented or run |
| Subsystem | CONSYS power, WMT/STP, EMI, WLAN HIF |
| Device variant | named Gemini PDA (MT6797X), development station |
| Date(s) | 2026-10-30 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

The [development station](../2026-10-30-mainline-dev-station/README.md)
can load, unload and re-attach the mac80211 layer (0338 to 0340) on one
firmware start. Firmware, HIF and WMT changes still need a reboot, because
CONSYS starts the firmware once per boot and has no stop path
([restart boundary](../2026-10-13-mt6797-wifi-native-delivery-probe/FIRMWARE_RESTART_BOUNDARY.md)).
A restart is also what a daily driver needs to recover from a firmware
crash without rebooting.

**Question:** can CONSYS stop the WLAN firmware and start it again in one
boot, following the vendor driver's own sequences, with every step bounded
and observable?

## What the vendor driver does

Source: the public Gemian kernel, gemian/gemini-linux-kernel-3.18 at
`8cfe6596a503612e3332d9c26e292a19525a7f07`. `C/` stands for
`drivers/misc/mediatek/connectivity/common/common_main/` and `W/` for
`drivers/misc/mediatek/connectivity/wlan/gen3/`. The running Gemian config
builds the SOC (MT6797) CONSYS, the gen3 WLAN driver over the AHB HIF, and
CCF power control.

**WLAN off.** This is `/dev/wmtWifi` `'0'`, which calls
`mtk_wcn_wmt_func_off(WIFI)`.
- On a SOC chip this sends no WMT command. It calls `wlanRemove()`, then
  switches off VCN33-WIFI (`C/core/wmt_func.c:729-758`,
  `W/os/linux/hif/ahb_sdioLike/ahb.c:1472-1505`).
- `wlanAdapterStop()` (`W/common/wlan_lib.c:941-1040`):
  - clears the queues and disables the interrupt;
  - sends `CMD_ID_NIC_POWER_CTRL` (0x04) with power mode 1, on TC4 with no
    response;
  - drains once, then polls WCIR bit 21 (`WLAN_READY`) until it clears, at
    1 ms per poll;
  - then sets FW own.
- On timeout it falls back to a mailbox power-off interrupt, and after 512
  polls to a firmware assert and whole-chip reset.
- The CONN domain powers off only when WIFI was the last client. If BT, FM
  or GPS is still on, CONSYS stays powered
  (`C/core/wmt_core.c:1340-1360`). Both branches were already observed on
  Gemian ([Wi-Fi hardware notes](../../docs/hardware/mt6797-wifi.md)).

**CONN power-off** (last client):
1. STP and BTIF are closed (`C/core/wmt_ctrl.c:457-498`).
2. In `mtk_wcn_consys_hw_reg_ctrl(0)` (`C/mt6797/mtk_wcn_consys_hw.c:611-752`):
   - the SCPSYS CONN clock is disabled, which powers the domain off;
   - the VCN28 HW-mode bit is cleared;
   - VCN28 and then VCN18 are switched off.
3. There is no CPU reset and no EMI access.

**CONN power-on** (`reg_ctrl(1)`, `hw.c:288-609`):
1. VCN18, then VCN28 in HW mode.
2. Assert the CONMCU CPU reset in TOPRGU (`hw.c:338`).
3. SPM `PWRON_CONFG_EN`, then the domain on.
4. Poll chip ID `0x0279`.
5. ACR and AFE writes.
6. Release the CPU reset.
7. The full WMT `stp_init` then runs again: negotiation, the ROM patch
   download (every time) and RF calibration with PALDO toggling
   (`C/core/wmt_ic_soc.c:975-1366`).

**WLAN on** (`wlanProbe`, `W/os/linux/gl_init.c:1916-2260`):
1. VCN33-WIFI on and a fresh adapter.
2. NVRAM and the firmware file are re-read.
3. HIF sections 0 and 1, then the later sections copied into EMI region 18,
   which is reopened, written and resealed on every probe
   (`W/common/wlan_lib.c:818-880`).
4. START, then wait for `WLAN_READY`.
5. Region 19 and the EMI remap register are set only at module init, and
   never again (`hw.c:1098-1140`).

**Whole-chip reset** (`wmt_lib_cmb_rst`, `C/core/wmt_lib.c:1831-1915`):
1. STP is blocked, and `RESET_START` goes to the BT, FM, GPS and WIFI
   callbacks.
2. Every function is forced off.
3. `reg_ctrl(0)` and then `reg_ctrl(1)`, followed by a full `stp_init`.
   This is retried up to 10 times.
4. Only WIFI re-enables itself afterwards. BT, FM and GPS must reopen.

**What the source does not answer:**
- whether every earlier firmware event has been emitted before `WLAN_READY`
  clears, since the vendor just discards host state;
- whether the WLAN RAM code stops on the shared CONN MCU under 0x04.

## Proposed design

Two increments, each its own boot on the station. They are stopped, not
escalated, on any timeout.

**R1: the stop half only.** It answers whether the firmware stops when
asked.
1. Quiesce the mac layer (detach, from 0339).
2. Stop the HIF worker and interrupt, and take driver own.
3. Send 0x04 with power mode 1 and drain once.
4. Poll WCIR bit 21 clear, at 1 ms for at most 1 s.
5. Set FW own, then switch VCN33-WIFI off.
6. Stop there and record. The firmware stays stopped until the next boot.

No mailbox interrupt, assert or chip reset follows a timeout.

**R2: full CONN restart.** This is the vendor's last-client path, and the
only one that physically retires the firmware.
- **Stop:** R1, then close STP and BTIF; then domain off, VCN28 HW-mode
  bit cleared, VCN28 off and VCN18 off; then confirm the domain is off.
- **Start:** rerun the existing one-shot CONSYS sequence:
  - rails, CONMCU reset held, domain on, chip ID, ACR/AFE, reset released;
  - WMT negotiate and common init, which repeat the ROM patch and RF
    calibration;
  - VCN33-WIFI;
  - region 18 reopened, copied and resealed;
  - ordinary sections, START, `WLAN_READY`;
  - then a fresh HIF instance and a mac attach.
- **Kept:** the binding, the reservation, region 19's window and policy,
  the remap register and the firmware bytes. The vendor never redoes
  these.
- **Reset at the proven boundary:**
  - the WMT, common-init, EMI-set, EMI-copy, seal and START one-shot
    flags;
  - the STP sequence and ACK state;
  - a fresh HIF and mac instance, never cleared in place.
- **Admission:** the prestart gate must expect region 18's sealed values
  (`0xb6da2d`) rather than zero. Whether to clear region 19 again is
  decided before R2.
- **Precondition:** no BT vote. The one-shot BT H1 may hold VCN33-BT, so
  R2 refuses if any other CONN client is active.

## Safety assessment: effects needing owner review

These are new operations under [SAFETY](../../docs/SAFETY.md):
- **R1:** a firmware power-control command (0x04), then VCN33-WIFI off.
- **R2:**
  - regulator off and on for VCN18, VCN28 (including the PMIC HW-mode bit)
    and VCN33-WIFI;
  - the SCPSYS CONN domain off and on, with AXI bus protection. A
    bus-protect hang is a stop condition;
  - the CONMCU CPU reset through TOPRGU, the watchdog block. This is a
    reset operation;
  - a second set of region 18 secure MPU writes (reopen and reseal), and a
    second EMI copy;
  - a repeated ROM patch download and a repeated RF calibration with PALDO
    toggling. Calibration needs its own protocol;
  - a second firmware START, a radio-capable state.
- **Not copied from the vendor:** the automatic escalation (mailbox
  interrupt, assert, coredump, whole-chip reset with retries). Each timeout
  is a stop.
- **Recovery:** a reboot, as for any station boot. The watchdog covers a
  hang.

## Readings (predeclared, for after review)

| Observation | Reading |
|---|---|
| R1: WCIR bit 21 clears within 1 s | The firmware honours 0x04; R2 can follow |
| R1: bit 21 never clears | 0x04 does not stop this firmware; R2 is the only boundary, and R1's evidence goes into its design |
| R2: chip ID, WMT, common init and START all succeed a second time, and a scan works | The firmware restarts within one boot; CONSYS as a module becomes possible |
| R2: the second START or calibration fails | That step names what does not survive a power cycle; stop and record |

## Observations

None. Not implemented or run.

## Conclusion

Not run.

## Follow-up

Owner review of the effects above, then R1 as its own patch and station
boot.
