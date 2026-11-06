# Experiment: both USB-C ports, what each one is and the first mainline step

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-usb-c` |
| Status | `running`: source study done; both-port support written and compile-checked (0595–0602); device tests U1–U4 not run |
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
  `vbus-supply`.
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
`usb-storage`, `sd_mod`, `scsi_mod`, `scsi_common`, `usbhid`.

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
`musb_hdrc.ko`, `mediatek.ko`, `scsi_common.ko`, `scsi_mod.ko`, `sd_mod.ko`,
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
