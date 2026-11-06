# Experiment: both USB-C ports, what each one is and the first mainline step

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-usb-c` |
| Status | `completed` for the source study; device readings R1–R4 open; first step T1 proposed, not run |
| Subsystem | MTU3/xHCI, USB11 MUSB, T-PHY, FUSB301/FUSB301A, BQ25896 boost, SiI902x HDMI |
| Device variant | named Gemini PDA (MT6797X); Gemian `3.18.41+` evidence from earlier records |
| Date(s) | 2026-11-05 |
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

## Validation

Documentation only: `./scripts/check-repository`. No kernel build, DT check
or device action.
