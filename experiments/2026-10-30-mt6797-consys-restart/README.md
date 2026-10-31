# Experiment: restarting the MT6797 Wi-Fi firmware within one boot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-30-mt6797-consys-restart` |
| Status | `running`: R1 and R2 work on the device; every Wi-Fi layer reloads on a running station |
| Subsystem | CONSYS power, WMT/STP, EMI, WLAN HIF |
| Device variant | named Gemini PDA (MT6797X), development station |
| Date(s) | 2026-10-30, 2026-10-31 |
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

## Approval

The owner approved this design on 2026-10-31, including the effects listed
above. R2's repeated RF calibration still needs its own protocol before R2
runs.

## R1 implementation

Patch 0341, in the station series after 0340. VM checks: W=1 builds with
`mac` built in and as a module, without warnings; the station image and
modules link; checkpatch is clean. Not run on the device.

- **Trigger:** `echo 1 > /sys/bus/platform/devices/10001340.consys/wlan_stop`.
  It exists only when `mac` is a module. It is refused unless the firmware is
  ready and the layer is detached (`rmmod mac` first), and admits one attempt
  per boot.
- **Request:** NIC_POWER_CTRL (0x04), power mode 1, four bytes, at the next
  unused command sequence (at least 5). The normal-command state admits it
  after the record with that exact payload only.
- **Poll:** WCIR every millisecond, within a one-second HIF deadline, until
  bit 21 clears.
- **Then, only if it cleared:** FW own (WHLPCR bit 8 written), one WHLPCR
  read after a millisecond, and VCN33-WIFI disabled. The HIF probe holds the
  only enable of that rail: common init leaves it off (`wifi-rail=0`).
- **Either way:** the HIF context refuses every later command, and the
  firmware stays stopped until the next boot.
- **Not done:** the vendor's one TX-done drain. With the layer detached,
  this HIF has no interrupt or worker left.
- **Kernel log:**
  - `WLAN stop: power-off status=S sequence=N WCIR=…`
  - `WLAN stop: FW own WHLPCR=…, VCN33-WIFI off=R enabled=E`
  - then `WLAN stopped; a restart needs the next boot`, or
    `WLAN stop stopped (E); nothing escalated, state retained`.

The station's [cycle script](../2026-10-30-mainline-dev-station/wifi-cycles.sh)
runs it after the cycles when `STOP=1` is set.

## Readings (predeclared)

| Observation | Reading |
|---|---|
| R1: WCIR bit 21 clears within 1 s | The firmware honours 0x04; R2 can follow |
| R1: bit 21 never clears | 0x04 does not stop this firmware; R2 is the only boundary, and R1's evidence goes into its design |
| R1: bit 21 clears, then `insmod mac` is refused with `-ENODEV` and the station stays up | The stop is contained: the HIF and attach refuse a stopped firmware |
| R1: WHLPCR bit 8 reads set after FW own | FW own is not taken by the firmware once powered off; recorded, not retried |
| R2: chip ID, WMT, common init and START all succeed a second time, and a scan works | The firmware restarts within one boot; CONSYS as a module becomes possible |
| R2: the second START or calibration fails | That step names what does not survive a power cycle; stop and record |

## Observations

**R1 on station 6, boot `967d17be-e447-4e4c-b084-194e5eb7a0b4`** (boot2
`fb6d3f13…`, built at `f328f438`, `mac.ko` `335f2ec8…`; 8 CPUs, RAM root,
`/mnt/data` mounted).
- **Run:** `CYCLES=1 STOP=1` of the station's cycle script, about 20 s
  after boot.
- **Before the stop:** firmware start 0/0. One cycle: insmod 0,
  configuration `status=0`, scan with 3 BSS, rmmod 0, `mac detached;
  firmware kept`.
- **Stop:** `echo 1 > wlan_stop` returned success.
  - `WLAN stop: power-off status=0 sequence=17 WCIR=0x00100279`.
    WLAN_READY (bit 21) was clear by the time the logged WCIR was read. The
    whole stop took under 2 ms by the log stamps. Bit 20 was set in that
    read, which it is not in the ready value; its meaning is not
    established.
  - `FW own WHLPCR=0x00000000`: the driver-own bit cleared after the FW own
    write.
  - `VCN33-WIFI off=0 enabled=0`: the rail is off.
  - `WLAN stopped; a restart needs the next boot`.
- **After the stop:** `insmod mac` failed with `No such device` (-ENODEV),
  and nothing was loaded. The station stayed up over SSH with no Oops, BUG,
  WARNING or call trace in the kernel log.

## Conclusion

R1 gives the first predeclared reading: the firmware honours NIC_POWER_CTRL
power mode 1, and WLAN_READY clears within milliseconds. The third R1 row
(the stop is contained) also holds. The second (bit 21 never clears) and
the FW-own anomaly row did not occur.

This only shows that the firmware stops on request. It does not show that
the CONN MCU stopped running WLAN code, nor that a start can follow. R2 can
now follow, and it still needs a calibration protocol.

## R2 as a module reload (2026-10-31)

The owner admitted the [calibration protocol](CALIBRATION_PROTOCOL.md) on
2026-10-31 and chose the full split: every Wi-Fi layer loadable, so a change
to any of them is tested by unloading and loading modules, not by flashing.
R2 is therefore no separate restart path. Unloading the CONSYS owner stops
the firmware and powers CONN off; loading it again is an ordinary start, the
second common init included.

**Patches:**
- [0346](../../patches/proposals/0346-wifi-mt6797-build-the-host-interface-and-firmware-lo.patch):
  the host interface, firmware loaders and snapshot helper build as one
  module, `mt6797-wlan-core`. CONSYS is the only caller of the 15 functions
  this patch exports, and nothing calls back into CONSYS.
- [0347](../../patches/proposals/0347-soc-mediatek-mt6797-consys-power-CONN-off-when-the-m.patch):
  CONSYS builds as a module, `mt6797-consys`. Its unload:
  - runs the R1 stop if the firmware is running;
  - asserts the CONN MCU reset and switches the domain off;
  - clears VCN28 hardware control and switches VCN28 and VCN18 off;
  - returns the other votes the start took (PA rails, HIF VCN33, BTIF and
    AP-DMA clocks).

  This is the order of the vendor's `mtk_wcn_consys_hw_reg_ctrl(0)`, and like
  that function it powers off even after a failed stop. The `mac` module
  holds CONSYS, so it is always detached first.
- [0348](../../patches/proposals/0348-soc-mediatek-mt6797-consys-accept-its-own-EMI-setup-.patch):
  a later start accepts the EMI state its earlier start left:
  - region 19 at its copy policy, region 18 sealed, region 23 clear, and the
    remap set. Any other state is still refused.
  - **From the vendor source:** it keeps region 19 across CONN power cycles,
    and sets region 18 open, copies and seals it again on every WLAN
    firmware download.
  - **On a kept start:** the WMT setup skips its SMC and remap write, but
    still clears and verifies the window. The EMI set reopens, refills and
    reseals region 18.
- **In the station series:** 0334 (sequence recycling, now with the export
  `mac.ko` needs) and 0335 (no packet budget for a connected lifetime), in
  canonical order. 0336-0345 were regenerated on top of them; only 0338's
  context changed.

**Tested in the VM:**
- the station profile builds with all three as modules;
- the soak profile, all built in, still builds;
- W=1 is clean on both directories;
- the station series applies to exactly the tested tree.

Not tested: any device run.

**Device test (predeclared):** station 9, `CYCLES=1 RESTARTS=3`
[`wifi-cycles.sh`](../2026-10-30-mainline-dev-station/wifi-cycles.sh).

| Observation | Reading |
|---|---|
| Each restart: `CONN power-off ... domain off=0`, `CONSYS unloaded`, then `WMT setup kept from an earlier start`, common init `completed` equal to the first, firmware ready and a scan with BSS | R2 works; any Wi-Fi layer can be reloaded on a running station |
| The unload's stop or power-off line reports an error, and the next load refuses (domain not confirmed off) | The power-off is incomplete; the refusal names the check, and the station needs a reboot |
| The kept WMT setup or the EMI set refuses | The earlier start left a state the acceptance does not name; that line names it |
| A common init step fails | Per the [calibration protocol](CALIBRATION_PROTOCOL.md): that step named, PA rails per its stop rule |
| Firmware ready, but the scan fails or times out | The start survives the restart, but the WLAN path does not; the cycle log names it |

### Station 9, boot `e0e9320c…`: the unload works, the reload crashed

- **Identity:**
  - boot2 `1bb3d739…`, built at `477b11d0`, release
    `7.1.3-gemini-a53-station`, 8 CPUs;
  - the three module checksums match the package: `mac` `01d14de5…`, core
    `1127d8d0…`, CONSYS `770f472f…`.
- **Boot:** 54 log lines match the fault patterns, all initcall names
  containing "debug", the same count as station 8.
- **First start and cycle 1:** common init `completed=285/285`, region 18
  sealed (`range=0xbfa0bfa7 policy=0x00b6da2d`), firmware ready, `mac`
  insmod 0, scan with 3 BSS, rmmod 0.
- **Restart 1, unload:** the CONSYS unload stopped and powered off cleanly.
  - The R1 stop logged `power-off status=0 sequence=17 WCIR=0x00100279`,
    FW own `WHLPCR=0`, then `VCN33-WIFI off=0 enabled=0`.
  - Then `CONN power-off: runtime put=0 domain off=0` and `CONSYS unloaded:
    WLAN stop=0, CONN off, VCN28 off, VCN18 off`.
- **The core did not unload:** `mt6797_wlan_core` showed `[permanent]`. Its
  firmware probe was registered with `builtin_platform_driver()`, which in
  a module gives an init with no exit.
- **Restart 1, reload:**
  - CONSYS bound again; the domain was confirmed off.
  - `sysfs: cannot create duplicate filename .../region19_snapshot`: the
    unload had left the probe's hand-added attributes in place.
  - The `region19_prepare` write then ran a stale attribute into the
    unloaded module's code: `SP/PC alignment exception`, an Oops in
    process context, with the PC in freed module text.
  - No CONN power was on: the reload had only bound, and the deferred start
    never ran.
- **End:** the log and `/run/station` were saved, and the station powered
  off.

**Reading.** The power-off half of R2 works, and gives a later load a
confirmed-off domain. The predeclared reload rows were not reached. Two
unload bugs, both in module code:
- [0349](../../patches/proposals/0349-wifi-mt6797-let-the-firmware-probe-unload-with-the-c.patch)
  registers the firmware probe with `module_platform_driver()`;
- [0350](../../patches/proposals/0350-soc-mediatek-mt6797-consys-remove-the-probe-attribut.patch)
  removes the probe's attributes first in the unload.

Both build W=1-clean in the station (modules) and soak (built-in) profiles.
Neither changes built-in code, so the rebuilt modules load into the
station 9 kernel: the next run copies them over `/lib/modules` and needs
no reflash.

### Station 9, boot `960b9505…`: R2 works, three restarts in one boot

- **Identity:** the same boot2 `1bb3d739…`. After boot, the core and CONSYS
  modules were replaced over SSH from the package built at `6e720e50`
  (0349 and 0350): core `abffb56a…`, CONSYS `72147b51…`, `mac` unchanged
  at `01d14de5…`.
  - That package's `Image.gz` is byte-identical to the flashed one
    (`678da35c…`), so the built-in kernel is the same.
- **Run:** `CYCLES=1 RESTARTS=3` [`wifi-cycles.sh`](../2026-10-30-mainline-dev-station/wifi-cycles.sh),
  from 129 s to 145 s of uptime.
- **First start:** common init `completed=285/285`, region 18 sealed, then
  cycle 1 with a scan of 3 BSS.
- **Each of the three restarts:**
  - **Unload:** core and CONSYS both rmmod 0. The R1 stop logged `status=0
    sequence=17 WCIR=0x00100279`, then `CONN power-off: runtime put=0 domain
    off=0` and `CONSYS unloaded: WLAN stop=0, CONN off, VCN28 off, VCN18 off`.
  - **Load:** `WMT setup kept from an earlier start`, common init
    `completed=285/285` with both rails off after, then region 18 reopened,
    refilled and sealed (`status=0`, the same range and policy).
  - **WLAN:** firmware ready, then a `mac` cycle on a new phy (`phy1`-`phy3`):
    regulatory configuration 0, a scan of 3 BSS, rmmod 0.
- **Calibration:** the four calibration events in this boot are of equal
  length, and their bytes are `same` in all four (the bytes stay private).
- **Each restart took about 4.6 s,** unload to firmware ready.
- **Kernel log:** no Oops, BUG, WARNING, call trace or refusal; the kernel
  is not tainted.

**Reading.** The first predeclared row: R2 works. Every Wi-Fi layer can now
be reloaded on a running station, so a change to the HIF, the loaders or
CONSYS is tested by replacing a module, like a `mac` change. The second
calibration matching the first, three times, was not predicted either way;
the protocol's `different` row did not occur.

**Not shown:**
- a restart while associated or carrying traffic: every restart here
  followed a scan only;
- a restart after a failed start;
- a long run of restarts.

## Follow-up

Daily-use Wi-Fi on the station, now iterated by module reload: a persistent
WPA2 join with 0334 and 0335 in place, as proposed in the dev-station
record. A `mac` change already needs no reboot; after R2
passes, neither does a HIF, loader or CONSYS change.
