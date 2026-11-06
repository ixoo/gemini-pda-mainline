# Experiment: both USB-C ports, what each one is and the first mainline step

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-usb-c` |
| Status | `running`: source study done; both-port support written (0595–0604); U1 and U2 passed on boot `9207cc89`, U1 after two failures (I2C adapters deferred: fw_devlink, then the adapter's `vbus` bus-supply lookup finding the Type-C children); U3 passed (right-port host, full and high speed) after 0608 and 0620; U4 (left-port host) failed: no boost VBUS, and `sink` did not end the source state while a partner was attached |
| Subsystem | MTU3/xHCI, USB11 MUSB, T-PHY, FUSB301/FUSB301A, BQ25896 boost, SiI902x HDMI |
| Device variant | named Gemini PDA (MT6797X); Gemian `3.18.41+` evidence from earlier records |
| Date(s) | 2026-11-05 to 2026-11-06 |
| Investigator(s) | Claude (USB-C session) |
| Tracking issue | none |

## Question

For each USB-C port: which controller and PHY, what does CC detection and role
choice, who supplies VBUS in host mode, does it charge, is there PD or video, is
there firmware, and which upstream drivers fit? And what is the smallest first
mainline step?

The durable answer is the [USB-C hardware page](../../docs/hardware/usb-c.md).
This record keeps the new evidence, the readings still needed and the proposal.

## Inputs and method

No device access, boot, build or register operation. Sources:

- Gemian GPL kernel, commit `8cfe6596a503612e3332d9c26e292a19525a7f07`
  ([tree](https://github.com/gemian/gemini-linux-kernel-3.18/tree/8cfe6596a503612e3332d9c26e292a19525a7f07)),
  read from Git objects in the RE VM.
- Linux 7.1.3 as pinned in `kernel/manifest.json`, with the local series.
- Public datasheets: onsemi [FUSB301](https://www.onsemi.com/download/data-sheet/pdf/fusb301-d.pdf)
  and [FUSB301A](https://www.onsemi.com/download/data-sheet/pdf/fusb301a-d.pdf);
  TI BQ25896, SLUSC76C (May 2018).
- Planet Computers, *Gemini PDA User Guide* (2018), the public PDF at
  `https://support.planetcom.co.uk/download/GeminiPDAUserGuide.pdf`, SHA-256
  `8ea5bf459ec03f37886b4f9881711dfc44080c0aaab8c575e642206f171f7807`.
- The retained Gemian userspace image's firmware directories.
- Earlier records: [USB/Type-C recovery](../2026-07-12-usb-typec-recovery/README.md),
  [VBUS ownership](../2026-09-08-usb-vbus-ownership/README.md),
  [USB-role review](../2026-10-04-gemini-lid-microsd-usb-re/README.md),
  [charging review](../2026-10-04-gemini-charging-re/README.md),
  [kernel charge guard](../2026-11-02-gemini-kernel-charge-guard/README.md),
  [external display](../2026-07-13-external-display-recovery/README.md).

Vendor lines below are cited at the pinned commit (`G:` = the Gemian tree URL above).

## New findings

**N1. Gemian forces both Type-C controllers to Source-only.** Both
`InitializeFUSB300()` (`G:drivers/misc/mediatek/usb_c/fusb302/usb_typec.c`
line 60) and `InitializeFUSB301()` (`.../fusb301/usb_typec.c` line 55) write
`0x01` to Modes, register `0x02`. In both onsemi datasheets the Modes register (FUSB301 table 6)
has bit 0 = Source, bit 2 = Sink, reset value `0x04`, and the chip "will power
up in Sink mode". Earlier records noted the write but not its meaning.

*Inference:* under Gemian neither port presents Rd, so a Type-C source that
waits for Rd (a C-to-C charger, a Mac) gives no VBUS. Legacy A-to-C cables
still work. A private Gemian watch from 2026-09-25, with the left port reported
cabled to the Mac, stayed at `usb/online=0` and `Not charging` for five minutes.
That is consistent with N1, but the cable type was not recorded (R3 settles it).

**N2. Only the left port charges, and HDMI uses the right port.** The user
guide states both: charging is only possible through the left-side USB-C port,
and Planet's HDMI adapter must use the right-side port. The guide also says
keyboards and mice can plug into the "USB ports". That describes the Android
firmware, not Gemian.

**N3. No USB PD anywhere.** The vendor Kconfig for both selected drivers says
"Only supports CC detect, without PD" (`G:drivers/misc/mediatek/usb_c/Kconfig`
lines 22, 33). The defconfig selects neither the ANX7418 nor the SiI7033
Type-C/PD drivers, nor any TCPC option
(`G:arch/arm64/configs/aeon6797_6m_n_defconfig` lines 186–199, 273–292). The
FUSB301 has no PD engine.

**N4. Right-port video is SiI902x HDMI through a GPIO lane switch, not an
alternate mode.** `CONFIG_MTK_HDMI_SUPPORT=y` with
`CONFIG_CUSTOM_KERNEL_HDMI="sil9024"` (defconfig lines 198–199). The FUSB301A
work function (`fusb302/usb_typec.c` lines 107–167) enables the GPIO70/GPIO71
switch per CC orientation only when GPIO89 `sil9022_hpd_int` is high, and it
otherwise raises GPIO72 for "usb1 OTG mode". The Sii8348 MHL sources exist but
aren't built.

**N5. The USB11 host is set up for high speed.** `musbfsh_core.c` lines
1295–1296 set `MUSBFSH_POWER_HSENAB`, under a comment that wrongly says
"disable". The Kconfig title "fullspeed Host" describes the IP's history, not
this setting. Not observed on the unit.

**N6. The left-port controller is built SuperSpeed-capable.**
`G:drivers/misc/mediatek/mu3d/hal/mu3d_hal_hw.h` lines 27–31 define
`SUPPORT_U3` with a SuperSpeed default. Whether the connector's SuperSpeed
pairs, and an orientation mux, are fitted is unknown (R4).

**N7. Boost and watchdog.** BQ25896 REG03 `OTG_CONFIG` defaults to 0 and is
reset by the I2C watchdog (SLUSC76C, table 9); the boost also needs the OTG pin
high and no input on VBUS (pin table, §9.2.5). No GPIO for the OTG pin appears
in the vendor DT or charger code. The mainline guard kicks the watchdog only
while charging is stopped, and its `linux,no-chip-config` mode registers no
OTG regulator. So any mainline use of the boost needs the guard extended. On
the station REG03 was `0x0a` (boost off) in the guard record.

**N8. No port firmware.** No file under the retained image's
`system/vendor/firmware` or `system/etc/firmware` relates to USB, Type-C or
HDMI, and none of the USB-C, USB11, MU3D or SiI902x drivers request firmware.

Earlier facts that this record relies on but does not repeat: controller
resources and the T-PHY split (USB/Type-C recovery), the FUSB301 `-EINVAL` IRQ
and GPIO64 IRQ (same), the GPIO94/GPIO70–72 callback and the 4 V ID-pin
refusal (USB-role review U3, U5), and the unresolved GPIO94 source (VBUS
ownership record).

## Station reading, 2026-11-06

Read-only, by the device custodian, on station boot `a22a4ca8` (checked first
and last, taint 0), image built from `c546644d`, with the laptop cable on the
left port. Only I2C byte reads of FUSB301 registers `0x01`–`0x03`, `0x10`–`0x12`
(not `0x13`, which clears on read), debugfs pin state, `power-status -r`, the
UDC speed and `dmesg`. Nothing was bound at `0x25`.

| | `01` ID | `02` Modes | `03` Control | `10` Mask | `11` Status | `12` Type |
| --- | --- | --- | --- | --- | --- | --- |
| Right, I2C0 (FUSB301A) | `0x12` | `0x04` | `0x03` | `0x00` | `0x00` | `0x00` |
| Left, I2C1 (FUSB301) | `0x12` | `0x04` | `0x03` | `0x00` | `0x2f` | `0x08` |

- **Both chips are in Sink mode, their reset value, at a mainline boot.**
  Gemian's Source-only write (N1) does not carry over. The current station,
  which never writes the chips, therefore presents Rd on both ports.
- **The left chip sees the laptop as a 3 A Type-C source.** Status `0x2f`:
  attached, BC level 3 (3.0 A advertisement), VBUSOK, orientation CC2.
  Type `0x08`: a source partner. A legacy A-to-C cable advertises default
  current, so the station link is a C-to-C cable. A C-to-C link that works
  with the chip in Sink, after an earlier Gemian watch with the Mac showed
  no VBUS, supports N1's explanation. It is still not a Gemian test of the
  same cable.
- The control register reads `0x03`: interrupts masked (bit 0), default host
  current (bits 2:1 = 01).
- **Pins at handoff.** None of GPIO64, 70, 71, 72 or 94 is claimed. GPIO64 is
  in mode 1 (EINT3), input, reading 1: the FUSB301A's ID output is idle-high
  with no sink attached, and the firmware has already muxed it for EINT.
  GPIO70, 71, 72 and 94 are GPIO-mode outputs driven 0. So VBUS (94) and the
  USB data switch (72) are off, as 0602's regulators leave them. The HDMI
  lane switch enable (70) is low, which the vendor callback uses for HDMI;
  the vendor idle state is high. 0602 does not touch it.
- `power-status -r`: USB SDP input, power good, not charging, battery 4.28 V,
  VBUS 5.1 V; REG0B `0x26` (`VBUS_STAT` 001, SDP: no boost). REG03 was not
  in this dump.
- The UDC runs at high speed; MTU3 logs `dr_mode` 2 (peripheral) and the
  forced B-session; no T-PHY error.

This settles R3's cable question (C-to-C) and the carry-over question in N1.
It changes nothing in 0595–0602: the left driver starts the chip in the
mode it is already in.

## Device readings needed

None of these changes a role, VBUS or a charger register. Each goes to the
device custodian as one request. R1 and R4 need Gemian booted, which is the
custodian's and owner's call.

**R1. Does the right port host under Gemian, and is the boost on while it
does?** (decides GPIO94's source, the key unknown.) The owner plugs a USB
flash drive into the right port on running Gemian, which makes Gemian's own
driver raise GPIO94 as it always does. The custodian reads, in one SSH request with
boot-ID checks at both ends: `lsusb -t`; the `fusb300_eint_work` and USB
lines from `dmesg`; the `fusb300-eint` count from `/proc/interrupts`; and the
most recent periodic `[bq25890 reg@]` dump lines from `dmesg` (REG03 bit 5,
REG0B `VBUS_STAT`). It doesn't use `bq25890_access`. Branches:
- enumerates, REG03 bit 5 clear and `VBUS_STAT` not `111` → GPIO94 switches a
  source independent of the boost; T1 can use GPIO94 alone;
- enumerates with the boost on → the right port depends on the charger, and
  T1 must wait for an OTG decision on the guard;
- no enumeration → the right port doesn't host under Gemian; check GPIO72 and
  the USB11 PHY before any mainline attempt.

If the owner has a USB power meter, reading it on the right port with and
without the drive adds an electrical check at no extra device time.

**R2. Mainline station: none needed now.** The station's REG03 is already
recorded.

**R3. Owner questions, no device access.** Which cable does the station use on
the left port (A-to-C or C-to-C)? Does Gemian charge or show the gadget with a
C-to-C cable to the Mac or a USB-C charger? A "no" with C-to-C and "yes" with
A-to-C confirms N1.

**R4. Left-port link speed under Gemian.** With Gemian's gadget connected to the
Mac, read `/sys/class/udc/*/current_speed` on Gemian, plus the Mac's own USB
listing for the device speed. `super-speed` means the SuperSpeed pairs and an
orientation mux are fitted. Low priority: nothing in T1 depends on it.

## Proposal: first mainline step

**Host on the right port, USB 2.0 only, through USB11 MUSB.** Reasons:

- The left port is the station's only network link. Making it a host loses
  SSH. Its host power also needs the charger boost, which the guard can't hold.
- The right port's host path needs no charger write if R1 shows GPIO94 is
  independent of the boost.
- USB 2.0 needs neither the HDMI lane switch (GPIO70/71) nor the FUSB301A
  driver. GPIO72 and GPIO94 are plain GPIOs.

The proposal runs only after R1's first branch. Inputs, batched into one image:
- DT: enable the 0070 USB11 MUSB and its U2 PHY with `dr_mode = "host"`; no
  `vbus-supply`; no FUSB301A node.
- Config: MUSB core, the MediaTek glue and the T-PHY consumers for USB11 as
  `=m`, so nothing probes at boot. The left port's built-in MTU3 path stays
  unchanged.
- GPIO72 and GPIO94 stay at their boot state until the test sets them by hand
  through the GPIO character device.

### T1, written in advance, not run

*Hypothesis:* with GPIO72 and GPIO94 high, a USB 2.0 flash drive on the right
port enumerates on the USB11 root hub at high speed, and the left-port SSH link
and the charge guard are unaffected.

*Unique observation:* enumeration speed from `dmesg`/`lsusb -t`, plus REG03 and
`power-status` before, during and after.

*Preconditions:* R1 first branch; candidate built from pushed inputs; battery
above 30 %; charger on the left port allowed; owner present to plug and
unplug; a known-good USB 2.0 flash drive.

*Steps:*
1. Record identity, REG03, `power-status`, and the GPIO72/94 line states.
2. `insmod` the USB11 PHY and MUSB modules with nothing on the right port.
   Expect a USB11 root hub and no errors.
3. Set GPIO72 high, then GPIO94 high. If a meter is present, read the right port.
4. The owner plugs in the drive. Wait 10 s and record `dmesg`, `lsusb -t` and
   the drive's speed. Read one block from the drive, no writes.
5. The owner unplugs it. Set GPIO94 low, then GPIO72 low, and `rmmod` in reverse.
6. Record REG03 and `power-status` again.

*Stop at once* (GPIO94 low, GPIO72 low, owner unplugs) if: REG03 changes in any
bit but `CHG_CONFIG`/`WD_RST`; `VBUS_STAT` reads `111`; the left-port SSH link
drops; a kernel oops or MUSB/PHY error repeats; the meter shows anything but
about 5 V; the drive or connector warms.

*Decision branches:*
- enumerates at high speed → write the clean description: GPIO94 as a
  `regulator-fixed`, an ID-gated `gpio-usb-b-connector` on GPIO64 (which needs
  the FUSB301A in Source mode, through 0056), and GPIO72 as part of the board
  wiring;
- enumerates at full speed only → record it; check the USB11 PHY calibration
  (`mediatek,eye-src`) before the clean description;
- root hub but no attach → GPIO72's role, or the PHY, is wrong; stop and take
  it back to source;
- no root hub → glue or PHY probe problem; stop, no GPIO change.

Left-port host, dual role, SuperSpeed and HDMI all come after this, each with
its own record.

## Implementation: both ports in every configuration (2026-11-06)

The owner asked for both ports in any configuration, with the left port
kept as the SSH link and charging port by default. This replaces T1's
hand-driven GPIOs with the drivers' own control. T1 stays above as the
reasoning; U3 below is its replacement.

| Configuration | How | VBUS |
| --- | --- | --- |
| Left device, charging (default) | Nothing to do. MTU3's role switch starts as a device; the FUSB301 starts as a sink | from the computer or charger |
| Left host | `echo source > .../1-0025/typec/port*/port_type`, then attach a device | charger boost, only while a sink is attached |
| Left back to default | `echo sink` to the same file | off |
| Left dual-role | `echo dual` (the chip toggles with no role preference, so a laptop may end up the device) | as left host, when it is the source |
| Right host | Load the modules, attach a device | GPIO94 switch, only while a sink is attached |
| Both together | Independent; the right port never touches the charger | as above |

The patches, all proposals, in the canonical series and
`series-a53-station`:

- [0595](../../patches/proposals/0595-usb-typec-let-a-port-driver-set-the-port-type-of-a-d.patch):
  the Type-C class gets `typec_set_port_type()`, the body of the
  `port_type` store, so a driver can start a dual-role port as a sink and
  the attribute still tells the truth.
- [0596](../../patches/proposals/0596-dt-bindings-usb-fusb301-make-the-interrupt-optional-.patch):
  the FUSB301 binding: interrupt optional, either INT_N or the ID output;
  `vbus-out-supply` (renamed from `vbus-supply` after the U1 retry, below).
- [0597](../../patches/proposals/0597-usb-typec-fusb301-poll-the-status-when-there-is-no-i.patch):
  without an interrupt the driver polls every 500 ms. Also fixes remove,
  which left the devres interrupt live after the port went.
- [0598](../../patches/proposals/0598-usb-typec-fusb301-switch-VBUS-and-the-USB-role-with-.patch):
  VBUS on and host role only while the port sources an attached sink;
  device role and VBUS off otherwise.
- [0599](../../patches/proposals/0599-usb-typec-fusb301-start-a-dual-role-port-that-prefer.patch):
  a dual-role connector with `try-power-role = "sink"` starts as a sink.
  The chip has no Try.SNK, and toggling could make the laptop the device.
- [0600](../../patches/proposals/0600-dt-bindings-power-supply-bq25890-describe-the-OTG-bo.patch),
  [0601](../../patches/proposals/0601-power-supply-bq25890-let-the-guard-mode-drive-the-OT.patch):
  in guard mode the charger registers the boost regulator when the board
  has an `usb-otg-vbus` node, lets `OTG_CONFIG` through its write filter,
  and the guard kicks the watchdog while the boost is on. If the guard
  stops, the watchdog clears `OTG_CONFIG` within 40 s (N7).
- [0602](../../patches/proposals/0602-arm64-dts-mediatek-gemini-station-describe-both-USB-.patch):
  the station tree. MTU3 `dr_mode = "otg"` with a role switch defaulting to
  peripheral, USB 2.0 only on its xHCI; the left FUSB301 polled, connector
  dual-role preferring sink, VBUS from the boost; the right FUSB301A on
  EINT3 (its ID output, both edges), source only, VBUS from GPIO94 with
  GPIO72 as that regulator's supply so the data switch follows; USB11 and
  its PHY enabled.

[`gemini-a53-station-usb.fragment`](../../configs/gemini-a53-station-usb.fragment)
joins the `mt6797-a53-station-a72` profile. Built in: the USB host core,
MTU3 dual-role and the role switch class, which MTU3 needs. Modules that
nothing loads: `typec`, `fusb301`, `fixed` (regulator), `xhci-hcd`,
`xhci-mtk-hcd`, `phy-generic`, `musb_hdrc`, `mediatek` (MUSB glue),
`usb-storage`, `sd_mod`, `usbhid`. The SCSI core is built in (see `0d68c839`).

**Why the Type-C driver owns VBUS, not MTU3.** MTU3 in OTG mode enables its
`vbus` regulator during probe (`ssusb_host_setup()`), before switching to
the default device role. On the left port that would turn the boost on at
every boot with the laptop attached. The FUSB301 knows when a sink is
attached; MTU3 only follows the role it is given.

**What changes at boot.** MTU3 probes as dual-role: host IP up, then device.
The left port should reach the same gadget link; U1 checks it. Nothing else
acts until a module loads.

**Not covered.** SuperSpeed on the left port (R4); HDMI on the right port
(GPIO70/71 and the SiI902x stay untouched); USB PD (none in hardware); the
left FUSB301's `SS_SW`.

### Device tests, written in advance, not run

Each test goes to the device custodian. Candidate: the
`mt6797-a53-station-a72` profile at the pushed commit, built on Buildbox and
composed into a station image as usual. Battery above 30 %. A reading of
`power-status -r` (REG03, REG0B) opens and closes every test.

**U1. Boot: the left port is unchanged.** *Hypothesis:* with MTU3 dual-role
built in and no USB module loaded, the station boots to the same SSH link
and charges as before. *Observe:* SSH; `dmesg` for `mtu3` (`dr_mode: 3`, OTG; today's image logs 2),
`cat /sys/class/usb_role/*/role` = `device`; the guard's binding; REG03
bit 5 clear. *Branches:* as before → U2. No SSH → console shell on tty1
reads `dmesg`; the owner returns to the previous image (boot2 rewrite from
Gemian only through the reviewed path). A boost bit set → stop and record.

**U2. Left Type-C, laptop attached.** `insmod typec.ko fusb301.ko` only
(the right FUSB301A waits for its regulator). *Hypothesis:* the left port
reports `[sink]`, a partner that is a source, power role sink, data role
device, and SSH stays up. *Then:* the owner unplugs and replugs the laptop
cable once; SSH returns within 30 s. The station link is already a C-to-C
cable (station reading below), so this also covers C-to-C. *Stop:* SSH lost
for more than 60 s after a replug → owner reboots (the modules don't load at
boot).

**U3. Right port host.** `insmod fixed.ko`, then `phy-generic.ko`,
`musb_hdrc.ko`, `mediatek.ko`, `sd_mod.ko`,
`usb-storage.ko`, `usbhid.ko`. *Hypothesis:* the FUSB301A binds as a
source; a USB 2.0 flash drive on the right port raises the EINT3 count,
registers a sink partner, enables `usb1-vbus`, and enumerates on the USB11
root hub at high speed; unplugging it disables the regulator. *Observe:*
`dmesg`, `/sys/class/regulator/*/state` for `usb1-vbus` and
`usb1-data-switch`, `lsusb`-equivalent sysfs listing, the drive's speed,
one block read (no writes). Optional: a USB meter on the right port.
*Branches:* enumerates → right port done; also try a keyboard. No power on
the drive with the regulator on → GPIO94 does not switch a live source
alone; the boost is the next candidate (vin-supply to `usb0_vbus`), which
needs its own test. Power but no enumeration → GPIO72 or the USB11 PHY.
*Stop:* REG03 bit 5 set, `VBUS_STAT` = `111`, SSH lost, a repeating MUSB or
PHY error, or a hot drive: `rmmod fusb301` (turns VBUS off), owner unplugs.

**U4. Left port host.** Needs the owner at the device; SSH drops while the
laptop is unplugged. `insmod xhci-hcd.ko xhci-mtk-hcd.ko` (and U3's class
modules), then over SSH start a bounded switch that returns by itself:
`p=$(echo /sys/bus/i2c/devices/1-0025/typec/port*/port_type); (echo source > $p; sleep 180; echo sink > $p) &`,
logging `dmesg` and `power-status -r` every 10 s to `/mnt/data`. The owner
then swaps the laptop cable for a flash drive (C plug, or a C-to-A OTG
adapter), waits 60 s, removes it and reconnects the laptop after the 180 s.
*Hypothesis:* REG03 bit 5 set and `VBUS_STAT` = `111` only while the drive
is attached; the drive enumerates on the xHCI root hub; the guard's
watchdog kicks continue; after `sink` the laptop link returns. *Stop:* the
port stays in source after 180 s → the owner uses the console: `echo sink`
to the same file, or reboots. Any charger fault bit → stop.

**U1 candidate (staged 2026-11-06, not booted).** Built by the custodian on
Buildbox from `0d68c839`, profile `mt6797-a53-station-a72`: package
inventory `b9111a2e…` with SHA256SUMS passing, config `6225c1a1…`. Station
image `station-work-59`: boot2 `30ba7ad9…`, DTB `5c75c57d…`, with the parent
RAM root and tools of `station-work-58`. The custodian checked the resolved
config and the DT: MTU3 `otg` with its role switch, both FUSB301 nodes, the
boost child, and the GPIO72/GPIO94 regulators with no boot-on. The defconfig
also builds the `hd3ss3220`, `tipd`, `tcpm` and altmode Type-C modules;
nothing loads them. The first config, from `59fed0bc`, failed Buildbox's
retention check on `PHY_MTK_UFS`, which SCSI brought back. `0d68c839` fixes
that and four more lines found by running the same check in the VM.

**U1 result, boot `c85e7cb8` (station-work-59): failed on a stop condition.**
Run by the custodian; evidence kept privately under
`artifacts/station-work-59/boot-1/`.
- *Held:* SSH came up. MTU3 logged `dr_mode: 3, drd: auto`, the forced
  B-session and xHCI platform registration; the gadget linked at high
  speed. The role switch read `device`. No USB module was loaded.
- *Failed:* the station's check reported the charge guard missing. I2C0
  (`11007000`) and I2C1 (`11008000`) both deferred about 25 times and were
  left "deferred probe pending", so the charger and everything else on those
  buses never bound. The battery read `Discharging` at 91 % with the cable
  in. The custodian restored station-work-58 to boot2, verified the
  readback, and powered off.
- *Cause:* until a client's driver binds, fw_devlink counts the client's
  suppliers against its parent. On I2C0, the FUSB301A's `vbus-supply` is the
  GPIO94 regulator, whose driver is a module nothing loads; devlink showed
  `11007000.i2c` waiting on `regulator-usb1-vbus`. On I2C1, the FUSB301's
  `vbus-supply` is the charger's boost on I2C0, so I2C1 waited on I2C0.
- *Also:* the USB11 T-PHY failed with `-EBUSY`. Its shared window
  `0x11210000`+`0x1000` (from 0070) covered its own U2 port at
  `0x11210800`. This is harmless at boot, but the right port could not have
  worked.
- *Not read:* pins 72 and 94 (no pinctrl debugfs on this boot).

**Fixes, compile- and DT-checked in the VM, not run:**
- [0603](../../patches/proposals/0603-arm64-dts-mediatek-gemini-station-do-not-hold-the-I2.patch):
  both Type-C nodes list their VBUS regulator in `post-init-providers`,
  which makes fw_devlink ignore that supplier for probe ordering. The driver
  still waits for VBUS itself. `CHECK_DTBS` now warns that the FUSB301
  binding does not list `post-init-providers`; this is a schema warning
  only.
- [0604](../../patches/proposals/0604-arm64-dts-mediatek-mt6797-end-the-USB11-T-PHY-s-shar.patch):
  the USB11 T-PHY's shared window ends at `0x800`, as the SSUSB T-PHY's does.

**U1 retry, boot `039510b0` (station-work-60, from `10ad23f3`): failed on
the same stop.** Evidence is kept privately under
`artifacts/station-work-60/boot-1/`.
- 0603 removed the devlinks to `regulator-usb1-vbus`; all links left on the
  adapters were `available`.
- 0604 worked: `11210000.t-phy` probed with no `-EBUSY`.
- SSH, MTU3 `dr_mode: 3`, role `device`, no USB modules, and GPIO72/94 as
  outputs at 0 held as before.
- Both adapters still deferred, with an empty reason. The custodian pointed
  out that `really_probe` printed a positive 517, which means the driver's
  own probe returned `-EPROBE_DEFER`; the devlink check prints -517.

*Cause:* `mtk_i2c_probe()` takes an optional bus supply with
`devm_regulator_get_optional(dev, "vbus")` (`i2c-mt65xx.c` line 3396). When
the adapter's node has no `vbus-supply`, `of_get_regulator()` searches the
adapter's child nodes for one (`of_get_child_regulator()`,
`of_regulator.c` lines 582–633). It found each FUSB301's `vbus-supply`,
whose regulator was not registered, so the adapter deferred. Had the
regulator existed, the adapter would have taken it as its own bus supply,
and on I2C1 that is the charger's boost, enabled with the bus.

*Fix:* the FUSB301 supply is now `vbus-out-supply` in the binding (0596),
the driver (0598) and the station tree (0602, 0603). 0603's
`post-init-providers` stays, for the fw_devlink half. In the rebuilt
station DTB neither adapter's subtree has a `vbus-supply` property. The
fusb301 object builds clean at `W=1`, and checkpatch is clean on
0595–0604. Not run.

**U1 passed, boot `9207cc89` (station-work-61, boot2 `ef50ae38…`, built
from `ce1b4541`, live DTB `9e0dc067…`), taint 0.** Run by the custodian;
evidence kept privately under `artifacts/station-work-61/boot-1/`. The
station stays on this image.
- I2C0 and I2C1 probe (I2C6 defers once as usual), and `devices_deferred`
  is empty. `0-006b` binds to the charger. The guard runs ("charging
  stopped: … capacity=98 limit=80 full"), and the missing-guard line is gone.
  `1-0048` and `1-0069` are unbound as before: their drivers are modules
  nothing loads. `0-0025` and `1-0025` exist and are unbound.
- Both T-PHYs probe, `11210000.t-phy` included.
- MTU3 logs `dr_mode: 3, drd: auto`, the forced B-session and the xHCI
  platform device. The role reads `device`, and the UDC is high-speed and
  configured, with SSH over the left port.
- `power-status -r`: USB SDP, power good, VBUS 5.1 V, not charging (the
  guard's 80 % limit, at 98 %), battery 25.2 °C; REG0B `0x26`. REG03 is
  `0x0a` from the regmap debugfs, so `OTG_CONFIG` is clear. `usb0-vbus` is
  disabled with no users.
- No USB, Type-C, regulator or storage module is loaded. GPIO72 and GPIO94
  are outputs at 0, GPIO70/71 outputs at 0, and GPIO64 is in EINT mode.
- The only new log line is the expected "Fixed dependency cycle(s)" between
  the left connector and MTU3.

So the dual-role build boots to the same left-port device and charging
behaviour, with nothing driving the ports.

**U2 passed, same boot `9207cc89`, taint 0.** The owner approved it in the
custodian's session. The custodian loaded `typec.ko` and `fusb301.ko` from
the `ce1b4541` package; the station's RAM root does not carry them.
Evidence is kept privately under `artifacts/station-work-61/boot-1/`.
- The left chip probed with "no interrupt, polling the status". Its port
  reads `port_type` `dual source [sink]`, power role sink, data role device,
  preferred role sink, 3.0 A operation mode, orientation reverse, and a
  partner with no PD. So 0599's sink start and the class helper (0595)
  report what the chip does.
- The right chip deferred with "failed to get VBUS", as expected without
  `fixed.ko`.
- Throughout, REG03 stayed `0x0a` (`OTG_CONFIG` clear), REG0B `0x26` and
  REG0C `0x00`. `usb0-vbus` stayed disabled with no users. The guard held
  its 80 % stop, and the role stayed `device` with the UDC configured at high
  speed.
- The owner unplugged the laptop cable, waited about 5 s, and replugged it.
  The laptop's ping watcher lost the link for about 4 s (the limit was 30 s),
  and the port read the same afterwards.
- *Limit:* the driver logs nothing on attach or detach, so this boot does
  not show that the poll saw the detach. A typec uevent monitor during U3
  or U4 would.

The two modules stay loaded; that is harmless, since the left port is in its
default.

**U3 stopped before a drive was attached, same boot `9207cc89`.** The owner
was ready. Evidence is kept privately under `artifacts/station-work-61/boot-1/`.
- `fixed.ko` loaded. Both GPIO regulators probed, and `0-0025` bound
  `fusb301` as a source/host port. All three VBUS-side regulators stayed
  disabled with no users, GPIO72 and GPIO94 stayed output 0, and REG03 stayed
  `0x0a`.
- The MUSB glue bound `11200000.usb`, but `musb-hdrc` failed: "DMA
  controller not set", then `musb_init_controller` `-ENODEV`. With neither
  `MUSB_PIO_ONLY` nor an Inventra DMA option set, `musb_core` refuses a glue
  without DMA operations. No USB bus appeared, VBUS was never enabled, and
  the left port was unaffected.
- The custodian's uevent log showed the polled left port sending a typec
  `change` event every 0.5 s with nothing changing: `typec_set_orientation()`
  notifies on every call.

*Fixes, VM-built, not run:* the fragment selects `MUSB_PIO_ONLY` (DMA stays
a later step, as the USB11 study set out), and
[0605](../../patches/proposals/0605-usb-typec-fusb301-update-the-port-only-when-the-chip.patch)
updates the class only when the status or type register changes. Both are
module-only: the station kernel has no module signing or modversions, and
the rebuilt modules carry its vermagic. So U3 can retry on the running
station with `musb_hdrc.ko`, `mediatek.ko` and `fusb301.ko` from a package
of the new commit, after `rmmod` of the old ones.

**U3 module swap stopped: `rmmod mediatek` oopsed, same boot `9207cc89`, now
tainted D.** The new modules came from a package of `799bc8c4`, with
vermagic matching. `rmmod mediatek` hit a NULL dereference in
`usb_put_phy()` from `devm_usb_phy_release()` during driver detach.
`mediatek` and `musb_hdrc` cannot be unloaded until a reboot. The new
`fusb301` loaded. It now binds the right chip first, so the right port is
`port0`, and 0605 worked: no `change` events after the bind. Throughout,
REG03 was `0x0a` and REG0C `0x00`, all three USB regulators were off,
GPIO72/94 were low, the left port stayed the SSH device, and the guard ran.
Evidence is kept privately under `artifacts/station-work-61/boot-1/`.

*Cause:* an ordering bug in the upstream MediaTek MUSB glue, not in this
board's changes. `mtk_musb_probe()` takes the generic PHY with
`devm_usb_get_phy()`, and `mtk_musb_remove()` (like the probe error paths)
unregisters the generic PHY device by hand. Unbinding that device frees the
`usb_phy`, and devres then puts it from freed memory.
[0607](../../patches/proposals/0607-usb-musb-mediatek-drop-the-transceiver-before-its-de.patch)
takes it with `usb_get_phy()` and puts it before the unregister. It builds
clean at `W=1`; not run.

*Next:* a fresh boot is needed. The custodian proposes batching it with the
microSD T3 image. U3 then loads the modules fresh; with 0607 in the image,
unloading `mediatek` is safe too, but the only unload in the stop path
remains `rmmod fusb301`.

**U3 on boot `2dc6de9f` (station-work-62, from `15bde8ff`), taint 0: the
port's power side worked, nothing enumerated.** Stopped with
`rmmod fusb301`. Evidence is kept privately under
`artifacts/station-work-62/boot-1/`.
- All nine modules loaded fresh. MUSB registered USB bus 1, a 480 Mb/s root
  hub with one port. Once, at start, before any VBUS was on, it logged
  "VBUS_ERROR in a_idle (80, <SessEnd)". 0605 held: three typec events from
  load to attach.
- The owner inserted a USB 2.0 flash drive. EINT3 counted one, a sink
  partner registered with orientation normal, `usb1-data-switch` and
  `usb1-vbus` were enabled, and GPIO72/GPIO94 read output 1. REG03 stayed
  `0x0a`, so the boost was off and VBUS came from GPIO94's path alone, if
  at all.
- Nothing enumerated in about 50 s. MUSB stayed `a_idle` with no further
  interrupt, and the root port reported no connect. The owner saw no LED,
  but whether the drive has one is unknown, so drive power is unproven.
- `rmmod fusb301` turned both regulators off and returned GPIO72/94 to 0.
  The left port and the guard were unaffected throughout.

*Reading:* `<SessEnd` in `a_idle` is the controller's view from the PHY's
VBUS and session comparators. In `a_idle` MUSB does not retry; it drops the
session and waits. GPIO94 switches the port's VBUS outside the PHY, so the
controller never learns that VBUS came up. The vendor USB11 driver forces
those signals at power-on (`mt65xx_usb11_phy_poweron_common()`: `0x6C`
gets VBUSVALID, BVALID and AVALID set and SESSEND cleared, `0x6D |= 0x3C`
forces all four) and forces IDDIG low.

*Fix:*
[0608](../../patches/proposals/0608-arm64-dts-mediatek-gemini-station-force-the-USB11-PH.patch)
gives the USB11 PHY port 0077's `mediatek,force-b-session-valid`. That
forces the same four signals, and IDDIG. The MUSB glue then sets host mode
after power-on, which clears IDDIG. DT only, so it needs a new image. In the
rebuilt DTB both PHY ports carry the property. Not run.

*What the next U3 shows:* the session and connect, if VBUS reaches the
drive. If MUSB now sits in `a_wait_bcon` and still sees no connect, the
drive is unpowered or GPIO72's switch is not the data path; a meter on the
right port then splits the two (GPIO94 alone versus the boost).

**U3 on boot `294ae5a1` (station-work-64, from `6488e6f8` with 0608), taint
0: session and connect work, enumeration fails with `-71`.** Stopped with
`rmmod fusb301` under the repeating-error rule. Evidence is kept privately
under `artifacts/station-work-64/boot-1/`.
- The PHY logged the forced session at load, there was no VBUS error, and
  MUSB waited in `a_idle` with no interrupts. 0608 works.
- On attach of the same drive: a sink partner, both regulators on, GPIO72
  and GPIO94 high. MUSB saw a high-speed device ("new high-speed USB device …
  using musb-hdrc"), so VBUS reaches the drive and GPIO72 carries D+/D-.
  This settles the power question: GPIO94's path powers the port without
  the boost, and REG03 stayed `0x0a`.
- Every first control transfer failed: four "device descriptor read/all,
  error -71" lines across eight addresses and two hub power-cycle attempts.
  MUSB went to `a_suspend`. The FUSB301A logged one partner remove and add
  about 4 s after the first power cycle, and the owner had not reseated the
  drive. Whether the root-hub power cycle caused that detach is open.
- After the stop: all regulators off, GPIO72/94 at 0, MUSB in
  `a_wait_bcon`, REG03 unchanged, the left port unaffected.

*Reading:* `-EPROTO` on `GET_DESCRIPTOR` after a high-speed chirp points at
high-speed signalling: the USB11 PHY's HS tuning (the vendor programs it
beyond the generic V1 T-PHY's defaults), the analogue switch on GPIO72, or
PIO timing. A low- or full-speed device separates high-speed signalling
from everything else, with no rebuild: MUSB cannot be capped at full speed
from DT, because the MediaTek glue does not pass `maximum-speed` to its
config.

**U3 keyboard split, same boot `294ae5a1`.** A USB-C keyboard plugged
straight into the right port: the FUSB301A registered a sink partner
(orientation normal), GPIO64 went low, EINT3 counted one, and both
regulators and GPIO72/GPIO94 went high. The owner saw the keyboard light,
so it had VBUS. MUSB stayed in `a_wait_bcon` for about 50 s with no
interrupt and no connect. The flash drive had been a USB-A drive through a
C-to-A adapter. Evidence is kept privately under
`artifacts/station-work-64/boot-1/`.

*Reading:* a host sees a connect as a pull-up on D+ (full or high speed) or
on D- (low speed). The drive's D+ pull-up was seen, but its high-speed
transfers failed. The keyboard, if low speed, pulls up D-, and nothing was
seen. One broken D- path explains both results. Candidates:
- GPIO70. The vendor kernel's USB host state ("usb1 OTG mode") leaves
  GPIO70 high, the lane switch disabled. At a mainline handoff the firmware
  leaves it low, which is the vendor's HDMI state. If that switch also
  touches D+/D-, it would load or divert them. 0602 does not drive GPIO70.
- Orientation. Both attaches were `normal`, so orientation does not tell
  the two devices apart. Still, a receptacle whose second D+/D- pair
  (B6/B7) is not joined to the first would fail one plug orientation.

The keyboard's speed class is not yet known.

The station has no GPIO tools, so GPIO70 cannot be tried by hand.
[0610](../../patches/proposals/0610-arm64-dts-mediatek-gemini-station-turn-the-right-por.patch)
adds it to the right port's chain for the next image: GPIO70 high (lane
switch off), then GPIO72, then GPIO94, while a sink is attached. That
matches the vendor's USB host state. At rest it stays low, as the firmware
leaves it. The DTB builds; not run.

**Second keyboard, same boot `294ae5a1`.** The owner attached another USB
keyboard (C-native or adapter not recorded) before `fusb301` loaded. It was
seen as a full-speed device on the USB11 root port, and every first control
transfer failed with `-71`, the same pattern as the drive: two error lines,
a hub power cycle, two more addresses. Orientation was `reverse`; the first
keyboard's was `normal`. GPIO70 stayed low and GPIO72/94 went high. The stop
returned all three pins to 0 and REG03 stayed `0x0a`. Evidence is kept
privately under `artifacts/station-work-64/boot-1/`.

So the failure is not specific to high speed or to one orientation. A D+
pull-up is seen, and differential signalling then fails at both 12 and
480 Mb/s. That fits a loaded or broken D- path. 0610 is the next test. If
it changes nothing, the next suspects are the USB11 PHY's analogue setup
(the vendor's power-on writes beyond the generic V1 T-PHY's) and the GPIO72
switch itself.

**U3 with 0610, boot `377bbcde` (station-work-65, from `54986910`), taint
0: no change.** With a full-speed keyboard attached at load, all three
right-port pins went high (GPIO70 included, as 0610 intends). The device
was seen at full speed and every first control transfer failed with `-71`,
as before. Stopped with `rmmod fusb301`; all regulators and pins returned
to off and REG03 stayed `0x0a`. Evidence is kept privately under
`artifacts/station-work-65/boot-1/`. So GPIO70 is not the cause; 0610 stays,
because it matches the vendor's host state.

*Where this leaves it:* `-EPROTO` on EP0 in MUSB host is a missing response
after retries. The host sees the device's pull-up but no transaction
completes at either speed. Remaining suspects:
- the USB11 PHY's analogue and clock setup against the vendor's;
- the PHY reference clock. 0078 replaced `CLK_INFRA_SSUSB_REF` with
  `clk26m` for the SSUSB port, on another tree's evidence; the USB11 port
  still uses `CLK_INFRA_SSUSB_REF`;
- the GPIO72 switch path.

The vendor exposes read-only debugfs dumps (`musbfsh/regdump`,
`musbfsh/regdumpphy`). A Gemian reading with a working keyboard in the
right port would show whether the board path works and give the PHY values
to compare.

**Gemian reading, boot `f0229646` (`3.18.41+`): the board path works.** The
same full-speed keyboard that failed under mainline enumerated on the
vendor's USB11 controller (`musbfsh`) at 12 Mb/s and became an input
device. Raw dumps, before and after the attach, are kept privately under
`artifacts/gemian-usbc-r2/`; the device's identity stays private. From the
vendor's own debugfs dumps:
- the port reset runs MUSB POWER `0x68` → `0x60` → `0x68`, so HSENAB stays
  set for a full-speed device;
- the PHY's U2PHYDTM1 is `0x3e2c`: VBUSVALID, BVALID and AVALID set,
  SESSEND and IDDIG clear, all five forced. That is the state 0608 gives;
- USBPHYACR6 is `0x00100488`, with SQTH 8 and DISCTH 8. Mainline's T-PHY
  writes SQTH 2;
- the other PHY words are USBPHYACR0 `0x00013c6e`, ACR1 `0x44a44400`,
  ACR5 `0x00804000`, U2PHYACR3 `0xc0040000`, U2PHYACR4 `0x1a`, U2PHYDCR0
  `0x402`, U2PHYDTM0 `0x02000000`, REGFCOM `0x2800`;
- MUSB ConfigData is `0xaa`, and HS/FS/LS_EOF1 are `0x80`/`0x77`/`0x72`.

So the fault is in mainline's USB11 setup, not the board. To diff it,
[0616](../../patches/proposals/0616-phy-mediatek-DIAGNOSTIC-dump-the-MT6797-USB11-PHY-re.patch)
adds a read-only diagnostic module. It prints the same PHY registers and
MUSB's index-free byte registers once (it never reads the read-to-clear
interrupt registers), then refuses to stay loaded. It is built as a module
in the station fragment and loads into the running kernel.

**Mainline dump, boot `28a5901c` (station-work-67), taint 0.** The custodian
loaded 0616 with the U3 modules in place, once idle and once after the
full-speed keyboard had failed. Evidence is kept privately under
`artifacts/station-work-67/boot-1/`. Against Gemian's working dump:
- **PHY:** every control register matches except USBPHYACR6: Gemian
  `0x00100488`, mainline `0x00100482`. Bits 3:0 are the U2 squelch threshold:
  the hardware default 8, which the vendor never writes, against the 2 that
  `u2_phy_instance_init()` writes to every port. DTM1 is `0x3e2c` on both.
  Only the monitor registers differ otherwise.
- **MAC:** POWER is `0x60` on Gemian and `0xe0`/`0xe2` on mainline. Upstream
  `musb_start()` sets ISOUPDATE (bit 7) on every platform, and bit 1 is
  suspend after the failures. The EOF timings, LinkInfo, VPLen and MISC
  match.

*Fix, built in, so a new image:*
[0617](../../patches/proposals/0617-dt-bindings-phy-mediatek-tphy-add-the-U2-squelch-thr.patch)
and
[0618](../../patches/proposals/0618-phy-mediatek-tphy-let-a-U2-port-name-its-squelch-thr.patch)
let a U2 port name its squelch threshold with `mediatek,rx-sqth`, keeping
2 without it. The property is parsed in `xlate`, before `phy_init`.
[0619](../../patches/proposals/0619-arm64-dts-mediatek-gemini-station-give-the-USB11-PHY.patch)
sets 8 on the USB11 port only; the left port keeps 2. VM checks: the T-PHY
builds clean at `W=1`, the binding validates, the DTB carries the property
on that one port, and checkpatch is clean. Not run. If 8 does not fix it,
ISOUPDATE is the remaining MAC difference, and a module-only test.

**U3 with 0617–0619, boot `4e6851f2` (station-work-68, from `84a70e42`),
taint 0: no change.** The left port was unchanged. The 0616 dump read
USBPHYACR6 `0x00100488`, so every PHY control register now equals Gemian's.
The full-speed keyboard still failed every first control transfer with
`-71`. Stopped with `rmmod fusb301`. Evidence is kept privately under
`artifacts/station-work-68/boot-1/`. 0617–0619 stay: they match the vendor
setting.

*Cause found in the controller configuration.* The vendor core sets
`is_multipoint = 1` unconditionally (`musbfsh_core.c` line 1262), despite
`.multipoint = false` in its config. It addresses each target through the
per-endpoint function address registers at `0x480`, which is what the
MediaTek glue's `busctl_offset` uses for the other MediaTek MUSBs. 0069
copied `.multipoint = false` for the USB11 data. So mainline ran the
controller as a plain HDRC: it wrote FADDR, programmed no target speed in
TYPE0, and printed "kernel must disable external hubs" at every load.
That fails transfers at any speed while the connect, which needs neither,
is still seen.
[0620](../../patches/proposals/0620-usb-musb-mediatek-run-the-MT6797-USB11-controller-as.patch)
sets multipoint for the USB11 data. It is module-only (`mediatek.ko`), and
with 0607 the swap no longer oopses. Built clean at `W=1`; not run.

### Gemian against mainline: the USB11 host path (2026-11-06)

The owner asked for a full comparison before more guesses. Sources: Gemian
GPL `drivers/misc/mediatek/usb11/` (`musbfsh_mt65xx.c`, `musbfsh_core.c`,
`musbfsh_host.c`, `musbfsh_regs.h`, `musbfsh_core.h`) at the pinned commit,
against Linux 7.1.3's `musb/mediatek.c`, `musb_core.c`, `musb_host.c` and
`phy-mtk-tphy.c` with the local series. The vendor build has
`CONFIG_MTK_ICUSB_SUPPORT` and `MTK_DT_USB_SUPPORT` off, so only the
plain-host paths apply. Binary RE was not needed: the source accounts for
what the dumps show.

What matches:
- PHY: the vendor's power-on, recover and save-current sequences write only
  inside the dumped bank and the frequency meter at `+0xf00`. The dumps
  agree on every control word, after 0608 and 0619.
- Clocks are the same two gates (`infra_icusb`, `sssub_ref_clk`).
- Interrupt enables: `INTRUSBE` `0xf7`, L1 mask `0x0f`. EOF timings, FIFO
  layout (five TX/RX pairs of 512 bytes), RAM bits 11, and the target
  address registers at `0x480 + 8 * ep`.
- BC1.2 is off and the UART is not forced; both show in the dumps.

Differences that can explain a seen connect followed by `-EPROTO` on every
first control transfer, ranked:
1. **Endpoint register model.** The vendor reaches endpoint registers only
   through the indexed window at `0x10`, selected by `INDEX`
   (`MUSBFSH_EP_OFFSET` = `MUSBFSH_INDEXED_OFFSET`, `musbfsh_core.h` line
   115). The MediaTek glue sets no `MUSB_INDEXED_EP`, so mainline's core
   drives CSR0, TYPE0 and NAKLIMIT0 through the flat window at `0x100`. If
   that window is absent on this older block, no transfer is ever started
   correctly, at any speed, while the connect (DEVCTL and POWER) works.
   Fix:
   0621 (withdrawn).
   Module-only.
2. **Multipoint.** The vendor forces `is_multipoint = 1`; mainline ran it
   as a plain HDRC, writing FADDR and no TYPE0 speed. Fix: 0620.
   Module-only.
3. **PHY byte `0x72`.** At power-on the vendor writes its low nibble to 9
   (`musbfsh_mt65xx.c` lines 1088–1089). Gemian reads `0x00091000` in that
   word and mainline `0x000a1000`, so it is a setting, not just a monitor.
   Mainline's T-PHY does not name the field. A test needs a built-in T-PHY
   change or a reviewed one-byte write.
4. **MUSB POWER.** Vendor `HSENAB | SOFTCONN | ENSUSPEND` (`0x61`);
   mainline `ISOUPDATE | HSENAB | SOFTCONN` (`0xe0`). ISOUPDATE affects
   only isochronous transfers. Low.

Cheapest test, all module-only on a running station: first load the
extended dump
(0622 (withdrawn)),
which prints Frame, INDEX and endpoint 0 in both windows with the current
driver. Then swap in `mediatek.ko` with 0620 and 0621 and attach the
keyboard. If both windows read alike, 1 is not the cause and the swap
tests 2 alone.

**U3 passed with 0620 alone, boot `4e6851f2` (station-work-68), taint 0.**
Run by the custodian on the live boot, swapping only `mediatek.ko` (0620,
from the `77f90783` package). Evidence is kept privately under
`artifacts/station-work-68/boot-1/`; device models are not recorded.
- `rmmod mediatek` worked with no oops, so 0607 holds. The reload left an
  "Unbalanced pm_runtime_enable" and five T-PHY debugfs "already exists"
  lines. Cleanup is pending.
- The "kernel must disable external hubs" line was gone.
- The full-speed keyboard enumerated on the USB11 root port (`a_host`, 12
  Mb/s) and became an input device. A key press and release arrived on its
  event node.
- The high-speed card reader, through its C-to-A adapter, enumerated at 480
  Mb/s as a SCSI disk. A raw 64 MiB read took 9.47 s (6.8 MiB/s, as
  expected for PIO), and two 16 MiB reads hashed the same. There were no
  errors or resets after the attach.
- Throughout: REG03 `0x0a`, REG0C `0x00`, `usb0-vbus` off, and the three
  right-port regulators on. `rmmod fusb301` turned them all off and returned
  the pins to 0. The block device was still listed right after VBUS was cut;
  detach handling is to be checked.

So multipoint was the cause: the controller needs its per-endpoint target
address and speed registers. 0621 (indexed endpoint access) and its
diagnostic companion 0622 were never needed. They are withdrawn from the
series, unbooted. PHY byte `0x72` is not needed either. 0610 (GPIO70) and
0619 (squelch 8) stay: they were in the passing image and match the vendor.

Open on the right port: Inventra DMA (PIO only now), the reload leftovers,
detach after VBUS is cut, and loading the modules at boot. Add to
the observations that I2C0 and I2C1 bind with their clients (`0-006b`,
`1-0048`, `1-0069`), and that `11210000.t-phy` probes.

### U4 result: left-port host failed (2026-11-06)

Run by the custodian with the owner at the device, on boot `4e6851f2`
(`station-work-68`, from `84a70e42`, with the 0620 `mediatek.ko` loaded live;
taint 0 throughout). Samples every 5 s and the kernel log are kept privately.

- `insmod fusb301`: the left port came up `dual [sink]`, partner the laptop.
  A detached script then loaded `xhci-hcd` and `xhci-mtk-hcd` (both returned
  0; bus 2 registered with "USB0 root hub has no ports", hub `2-0:1.0`
  present), wrote `source` to the left port's `port_type`, waited 180 s,
  wrote `sink`, waited up to 60 s for the gadget and unloaded xHCI.
- **No VBUS from the boost; the drive never enumerated.** From t+15 s, with
  the drive's adapter attached, the port reported power role source, data
  role host and USB role host; `usb0-vbus` was enabled and REG03 went
  `0x0a` → `0x2a` (`OTG_CONFIG` set). REG0B stayed `0x02` (`VBUS_STAT` `000`,
  not `111`) for the whole run. At the end `power-status` read VBUS 2.6 V
  with the boost still enabled and the partner still attached. No device
  appeared on bus 2. The partner went away at t+85..90 s (USB role device,
  boost off) and came back at t+95 s, probably the drive being moved.
- **`sink` did not end the source state.** At t+180 s `port_type` read
  `[sink]`, but the power role stayed source, the data role host, the USB
  role host, the partner stayed, `usb0-vbus` stayed enabled and REG03 stayed
  `0x2a`, through the +60 s and post-`rmmod` samples. The gadget did not
  return and SSH stayed down until the owner unplugged and replugged the
  cable; then the port was sink and device, the gadget configured and REG03
  was `0x0a` again. This is U4's "stays in source" stop condition, resolved
  by the replug.
- No charger fault in the kernel log; REG0C was not read. Afterwards the
  station was back at its starting state: `fusb301` and xHCI unloaded, all
  USB regulators off, REG03 `0x0a`, SSH on the left port.

Inference, not tested:

- `OTG_CONFIG` alone does not start the boost. N7 lists the other
  conditions: the chip's OTG pin high and no input on VBUS. The OTG pin's
  wiring is unknown and the vendor sources drive no GPIO for it, so the next
  step is to find what Gemian does when it powers a left-port device, not
  another mainline attempt.
- The `sink` write reaches the chip, and `fusb301_set_port_type()` turns host
  off at once, but the FUSB301 appears to keep reporting the attached sink:
  0605 clears the cached status on a port-type change, so the next poll sees
  the same attach and turns host and VBUS back on. A fix should make a sink
  `port_type` refuse a sink partner (or force a detach) rather than wait for
  the next physical detach.

U5 (later, not prepared): both ports at once; a C-to-C charger on the left
port in the default; repeated attach cycles.

## Validation

Source study (2026-11-05): documentation only, `./scripts/check-repository`.

Implementation (2026-11-06), compile-only in the dev VM (owner-allowed for
iteration; any booted image comes from Buildbox): the full
`series-a53-station` tree, defconfig plus the `mt6797-a53-station-a72`
fragments and the USB fragment.

- Every fragment line lands in the resolved `.config` as written.
- `Image`, `modules` and `dtbs` build. The thirteen modules above exist
  under the names given. `fusb301.o`, `class.o` and
  `bq25890_charger.o` are clean at `W=1`. The first build caught a
  use-before-definition in 0598, fixed before export.
- `checkpatch --strict` is clean on 0595–0602.
- `dt-doc-validate` and `yamllint` pass on both changed bindings.
- `CHECK_DTBS` on `mt6797-gemini-pda-station-a72.dtb` reports nothing on
  the USB, Type-C, regulator or charger nodes. The 114 lines it prints are
  for SPI, display, panel and audio-pin nodes; the `ranges_format` warning
  on `usb@11271000` comes from 0068.
- `validate-manifest-series` passes; `check-repository` before push.

Not run: a Buildbox build, any boot, U1–U4.
