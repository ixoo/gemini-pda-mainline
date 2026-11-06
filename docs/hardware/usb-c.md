# Gemini USB-C ports

Scope: both USB-C connectors on the Gemini PDA, their controllers, PHYs, Type-C
logic, VBUS sources, charging, video and the upstream drivers that could cover
them. Each fact is labelled **observed** (seen on the device), **source** (Gemian
GPL kernel, public datasheet or public user guide) or **inference**. Evidence
and chronology are in the
[2026-11-05 USB-C record](../../experiments/2026-11-05-gemini-usb-c/README.md),
which builds on the [USB/Type-C recovery](../../experiments/2026-07-12-usb-typec-recovery/README.md),
the [VBUS ownership record](../../experiments/2026-09-08-usb-vbus-ownership/README.md)
and the [USB-role review](../../experiments/2026-10-04-gemini-lid-microsd-usb-re/README.md).

"Left" and "right" are as the user guide uses them: device open, keyboard
towards the user.

## 1. Summary

| | Left port | Right port |
| --- | --- | --- |
| Controller | MTU3 (SSUSB) device + xHCI host, `0x11270000` | USB11 MUSB host, `0x11200000` (source; the name "full-speed" is misleading, see §3) |
| PHY | SSUSB T-PHY, U2 port at `0x11290800`, U3 port at `0x11290900` | USB11 U2 PHY in the SIF at `0x11210800` |
| USB 3 | Controller and PHY support it; whether the connector's SuperSpeed pairs are wired is **unknown** | No. The connector's high-speed lane pairs carry HDMI instead (§6) |
| Type-C chip | FUSB301, I2C1 `0x25`, ID `0x12`, **no interrupt** | FUSB301A, I2C0 `0x25`, ID `0x12`, interrupt on GPIO64 |
| Roles in Gemian | Device (gadget); host only through an ID-pin path never seen to fire | Host only |
| VBUS out (host) | BQ25896 boost (`OTG_CONFIG`), source | GPIO94 `usb1_drvvbus`; what it switches is **unknown** |
| Charging | Yes, the only charging port (user guide) | No (user guide) |
| USB PD | No | No |
| Video | No | HDMI through SiI902x and Planet's HDMI adapter (user guide, source) |
| Firmware | None | None |
| Mainline today | Dual-role, device by default (**observed**: SSH and charging unchanged; the Type-C chip starts as a sink). Host mode written, untested | Host works (**observed**: full and high speed, PIO), modules loaded by hand |

## 2. Left port

**Controller and PHY.** The MediaTek SSUSB block: an MTU3 device controller and
an xHCI host sharing the T-PHY's U2 and U3 ports. The local series describes it
with `mediatek,mt6797-mtu3`/`mt6797-xhci` and `mt6797-tphy`, and patch 0078 runs
it peripheral-only at `maximum-speed = "high-speed"` with a forced B-session
(0077). Gemian's device driver is built with `SUPPORT_U3` (SuperSpeed default),
so the controller is SuperSpeed-capable, but no record has seen a SuperSpeed
link on this port.

**Type-C.** The I2C1 FUSB301 is bound in Gemian, reads ID `0x12`, and its probe
fails `request_irq` with `-EINVAL` because the live DT node has no interrupt
(**observed**). Its work function is empty (source). The left port's cable
detection in Gemian is the MT6351 `CHRDET` comparator plus BC1.1 typing, not the
Type-C chip.

**Roles.** Gemian's gadget runs here (**observed**). Host mode exists only as
a vendor xHCI state machine on the IDDIG pin (GPIO181, EINT186 in the vendor
map) that refuses host when the charger voltage is above 4 V and turns the
charger boost on through `bq25890_otg_en()` (source). No Gemian capture has
shown an xHCI root hub, and the IDDIG pin's wiring to the connector is
unproven.

**VBUS and charging.** This is the charger's input: the user guide says only
the left port charges. In host mode the source turns on the BQ25896 boost
(`OTG_CONFIG`, REG03 bit 5; 4.998 V, 1.4 A limit in the vendor
configuration). On the mainline station REG03 reads `0x0a`, so the boost is off
(**observed**).

## 3. Right port

**Controller and PHY.** The MT6797 USB11 block: a host-only MUSB with its own
U2 PHY in a second SIF window. Despite its Kconfig title ("fullspeed host"),
the vendor core sets `MUSBFSH_POWER_HSENAB`, which allows high-speed
negotiation (source; the speed on this unit isn't observed). Patches 0069 and
0070 add the MT6797 MUSB data and a disabled DT topology.

**Type-C.** The I2C0 FUSB301A, interrupt from GPIO64 (`fusb301a-pin`, live DT
interrupt cell 64, debounce 256 ms). The vendor reads that pin as the chip's
ID output, not INT_N. At a mainline handoff GPIO64 is already in EINT3 mode
and reads high, with no sink attached; GPIO70/71/72/94 are outputs driven
low (**observed**). Gemian probes it, reads ID `0x12`, and gets
an IRQ (**observed**). On every ID-pin change the vendor work function reads the
ID GPIO (low means a sink is attached), reads status bits 5:4 for CC1/CC2 and
then:

| Condition | GPIO94 `usb1_drvvbus` | GPIO70 `fusb301a_sw_en` | GPIO71 `fusb301a_sw_sel` | GPIO72 `sw7226_en` |
| --- | --- | --- | --- | --- |
| Idle, detach or bad CC | low | high | low | low |
| Sink attached, GPIO89 `sil9022_hpd_int` high, CC1 | high | low | low | low |
| Sink attached, GPIO89 high, CC2 | high | low | high | low |
| Sink attached, GPIO89 low ("usb1 OTG mode") | high | (unchanged, high) | (unchanged) | high |

(source). The inferred meaning: GPIO70 is an active-low enable and GPIO71 the
orientation select of a lane switch that puts the HDMI signals on the
connector, and GPIO72 enables the USB 2.0 data path for the USB11 host. Neither
switch chip is named in any source file.

**Roles.** Host only. There is no device controller behind this port.

**VBUS.** GPIO94 is the only software control for the right port's VBUS in
Gemian; the USB11 driver's own VBUS hook is compiled out, and nothing calls the
charger boost for this port (source). GPIO94 is raised for any partner that
presents Rd. What GPIO94 switches, and whether its source is the charger's
boost, a separate converter or the battery rail, is the main unknown. The
right port does not charge the device (user guide).

## 4. Both ports: Type-C behaviour

- **Gemian forces both controllers to Source-only.** Both vendor drivers write
  `0x01` to the Modes register, register `0x02` (source). Per the onsemi FUSB301 and FUSB301A
  datasheets, bit 0 is "Source" and the reset value is `0x04`, "Sink". So
  under Gemian both ports present Rp and never Rd.
- **Inference:** a USB-C-to-C charger or a Mac, which only turns VBUS on
  after it sees Rd, should not charge or enumerate the left port under Gemian,
  while a USB-A-to-C cable (legacy VBUS, always on) should. An earlier private
  Gemian watch with the left port reported cabled to the Mac stayed at
  `usb/online=0` throughout. That matches the inference but doesn't prove it,
  because the cable type wasn't recorded.
- The FUSB301 has dead-battery Rd when unpowered and comes up as a Sink. At a
  mainline station boot both chips read mode `0x04` (Sink), so Gemian's write
  does not carry over (**observed**). On that boot the left chip saw the
  laptop's C-to-C link as a 3 A source on CC2 with VBUS present
  (**observed**).
- The `SS_SW` output switches a SuperSpeed mux by itself, without software
  (datasheet). No Gemini source says whether either port's `SS_SW` pin is wired.
- **No USB Power Delivery** on either port. The FUSB301 has no PD engine; the
  vendor Kconfig for both drivers says "Only supports CC detect, without PD";
  the PD-capable alternatives in the tree (ANX7418, SiI7033, the TCPC stack)
  are not built.

## 5. Charging and the 80 % guard

- The BQ25896 has one input. The left port is it.
- The boost runs only with `OTG_CONFIG`=1, the chip's OTG pin high and no input
  at VBUS. `OTG_CONFIG` resets to 0 on power-on and on I2C watchdog expiry
  (TI SLUSC76C, REG03 table). The OTG pin's wiring isn't in any source file.
- The mainline charge guard (`linux,no-chip-config`) writes only REG03
  `CHG_CONFIG` and `WD_RST` as read-modify-writes, so it preserves
  `OTG_CONFIG`. It doesn't register the driver's `usb_otg_vbus` regulator, and
  it kicks the 40 s watchdog only while charging is stopped. So the boost
  can't be described or held on in mainline today: if something set
  `OTG_CONFIG`, the next watchdog expiry would clear it. For the left port, host
  mode needs a decision on the guard's mode, not just a DT node.
- Left-port host and left-port charging exclude each other: the boost needs an
  empty VBUS. The right port affects charging only if GPIO94 turns out to draw
  from the boost.

## 6. Video and alternate modes

- No DisplayPort alternate mode: there is no PD, and so no alt-mode negotiation.
- No MHL in the build: the Sii8348 MHL driver is in the tree but not selected.
- The build selects `CONFIG_MTK_HDMI_SUPPORT` with `CUSTOM_KERNEL_HDMI="sil9024"`,
  a SiI902x-family HDMI transmitter on I2C3 `0x39` (EDID at `0x50`), fed by
  DPI0 (source). The user guide's HDMI adapter goes on the right port. The
  callback in §3 enables the lane switch from GPIO89 only when a sink is
  attached, so this is a non-standard, Planet-specific HDMI-over-USB-C wiring,
  not a Type-C alternate mode (inference). In Gemian both I2C3 clients are
  unbound and no HPD interrupt was counted, so the transmitter has never been
  seen working ([external-display record](../../experiments/2026-07-13-external-display-recovery/README.md)).
  The source has two HPD-like pins: GPIO89 for the switch and GPIO62/EINT for
  the bridge.

## 7. Firmware

None. The FUSB301/FUSB301A are fixed-function chips. The SiI902x needs no
firmware, and neither does the MUSB or MTU3. The retained Gemian image has no
USB-C, Type-C or HDMI firmware file. See the [firmware boundary](firmware.md).

## 8. Upstream coverage

| Piece | Upstream Linux 7.1.3 | Local series | Missing |
| --- | --- | --- | --- |
| MTU3 + xHCI, left | `mtu3`, `xhci-mtk`; role from `usb-role-switch`, extcon or a `connector` child; optional `vbus-supply` | 0067 compatibles, 0068 topology, 0078 peripheral wiring | Host or dual-role on the board; U3 port never tested |
| T-PHY | `phy-mtk-tphy` | 0066 MT6797 V1, 0077 forced B-session | USB11 calibration variant |
| USB11 MUSB, right | `musb` + `mediatek.c` glue (no VBUS GPIO hook) | 0069 data, 0070 topology; 0604 PHY window, 0607 unload fix, 0608 forced session, 0619 squelch, 0620 multipoint | DMA (PIO only), detach handling |
| FUSB301/FUSB301A | None upstream | 0056 driver; 0596–0599 add polling, `vbus-out-supply`, a role switch and a sink start; 0595 a class helper | Runtime test |
| Connector, ID and VBUS | `usb-c-connector`, `regulator-fixed` | 0602: GPIO94 VBUS with GPIO72 as its supply (right), the boost (left) | Whether GPIO94 alone powers the port |
| Charger boost | `bq25890_charger` `usb_otg_vbus` regulator | 0517/0518 guard mode; 0600/0601 register the boost in that mode and keep the watchdog fed while it is on | Runtime test |
| Lane switch (GPIO70/71) | `gpio-sbu-mux` has the same enable/select shape but is for SBU lines | none | No fitting binding for an HDMI lane switch |
| HDMI | `sii902x` DRM bridge, `mtk_dpi` | disabled MT6797 DPI data | Board node, rails, HPD, DPI route |
| USB PD | Not applicable | — | — |

## 9. Mainline design

Described in the [record](../../experiments/2026-11-05-gemini-usb-c/README.md#implementation-both-ports-in-every-configuration-2026-11-06):
the left port is a device and a sink by default, a host when its Type-C
`port_type` is set to source, and gets VBUS from the boost only while a
sink is attached. The right port is a host whose VBUS follows an attached
sink. The Type-C driver owns VBUS on both; the controllers follow the role.

## 10. Open questions that need the device

Listed with their requests in the
[record](../../experiments/2026-11-05-gemini-usb-c/README.md#device-readings-needed):
whether the right port hosts under Gemian and whether the boost is on while it
does (GPIO94's source); which cable the station uses, and whether a C-to-C
charger or Mac charges the left port under Gemian; whether the left port links at
SuperSpeed under Gemian; whether a Planet HDMI adapter is available.
