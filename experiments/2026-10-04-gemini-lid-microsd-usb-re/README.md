# Experiment: Gemini lid, microSD and USB-role reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-lid-microsd-usb-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | Hall/lid input, MSDC1 microSD slot, USB-C ports, USB roles and VBUS |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, MT6351 E2) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | Not yet assigned |

## Question

What does the stock Gemian kernel actually do for the three "small win"
blocks in the roadmap's
[After Wi-Fi order](../../docs/ROADMAP.md#after-wi-fi-remaining-driver-gaps):
the lid (hall) sensor, the microSD slot and the USB ports with their role and
VBUS control? For each block this record separates what the pinned public
vendor source and the pinned Linux 7.1.3 tree prove from what still needs a
device measurement, and ranks the measurements by value. It follows the
[charging record](../2026-10-04-gemini-charging-re/README.md) and changes no
patch, profile, candidate or device state. Charging, the PMIC and the charger
boost are owned by that record and by the
[VBUS ownership record](../2026-09-08-usb-vbus-ownership/README.md); they are
only referenced here.

Earlier records own the live observations this builds on: the
[hall/lid recovery](../2026-07-12-hall-lid-switch-recovery/README.md) (live DT
and switch-class inventory), the
[MSDC recovery](../2026-07-12-mt6797-msdc-recovery/README.md) with its
[card-detect/power](../2026-07-12-mt6797-msdc-recovery/MICROSD_CONTRACT.md),
[power-state](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md) and
[pad](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md) follow-ups (retained
binary analysis), the [USB/Type-C recovery](../2026-07-12-usb-typec-recovery/README.md)
(live topology, FUSB301 probe logs) and the
[Gemian USB driver-selection observation](../2026-09-08-usb-vbus-ownership/GEMIAN_BINDINGS.md).

## Inputs

Every vendor citation below is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`. Every mainline citation is Linux
`7.1.3` as pinned in `kernel/manifest.json`. Exact URLs, sizes and SHA-256
values are in [`source-inputs.json`](source-inputs.json); line numbers refer to
those exact revisions. No vendor source, firmware or private capture is copied
into this repository.

Two caveats apply throughout:

- The public board DTS (`aeon6797_6m_n.dts`) is a reference-design file. For
  USB-C it describes GPIO196/197 redrivers and GPIO251/252 FUSB340 switches
  ([lines 1316–1468](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1316-L1468))
  that no Gemini driver reads; the Gemini port glue lives in
  `aeon_gpio.dtsi` and the `aeon_gpio` helper instead (U3). The public `hall`
  and `switch` nodes carry no `interrupts` or `debounce` property; the live
  DTB does (L2). Where public DTS and live capture disagree, the live capture
  wins.
- `cust_eint.dtsi` is a generated MT6735 reference file. Its `MSDC1_INS@5`
  entry ([lines 29–34](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/cust_eint.dtsi#L29-L34))
  is not the Gemini card-detect line; the Gemini board uses GPIO67/EINT6 (S2).

## Part 1: verified facts

### Lid (hall) and toggle inputs

- **L1. The lid sensor is a plain GPIO on GPIO66, sampled by software, with
  low meaning closed.** `hall_work_handler()` reads `gpio_get_value()` and
  reports `SW_LID = (value == HALL_FCOVER_CLOSE)` on the shared `kpd_accdet_dev`
  input device
  ([`hall.c` lines 94–122](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/hall/hall.c#L94-L122)),
  where `HALL_FCOVER_OPEN = 1` and `HALL_FCOVER_CLOSE = 0`
  ([`include/soc/mediatek/hall.h` lines 25–26](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/include/soc/mediatek/hall.h#L25-L26),
  a 2019 Gemian addition). The pin is configured as GPIO mode with pull-up
  ([`mt6797.dtsi` lines 4295–4310](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L4295-L4310)),
  and GPIO66's EINT function is EINT5
  ([`mt6797-pinfunc.h` line 390](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L390)).
  Patch 0074's `GPIO_ACTIVE_LOW` plus `SW_LID` therefore encodes the vendor
  convention exactly; only the physical magnet polarity is unmeasured.
- **L2. The vendor interrupt scheme is a level EINT whose polarity is flipped
  after each event; the 64 ms debounce is a hardware EINT debounce.** The
  handler disables the IRQ and queues work; the work re-arms the line as
  level-low when the pin reads high and level-high when it reads low, then
  calls `gpio_set_debounce()` and `enable_irq()`
  ([`hall.c` lines 123–139](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/hall/hall.c#L123-L139)).
  The probe reads `debounce` and `interrupts` from the DT node and requests
  the IRQ with `IRQF_TRIGGER_NONE`
  ([lines 241–256](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/hall/hall.c#L241-L256)).
  The public `hall` node has neither property
  ([`mt6797.dtsi` lines 4278–4283](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L4278-L4283));
  the live DTB supplies `interrupts = <66 8>` (level-low) and `debounce =
  <66 0xfa00>` (64,000 µs), per the
  [hall/lid record](../2026-07-12-hall-lid-switch-recovery/README.md#live-observations).
  Consequence for mainline: `gpio-keys` uses edge triggers and either hardware
  or software debounce (M1); the vendor's polarity dance is not needed.
- **L3. The probe samples the GPIO before it knows which GPIO it is.**
  `fcover_close_flag = gpio_get_value(hallgpiopin)` runs at
  [line 239](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/hall/hall.c#L239)
  while `hallgpiopin` is assigned from the DT at line 245, so the initial
  Android switch state is GPIO0's level, and the work handler forces five
  initial reports (`initVal < 5`, lines 99–102) to paper over it. The earlier
  record's "state 0" observations at idle are therefore not polarity evidence.
- **L4. Lid close drives keyboard policy in the vendor stack, not only an
  input event.** The hall driver runs a notifier chain
  ([`hall.c` lines 61–91, 109](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/hall/hall.c#L61-L91));
  the AW9523 keyboard driver registers for it and on `HALL_FCOVER_CLOSE` puts
  the keyboard controller into its early-suspend path, resuming on open
  ([`aw9523_key.c` lines 852–866, 929–930](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/aw9523/aw9523_key.c#L852-L866)),
  and its interrupt handler drops key interrupts while the lid is closed
  ([lines 555–559](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/aw9523/aw9523_key.c#L555-L559)).
  Under mainline this is userspace policy (`SW_LID` consumers such as logind);
  no kernel coupling is needed, but a closed-lid key storm is something a
  first lid test should watch for.
- **L5. Suspend/wake policy is the PMIC keypad's, not the hall driver's.**
  Both the hall and toggle drivers call `kpd_wakeup_src_setting()` on
  suspend/resume
  ([`hall.c` lines 288–316](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/hall/hall.c#L288-L316)),
  which is the keypad driver's wake-source toggle
  ([`kpd.c` lines 954, 970](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/keyboard/mediatek/kpd.c#L954)).
  Neither driver calls `enable_irq_wake()` on its own EINT. Lid wake is thus
  not demonstrated by the vendor path; a mainline `wakeup-source` would be a
  new behavior, consistent with patch 0074 leaving it out.
- **L6. The toggle input on GPIO93/EINT16 is a two-key pulse generator.**
  `switch.c` reads GPIO93, emits a 10 ms `KEY_F9` press for low and `KEY_F10`
  for high, updates switch class `switch`, and re-arms the level IRQ like L2
  ([`switch.c` lines 102–133](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/switch/switch.c#L102-L133)).
  The board DTS configures GPIO93 as GPIO with pull-up and labels the block
  `anti-tamper`
  ([`aeon6797_6m_n.dts` lines 1747–1768](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1747-L1768));
  GPIO93's EINT function is EINT16
  ([`mt6797-pinfunc.h` line 562](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L562)).
  No inspected file identifies the physical control. Both drivers are built
  (`CONFIG_MTK_HALL=y`, `CONFIG_MTK_TOGGLE_SWITCH=y`,
  [defconfig lines 352–353](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L352-L353)).

### microSD (MSDC1)

- **S1. The vendor slot runs 4-bit SD up to SDR104 at 200 MHz with DDR50
  disabled.** `&mmc1` sets `bus-width = <4>`, `max-frequency = <200000000>`,
  `cap-sd-highspeed`, `sd-uhs-sdr12/25/50/104`, with `sd-uhs-ddr50` commented
  out, `host_function = MSDC_SD`
  ([`aeon6797_6m_n.dts` lines 748–771](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L748-L771)).
  The SoC node is `msdc1@11240000`, GIC SPI 80 level-low, clock `INFRA_MSDC1`
  ([`mt6797.dtsi` lines 44–50](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L44-L50)),
  matching the local patch 0018 node.
- **S2. Card detect is GPIO67 in EINT6 mode, high means present, handled by
  the MMC core's GPIO card-detect path.** The node carries `cd_level =
  MSDC_CD_HIGH` (one byte) and `cd-gpios = <&pio 67 0>`
  ([`aeon6797_6m_n.dts` lines 769–770](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L769-L770));
  `msdc_of_parse()` reads both
  ([`msdc_io.c` lines 580–587](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/msdc_io.c#L580-L587))
  and `msdc_dt_init()` calls `mmc_of_parse()`
  ([line 615](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/msdc_io.c#L615)),
  which in 3.18 requests the `cd-gpios` descriptor and its IRQ. `msdc_ops_get_cd()`
  then reads the raw level and applies `cd_level`
  ([`sd.c` lines 4726–4768](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/sd.c#L4726-L4768)).
  The MSDC1 probe selects a dedicated `insert_cfg` pin state that puts GPIO67
  in `EINT6` mode with Schmitt trigger and pull-up
  ([`msdc_io.c` lines 739–757](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/msdc_io.c#L739-L757);
  [`aeon6797_6m_n.dts` lines 777–784](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L777-L784)).
  This agrees with the retained-binary analysis in the
  [card-detect contract](../2026-07-12-mt6797-msdc-recovery/MICROSD_CONTRACT.md#card-detection).
  The local EINT patch 0005 maps GPIO67 to EINT6, so a mainline
  `cd-gpios = <&pio 67 GPIO_ACTIVE_HIGH>` gets its interrupt through the same
  line.
- **S3. Slot power is VMCH (card) and VMC (I/O), both requested at 3.0 V, and
  the stock kernel leaves VMCH on with an empty slot.** `msdc_sd_power()` for
  host 1 programs drive/TDSEL/RDSEL, then requests VMCH at 3.0 V and VMC at
  3.0 V
  ([`msdc_io.c` lines 296–311](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/msdc_io.c#L296-L311)).
  The probe first does an on/off pair "so that removable card slot won't keep
  power"
  ([`sd.c` lines 5657–5665](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/sd.c#L5657-L5665)),
  but a later board-specific addition turns VMCH back on unconditionally at
  the end of probe (`msdc_sd_power(host, 1)` with a `power on vmch` print,
  [lines 5817–5820](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/sd.c#L5817-L5820)).
  Together with the off path never issuing a regulator disable
  ([power-state follow-up](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md)),
  this explains the live finding that VMCH and VMC read enabled at 3.0 V with
  no card and MSDC1 powered off. The PMIC DT ranges are VMCH 3.0–3.3 V and
  VMC 1.2–3.3 V
  ([`mt6797.dtsi` lines 580–585, 725–730](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L580-L585)).
- **S4. The probe applies relative PMIC trim adjustments and the 1.8 V switch
  applies another.** For host 1 the probe reads `0xACE` (VMCH cal), subtracts
  5 modulo 32 and writes it back, then reads `0xAE2` (VMC cal) and adds 5
  ([`sd.c` lines 5429–5460](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/sd.c#L5429-L5460));
  the 1.8 V switch applies a further VMC cal write before requesting 1.8 V
  ([`msdc_io.c` lines 199–222](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/msdc_io.c#L199-L222)).
  The source comments call the VMCH step "default change to 0 mV" and the VMC
  step "default not +100 mV". The retained-binary analysis confirms the same
  arithmetic and that upstream `regmap_update_bits()` on the voltage masks
  preserves these trim bits ([power-state follow-up](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md#the-standard-regulator-operations-preserve-trim-bits)).
  What remains unknown is the value the loader leaves in those fields, so the
  electrical meaning of "nominal 3.0 V" without the adjustment is unmeasured.
- **S5. After power-on the vendor checks VMCH over-current and powers off on
  OC.** `msdc_set_power_mode` reads `MT6351_PMIC_OC_STATUS_VMCH` 10 ms after
  enabling and disables power if set
  ([`sd.c` lines 1237–1250](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/sd.c#L1237-L1250)).
  Mainline has no equivalent; the MT6351 OC status bit is a cheap read-only
  diagnostic for a first card test.

### USB ports, roles and VBUS

- **U1. The stock build is a fixed-role split: MTU3 device on one port, USB11
  (MUSB) host on the other, with xHCI only loaded on an ID-pin event.**
  `CONFIG_USB_MU3D_DRV=y`, `CONFIG_MU3_PHY=y`, `CONFIG_MTK_USBFSH=y`,
  `CONFIG_USB_XHCI_MTK=y`, `CONFIG_USB_MTK_DUALMODE=y`,
  `CONFIG_USB_C_SWITCH_FUSB301=y`, `CONFIG_USB_C_SWITCH_FUSB302=y`,
  `CONFIG_USB_GADGET_VBUS_DRAW=500`
  ([defconfig lines 274–292, 464](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L274-L292)).
  The SoC nodes are `usb1@11200000` (`mediatek,mt6797-usb11`, SPI 73), the
  combined `usb3@11270000` (SPI 127 MUSB, SPI 126 xHCI) and `usb3_xhci` with
  the `eint_usb_iddig@181` child on EINT186
  ([`mt6797.dtsi` lines 2921–2956](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L2921-L2956)).
  The [USB recovery record](../2026-07-12-usb-typec-recovery/README.md#observations)
  observed exactly this at runtime: a USB1 root hub, `musb-mtu3d` bound, and
  `usb3_xhci` unbound. The local DT names the MTU3 port the left connector
  (patch 0078 comment) and the gadget path on it is proven; by elimination the
  USB11 host port is the right connector, which the inspected source does not
  itself state (H6).
- **U2. MTU3 device-side cable detection is the PMIC's, not the controller's.**
  `mu3d_hal_is_vbus_exist()` returns `upmu_get_rgs_chrdet()` / `upmu_is_chr_det()`
  ([`mt_usb.c` lines 237–252](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/mu3d/drv/mt_usb.c#L237-L252))
  and `usb_cable_connected()` connects the gadget only for BC1.1 `STANDARD_HOST`
  or `CHARGING_HOST` with VBUS present
  ([lines 256–292](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/mu3d/drv/mt_usb.c#L256-L292)).
  These are the `CHRDET` and BC1.1 facts of the charging record (F4, F6). It
  also means the vendor never relies on the T-PHY's own VBUS/session sensing,
  which is consistent with the forced B-session the local patch 0077 needed.
- **U3. Host-port VBUS and the SuperSpeed/HDMI mux are driven by one board
  callback keyed on the FUSB301A's ID output, using GPIO94, GPIO70, GPIO71 and
  GPIO72.** The `fusb302/`-directory driver matches `mediatek,fusb301a`
  ([`usb_typec.c` line 331](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/usb_c/fusb302/usb_typec.c#L331)),
  writes mode `0x01` and reads the device ID at probe (lines 54–61), takes its
  interrupt and GPIO from the `mediatek,fusb301a-pin` node (lines 192–212),
  and in its work function reads the ID GPIO: ID low means attached, then
  status bits `0x30` select CC1 (`0x10`) or CC2 (`0x20`); on either it raises
  `usb1_drvvbus` (GPIO94); if the HDMI hot-plug input `sil9022_hpd_int`
  (GPIO89) is high it lowers `fusb301a_sw_en` (GPIO70) and sets
  `fusb301a_sw_sel` (GPIO71) per CC orientation, otherwise it raises
  `sw7226_en` (GPIO72) for "usb1 OTG mode"; detach or an invalid CC restores
  GPIO70 high, GPIO71 low, GPIO72 low, GPIO94 low, and the level IRQ polarity
  is flipped as in L2
  ([lines 96–167](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/usb_c/fusb302/usb_typec.c#L96-L167)).
  The pin states are plain GPIO outputs
  ([`aeon_gpio.dtsi` lines 181–243](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon_gpio.dtsi#L181-L243));
  GPIO94's alternate function 1 is the SoC `USB_DRVVBUS`
  ([`mt6797-pinfunc.h` line 570](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L570)),
  which the vendor does not use. The USB11 host driver's own VBUS hook is
  disabled: `mt65xx_usb11_vbus()` is `#if 0` and `board_set_vbus` is commented
  out
  ([`musbfsh_mt65xx.c` lines 1253–1263, 1298](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/usb11/mt6797/musbfsh_mt65xx.c#L1253-L1263)).
  So in the stock kernel GPIO94 is the only software VBUS control for the
  host port, and it is raised for *any* attached partner, including a Type-C
  host (CC1/CC2 present, no role check). What GPIO94 switches electrically
  (a load switch from the charger boost, from VBUS of the other port, or from
  a separate 5 V source) is still not in any inspected file; the
  [VBUS record](../2026-09-08-usb-vbus-ownership/README.md) stands.
- **U4. The second FUSB301 (I2C1 `0x25`) has no functional path.** The
  `fusb301/`-directory driver (`mediatek,fusb301`, `FUSB301_0`) writes mode
  `0x01`, requests an IRQ from a `mediatek,fusb301-eint` node whose public
  definition has no `interrupts` property, and its work function is empty
  ([`usb_typec.c` lines 49–56, 93–100, 118–150](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/usb_c/fusb301/usb_typec.c#L93-L100)).
  This matches the live `request_irq` `-EINVAL` in the
  [USB recovery record](../2026-07-12-usb-typec-recovery/README.md#type-c-ports-and-board-switching).
  The device-port FUSB301 therefore only puts the chip in its default mode;
  all device-port behavior comes from the PMIC (U2). Both controllers report
  ID `0x12` and are generic autonomous controllers (patch 0056 driver).
- **U5. The xHCI ID-pin path is a software state machine on EINT186 that
  refuses host mode when VBUS is already above 4 V.** `mtk_xhci_eint_iddig_init()`
  takes the IRQ from the `mediatek,usb_iddig_bi_eint` node
  ([`xhci-mtk-driver.c` lines 710–726](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/xhci/xhci-mtk-driver.c#L710-L726)),
  requests it `IRQF_TRIGGER_LOW` with `enable_irq_wake()` (lines 685–699), and
  `mtk_xhci_mode_switch()` on ID-in checks `battery_meter_get_charger_voltage()
  > 4000` to choose `IDPIN_IN_DEVICE` (do nothing) over `IDPIN_IN_HOST`
  (load xHCI, enable charger OTG boost)
  ([lines 174–184, 613–627](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/xhci/xhci-mtk-driver.c#L613-L627)).
  Host load enables the charger boost through `bq25890_otg_en()`
  ([lines 425–460](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/xhci/xhci-mtk-driver.c#L425-L460),
  owned by the VBUS record). GPIO181's function 1 is the SoC `IDDIG`
  ([`mt6797-pinfunc.h` line 967](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L967));
  the live EINT map places EINT186 on GPIO181's alternate mode and EINT106 on
  its GPIO mode ([resource map](../../docs/hardware/mt6797-live-resource-map.md)),
  and the local patch 0005 maps GPIO181 to EINT106. Two different lines thus
  serve the same pin depending on mux mode. The live capture showed an
  `iddig_eint` consumer and no xHCI root hub, so no host session was ever
  observed on the MTU3 port.
- **U6. GPIO237 is a `usb_det` input the board helper only initialises.**
  `aeon_gpio.dtsi` defines `usb_det_low` as GPIO237 input with pull-down
  ([lines 245–253](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon_gpio.dtsi#L245-L253))
  and the helper selects it at probe
  ([`aeon_gpio.c` line 163](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpio/aeon_gpio.c#L163)).
  None of the nineteen vendor files inspected here reads it afterwards; the
  public board DTS also muxes GPIO237 as `SPI1_CS_B`
  ([`aeon6797_6m_n.dts` lines 1612–1625](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1612-L1625)).
  This is a bounded negative (not a whole-tree search); the pin is recorded
  so that a later VBUS-sense hypothesis does not rediscover it.

### Mainline 7.1.3 and this repository

- **M1. `gpio-keys` covers the lid completely.** It supports `EV_SW`/`SW_LID`,
  `debounce-interval` through `gpiod_set_debounce()` with a software fallback
  ([`gpio_keys.c` lines 554–561](https://github.com/gregkh/linux/blob/v7.1.3/drivers/input/keyboard/gpio_keys.c#L554-L561)),
  both-edge interrupts (line 599) and `wakeup-source` (lines 817–820). Patch
  0074 already describes GPIO66 as `GPIO_ACTIVE_LOW`, `SW_LID`, 64 ms, disabled,
  no wake. Upstream `pinctrl-mtk-mt6797.h` has `NO_EINT_SUPPORT` on every pin;
  the local patch 0005 adds EINT5/EINT6/EINT3/EINT16 for GPIO66/67/64/93, so the
  interrupt path exists only with the local series.
- **M2. `mtk-sd` and the MMC core cover card detect and both rails; the
  local DT has neither an MSDC1 board node nor VMCH/VMC regulator nodes.**
  `msdc_get_cd()` defers to `mmc_gpio_get_cd()`
  ([`mtk-sd.c` lines 2717–2726](https://github.com/gregkh/linux/blob/v7.1.3/drivers/mmc/host/mtk-sd.c#L2717-L2726)),
  `msdc_set_power_mode` drives `vmmc` through `mmc_regulator_set_ocr()` and
  `vqmmc` through `regulator_enable()`/`disable()` (lines 2151–2176), and the
  1.8 V switch selects `state_uhs` (lines 1663–1686; binding
  [`mtk-sd.yaml` lines 72–93](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/mmc/mtk-sd.yaml#L72-L93)).
  Locally, patch 0018 adds the disabled `mmc@11240000` node; patch 0020 adds
  only `ldo-vemc` and `ldo-vio18` regulator nodes and no `&mmc1`; patch 0015
  implements `ldo-vmch` (`0x0a2e` enable, `0x0ace` VOSEL bit 8) and `ldo-vmc`
  in the driver; the MSDC1 pad-field work (IES, drive, pull) lives in the
  separate `upstream-4d7d9486` topics and is not in the v7.1.3 series
  (patch 0071 is pinmux-only). The [pinctrl-errors fix](../2026-09-09-mtk-sd-pinctrl-errors/README.md)
  is likewise outside the device series.
- **M3. MTU3 dual-role in 7.1.3 has three selectable role sources and an
  optional `vbus` regulator; the local node is peripheral-only.** `mtu3_plat.c`
  takes `vbus` through `devm_regulator_get()` (a dummy when absent,
  [lines 290–294](https://github.com/gregkh/linux/blob/v7.1.3/drivers/usb/mtu3/mtu3_plat.c#L290-L294))
  and selects `enable-manual-drd` (debugfs), `usb-role-switch` or `extcon`
  (lines 300–318); `ssusb_set_vbus()` enables that regulator on host role
  ([`mtu3_dr.c` lines 103–125](https://github.com/gregkh/linux/blob/v7.1.3/drivers/usb/mtu3/mtu3_dr.c#L103-L125))
  and `ssusb_set_force_mode()` can force IDDIG in the IPPC register
  (lines 238–259). The binding allows a `connector` child, including
  `gpio-usb-b-connector` with `id-gpios`/`vbus-gpios`
  ([`mediatek,mtu3.yaml` lines 101–148](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/usb/mediatek,mtu3.yaml#L101-L148);
  [`usb-conn-gpio.c` line 356](https://github.com/gregkh/linux/blob/v7.1.3/drivers/usb/common/usb-conn-gpio.c#L356)).
  The local patches 0068/0070 add disabled MTU3/xHCI and USB11 topologies,
  0078 sets `dr_mode = "peripheral"` with no `vbus-supply`, 0077 forces the
  B-session in the T-PHY, and 0056 adds the FUSB301 Type-C class driver with
  no Gemini node. The T-PHY driver's `mediatek,force-mode` and `set_mode`
  ([`phy-mtk-tphy.c` lines 1130, 1442–1449](https://github.com/gregkh/linux/blob/v7.1.3/drivers/phy/mediatek/phy-mtk-tphy.c#L1442-L1449))
  are the upstream hooks a dual-role port would use instead of the vendor
  `usb20_pll_settings` path.
- **M4. The MUSB glue in 7.1.3 has no VBUS GPIO hook.** `drivers/usb/musb/mediatek.c`
  handles role through the MUSB core and a `usb-role-switch`/extcon; the
  USB11 host port's VBUS must come from a `vbus-supply` on a connector or a
  regulator consumer, which is exactly the GPIO94 ownership question of U3.

## Part 2: hypotheses, ranked by value per device minute

"Gemian read" means one bounded, read-only inspection of the running stock
kernel over the known-good LAN SSH path under the existing standing
authorization; "mainline boot" means a new reviewed experiment with its own
candidate, hypothesis and stop conditions. None is admitted by this record.

1. **H1. Enabling patch 0074's `gpio-keys` node as-is yields a correct
   `SW_LID` on the first try (L1, L2, M1).** The only unknown is the magnet
   polarity, and L3 shows the vendor's idle "state 0" is not evidence either
   way. Test: a mainline boot with the node enabled and `evtest` (or
   `/sys/class/input/*/sw` plus `/proc/interrupts` EINT5 counts) across one
   attended close/open; expected `SW_LID` 1 while closed. Branches: inverted
   → flip to `GPIO_ACTIVE_HIGH`; no events but level changes in `gpio` debugfs
   → EINT5 routing in patch 0005 is wrong; no level change → pull/magnet
   question (L1 pull-up is boot-firmware state under patch 0071's policy).
   Cheapest decision-changing test in this record. Confidence: high.
2. **H2. The MT6351 `CHRDET` interrupt is also the right mainline VBUS/role
   signal for the device port (U2), so the gadget path needs no FUSB301 and
   no T-PHY sensing.** This is the charging record's H2 seen from USB: if
   `CHRDET` fires, a small `extcon` or `usb-conn` consumer can drive the MTU3
   role switch, and the forced B-session (0077) can become conditional. Test:
   the same mainline boot as charging H2 (count `CHRDET` across one cable
   change); no extra device time. Confidence: high.
3. **H3. microSD at 3.0 V works with VMCH as `vmmc`, VMC as `vqmmc`, GPIO67
   active-high card detect and no UHS, without reproducing the trim
   arithmetic (S2, S3, S4, M2).** Requires: `ldo-vmch`/`ldo-vmc` regulator
   nodes under the MT6351 node, an `&mmc1` node with `cd-gpios = <&pio 67
   GPIO_ACTIVE_HIGH>`, `no-1-8-v`, `max-frequency` ≤ 50 MHz, pinmux-only pad
   state (0071 policy), and the host AUXADC/OC bit left alone. Before the
   card test, a Gemian read of PMIC `0xACE` and `0xAE2` bits 4:0 (through the
   vendor's own register debug interface, read-only) settles what trim the
   loader plus vendor probe leave in place; a mainline boot then compares the
   same fields at entry. Decision branches: card enumerates and reads a
   known file → S4 is a non-issue at 3.0 V; `vmmc` OC or no CMD response →
   measure VMCH with the MT6351 OC status (S5) before changing anything;
   card detect never fires → EINT6 routing or pull. Confidence: medium (the
   mainline `set_ios` path enables VMC before VMCH only by ordering, and the
   vendor applies drive settings mainline cannot yet).
4. **H4. GPIO94 switches a 5 V source that is independent of the MTU3 port
   and of the charger boost, so the host port can source VBUS under mainline
   with a plain `regulator-fixed` + `gpio` and no OTG boost (U3).** The
   vendor raises GPIO94 for every attach while the xHCI/boost path stays idle
   (U1, U5), which argues for a separate switch; the VBUS record argues the
   wiring is unproven. Test, in order: (a) Gemian read of the host port's
   VBUS pin with a USB meter while a known-good hub is attached and while
   nothing is attached (GPIO94 low) – no device write; (b) a mainline boot
   that configures GPIO94 as a `regulator-fixed` with `enable-active-high`,
   `status = "disabled"`, then toggles it once from userspace with the meter
   on the port and the charger unplugged, watching the charging record's H3
   charger status for a boost flag. Branches: 5 V appears only with GPIO94
   high and `OTG_CONFIG` clear → H4 true, USB11 host can be described with
   `vbus-supply`; 5 V appears only when the boost is on → the host port
   depends on the charger and the VBUS record's joint session is required.
   Confidence: medium.
5. **H5. The FUSB301A's ID output on GPIO64/EINT3 is the correct
   `id-gpios` for a `gpio-usb-b-connector` on the host port, and its CC
   orientation feeds the SW7226 redriver only for SuperSpeed, which a first
   USB 2.0 host test does not need (U3, M3, M4).** Test: in the H4 boot, read
   GPIO64 through gpio debugfs with and without a partner attached (active
   low expected), and read the FUSB301 status register through patch 0056's
   Type-C class attributes; no redriver GPIO is touched. If both agree, the
   USB11 host node (0070) can gain a connector child and the host test can
   be scheduled with the H4 VBUS owner. Confidence: medium-high for the ID
   polarity, low for whether USB 2.0 data passes the mux at the default
   GPIO70 high / GPIO72 low state (the vendor raises GPIO72 for "OTG mode").
6. **H6. The MTU3 port's hardware IDDIG (GPIO181 function 1, EINT186) is
   never grounded on the Gemini, so mainline dual-role on the left port
   should be driven by a role switch, not by the IDDIG pin (U1, U5).** The
   vendor only observed `iddig_eint` with no host session, and gates host
   mode on charger voltage anyway. Test: a Gemian read of `/proc/interrupts`
   `iddig_eint` count across one attach of an OTG adapter to the left port
   (no role change happens unless the vendor state machine loads xHCI, which
   its 4 V check prevents on a powered adapter); a count change proves the
   pin is wired. Branches decide whether patch 0068's MTU3 node ever needs
   `mediatek,force-mode`/IDDIG handling or only `usb-role-switch`.
   Confidence: medium.
7. **H7. The toggle on GPIO93 is a user-facing physical control whose two
   positions map to F9/F10 in Gemian userspace (L6).** Test: a Gemian read
   of `/proc/interrupts` EINT16 and the `switch` class state across one
   attended flip of each physical slider on the unit; the owner's own
   observation of which control moved resolves "anti-tamper" versus slider.
   Confidence: medium; cheap and it unblocks a one-line `gpio-keys` entry.
8. **H8. Lid wake is not a vendor behavior and should stay off until suspend
   exists (L5).** No test now; record only so that `wakeup-source` is not
   added to 0074 by analogy with other boards.
9. **H9. The upstream MT6797 pinctrl's missing pull/IES/drive callbacks
   do not block H3 at 3.0 V, because the boot firmware leaves MSDC1 pads in
   the vendor insert/default state (S2, M2).** Test: the H3 boot dumps the
   IOCFG_B fields from the [pad record](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md)
   at entry and compares with the vendor's active tuples. A mismatch moves
   the `upstream-4d7d9486` pad topics into the device series before a UHS
   test. Confidence: medium.

## Consequences for the roadmap (no changes applied here)

- The lid is ready for its one attended transition (H1); nothing in the vendor
  source argues for more preparation. The toggle needs an owner observation
  (H7), not source work.
- microSD needs two DT additions before a card test (VMCH/VMC regulator nodes,
  an `&mmc1` node) and one Gemian trim read (H3); the trim adjustment itself
  should not be ported.
- USB roles split cleanly: the device port's role signal is the PMIC `CHRDET`
  (H2, shared with charging), the host port's VBUS is GPIO94 whose source is
  the remaining unknown (H4), and the FUSB301A ID line is the candidate
  connector input (H5). The second FUSB301 contributes nothing in the stock
  kernel (U4). Nothing here authorizes a VBUS, role or boost change on the
  device.

## Validation

Documentation-only change: `./scripts/check-repository` and link checks apply;
no kernel build, DT check or device action was performed. Line numbers were
taken from the exact fetched files recorded in `source-inputs.json`.
