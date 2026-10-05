# Experiment: Gemini charging path reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-charging-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | BQ25896 charger, MT6351 charger detection, BC1.1, fuel gauge and AUXADC, USB VBUS |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, MT6351 E2) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | Not yet assigned |

## Question

What does the stock Gemian kernel actually do to charge the battery, detect a
charger, measure the battery and report state, and what does that imply for a
mainline description? The roadmap's
[battery and charging step](../../docs/ROADMAP.md#after-wi-fi-remaining-driver-gaps)
listed three unknowns: the charger interrupt line, conservative charge limits
and the fuel-gauge source. This record answers them from the pinned public
vendor source and the pinned Linux 7.1.3 tree, separates verified facts from
hypotheses, and ranks the hypotheses by how they should be tested on the
device. It changes no patch, profile, candidate or device state.

Earlier records own the live observations this builds on: the
[charger recovery experiment](../2026-07-12-charger-power-recovery/README.md)
(I2C population, vendor bindings, telemetry snapshots), the
[BQ25896 identity read](../2026-07-12-charger-power-recovery/CHARGER_ID.md),
the [PMIC recovery](../2026-07-11-mt6351-pmic-recovery/README.md) (MT6351 E2,
EINT176) and the [USB VBUS ownership record](../2026-09-08-usb-vbus-ownership/README.md).

## Inputs

Every vendor citation below is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`, the same commit the identity read
used. Every mainline citation is Linux `7.1.3` as pinned in
`kernel/manifest.json`. Exact URLs, sizes and SHA-256 values are in
[`source-inputs.json`](source-inputs.json). Line numbers refer to those exact
revisions. No vendor source, firmware or private capture is copied into this
repository; register addresses, bit positions and configuration values are
cited as facts.

One caveat applies throughout: the public board DTS (`aeon6797_6m_n.dts`) does
not match the live Gemian DTB in the charger node (fact F2). Where the public
DTS and the live capture disagree, the live capture wins and the public value is
marked as such.

## Part 1: verified facts

### Charger silicon, bus and driver selection

- **F1. The populated charger is a BQ25896 at I2C0 `0x6b`.** Register `0x14`
  read `0x06` (PN `000`, DEV_REV `10`) through the vendor interface on
  2026-09-12. Source: [`CHARGER_ID.md`](../2026-07-12-charger-power-recovery/CHARGER_ID.md),
  [`results/charger-id-20260912.json`](../2026-07-12-charger-power-recovery/results/charger-id-20260912.json).
  The vendor defconfig selects the BQ25896 path:
  `CONFIG_MTK_BQ25896_SUPPORT=y` at
  [`aeon6797_6m_n_defconfig` line 186](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L186),
  which the power
  [Makefile lines 43–44](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/Makefile#L43-L44)
  maps to `bq25890.o` and `charging_hw_bq25890.o`. `CONFIG_MTK_RT9466_SUPPORT=y`
  (line 187) also builds the RT9466 driver, whose probe reports no device on the
  live board ([2026-07-14 capture index](../2026-07-12-charger-power-recovery/results/live-charger-battery-recovery-20260714.txt)).
- **F2. The public board DTS does not describe the live charger node.**
  [`aeon6797_6m_n.dts` lines 46–50](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L46-L50)
  contains `bq24261@6b` with compatible `bq24261`, while the live DTB has
  `/soc/i2c@11007000/sw_charger@6b` with compatible `mediatek,sw_charger`
  ([`CHARGER_ID.md`](../2026-07-12-charger-power-recovery/CHARGER_ID.md),
  "Identity, finite effects and collection"). The vendor driver matches only
  `mediatek,sw_charger`
  ([`bq25890.c` lines 1150–1151](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/bq25890.c#L1150-L1151)).
  The live DTB therefore came from a board file this public commit does not
  carry; board-level values in the public DTS are not authoritative.
- **F3. The vendor charger driver requests no interrupt.** `bq25890.c` includes
  `<linux/of_irq.h>` but contains no `request_irq`, `request_threaded_irq`,
  `irq_of_parse_and_map` or EINT registration; its probe only stores the client,
  runs a presence check on register `0x03`, dumps registers and hooks the
  control table
  ([`bq25890.c` lines 1041–1056](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/bq25890.c#L1041-L1056)).
  The live `sw_charger@6b` node exposed only `compatible` and `reg`
  ([reuse audit](../2026-07-12-charger-power-recovery/results/bq25890-reuse-audit-20260713.txt)).
  Consequence: the BQ25896 `INT` pin's board wiring is not recorded anywhere in
  the vendor software path; the stock kernel polls the charger from a thread
  (F13) and reacts to cable events through the PMIC (F4).
- **F4. Cable presence comes from the MT6351 `CHRDET` comparator, not the
  charger.** Presence reads `RGS_CHRDET` = `CHR_CON0` (`0x0F78`) bit 5
  ([`upmu_hw.h` lines 981, 11148–11150](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/upmu_hw.h#L11148-L11150));
  used by `is_chr_det()` and `charging_get_charger_det_status()`
  ([`charging_hw_bq25890.c` lines 268–277, 506–515](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/charging_hw_bq25890.c#L268-L277)).
  The plug/unplug event is PMIC interrupt 46 (`INT_CON2` bit 14, `INT_STATUS2`
  at `0x02E4` bit 14; header lines 3018–3020, 3204–3206), registered as
  `chrdet_int_handler` and enabled unconditionally at
  [`pmic_irq.c` lines 599 and 614](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_irq.c#L599).
  The handler asserts `RG_USBDL_RST` and calls `do_chrdet_int_task()`
  ([lines 285–308](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_irq.c#L285-L308)).
  The local MT6351 interrupt enumeration already carries this line as
  `MT6351_IRQ_CHRDET`, the 47th entry (index 46) in
  [patch 0010](../../patches/v7.1.3/0010-mfd-mt6397-add-MT6351-core-and-interrupt-support.patch),
  so the numbering matches the vendor.
- **F5. The PMIC's external interrupt is EINT176 (vendor pseudo-GPIO 262),
  level-high, 1 ms debounce.** Live DT decode in
  [`eint-summary.txt`](../2026-07-11-mt6351-pmic-recovery/results/eint-summary.txt)
  and [`runtime-summary.txt`](../2026-07-11-mt6351-pmic-recovery/results/runtime-summary.txt);
  the public `mt6797.dtsi` agrees (`interrupts = <262 4>`, `debounce = <262 1000>`,
  [lines 969–975](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L969-L975)).
  Vendor requests it with `request_irq(..., IRQF_TRIGGER_NONE, "pmic-eint")`
  and `enable_irq_wake`
  ([`pmic_irq.c` lines 627–638](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_irq.c#L627-L638)).

### Charger type (BC1.1) and USB

- **F6. USB charger-type detection is done by the MT6351 BC1.1 block, not by
  the BQ25896 and not by the USB PHY.** `hw_charging_get_charger_type()` runs
  DCD, step A1/A2/B2 on the PMIC `RG_BC11_*` fields in `CHR_CON20` (`0x0FA0`:
  `BB_CTRL` bit 0, `RST` bit 1, `VSRC_EN` bits 2–3, `CMP_OUT` bit 7; header lines
  11319–11330) and classifies SDP (`STANDARD_HOST`), CDP (`CHARGING_HOST`),
  DCP (`STANDARD_CHARGER`), non-standard and Apple types
  ([`pmic_chr_type_det.c` lines 82–318](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_chr_type_det.c#L82-L318)).
  `Charger_Detect_Init()`/`Release()` (USB PHY D+/D- switch to the PMIC) wrap
  the sequence. The charger's own D+/D- detection is explicitly disabled:
  `REG02[0] AUTO_DPDM_EN = 0`, `HVDCP_EN = 0`, `MAXC_EN = 0`
  ([`charging_hw_bq25890.c` lines 1028–1030](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/charging_hw_bq25890.c#L1028-L1030)).
- **F7. The vendor `ac`/`usb` power-supply split is a software mapping of the
  BC1.1 result.** `AC_ONLINE = 1` for non-standard, DCP and Apple types; SDP and
  CDP stay on `usb`
  ([`battery_common.c` lines 2060–2080](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/power/mediatek/battery_common.c#L2060-L2080)).
  The earlier capture's "AC online, USB offline" therefore means a DCP-class
  adapter was attached, not a separate barrel input. Vendor logs' `chr_type=4`
  is `STANDARD_CHARGER` (DCP).
- **F8. Pump Express Plus is enabled and used with this charger.**
  `CONFIG_MTK_PUMP_EXPRESS_PLUS_SUPPORT=y`
  ([defconfig line 389](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L389)).
  For a DCP the switch-charging policy calls the PE+ hooks
  ([`switch_charging.c` lines 758–762](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/power/mediatek/switch_charging.c#L758-L762)),
  which raise adapter VBUS to 7 V and then try 9 V and 12 V
  ([`mtk_pep_intf.c` lines 233–234, 466–490](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/power/mediatek/mtk_pep_intf.c#L466-L490))
  using the BQ25896 `PUMPX_UP`/`PUMPX_DN` current-pulse pattern
  (`charging_set_ta_current_pattern`, `charging_hw_bq25890.c` line 656 onward;
  `bq25890_pumpx_up`, `bq25890.c` lines 656–672). The vendor `VINDPM` table
  and `V_CHARGER_MAX = 6500 mV` only apply to the non-PE path. The private
  capture's logged 3000 mA charge current with a 1700 mA input limit
  ([index](../2026-07-12-charger-power-recovery/results/live-charger-battery-recovery-20260714.txt))
  is consistent with a raised-VBUS PE+ session, not with 5 V operation.
- **F9. VBUS voltage is measured by the PMIC, not the charger ADC.**
  `read_adc_v_charger()` reads PMIC AUXADC channel 2 (`VCDT`, 12-bit, ratio 1,
  1.8 V full scale) and scales by `(r_charger_1 + r_charger_2) / r_charger_2`
  with DT values 330 and 39
  ([`battery_meter_hal.c` lines 1168–1183](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/battery_meter_hal.c#L1168-L1183),
  [`pmic_auxadc.c` lines 495–498](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_auxadc.c#L495-L498),
  [`mt6797.dtsi` lines 1042–1043](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L1042-L1043)).
  So an external 330 k / 39 k divider feeds the MT6351 `VCDT` pin, giving a
  nominal 17 V full scale. The PMIC `VCDT_HV` comparator threshold is also
  programmed by the charger HAL (`charging_set_hv_threshold`, line 457;
  `RG_VCDT_HV_EN`, line 803).
- **F10. The USB VBUS source path is unchanged from the earlier record.**
  GPIO94 (`usb1_drvvbus`) and the charger `OTG_CONFIG` boost (REG03[5], default
  boost 4.998 V, 1.4 A limit at `charging_hw_bq25890.c` lines 1036–1038) remain
  two software paths with no proven electrical join; see the
  [VBUS ownership record](../2026-09-08-usb-vbus-ownership/README.md). The
  public `aeon_gpio.dtsi` charger-enable pin states (`chr_ce0`/`chr_ce1`) are
  empty placeholders
  ([lines 63–77](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon_gpio.dtsi#L63-L77)),
  so no CE GPIO is documented for this board.

### Charger register configuration (the vendor's effective "board limits")

- **F11. `charging_sw_init()` is the full BQ25896 configuration the stock
  kernel applies at battery-driver start**
  ([`charging_hw_bq25890.c` lines 1003–1060](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/charging_hw_bq25890.c#L1003-L1060)).
  The decoded values, using TI's BQ25896 register map (datasheet rev. C,
  table 26 and preceding register tables; the same document the identity read
  cited):

  | Register / field | Vendor write | Decoded meaning |
  | --- | --- | --- |
  | REG00 `EN_ILIM` | 1 | Hardware ILIM pin is honoured: a board resistor sets a second input-current ceiling |
  | REG00 `IINLIM` | `0x3F` | 3.25 A register input limit (overridden per cable type later, F12) |
  | REG01 `VINDPM_OS` | `0x6` | 600 mV offset (relative mode) |
  | REG0D `FORCE_VINDPM`=1, `VINDPM`=`0x13` | absolute 4.5 V | Input voltage DPM threshold 2.6 V + 19 × 0.1 V |
  | REG04 `ICHG` | `0x08` | 512 mA initial fast-charge current ("pre-CC"), raised later by policy |
  | REG06 `VREG` | `0x20` | 3.840 V + 32 × 16 mV = **4.352 V** battery regulation voltage |
  | REG06 `BATLOWV` | 1 | 3.0 V precharge-to-fast-charge threshold |
  | REG06 `VRECHG` | 0 | Recharge at VREG − 100 mV |
  | REG05 `IPRECHG` | `0x1` | 128 mA precharge |
  | REG05 `ITERM` | `0x1` | 128 mA termination current |
  | REG07 `EN_TERM` | **0** | Hardware termination **disabled**; software decides "full" (F13) |
  | REG07 `WATCHDOG` | `0x1` | 40 s I2C watchdog **enabled**, kicked from the battery thread |
  | REG07 `EN_TIMER`=1, `CHG_TIMER`=`0x2` | 12 h | Safety timer on |
  | REG07 `JEITA_ISET` | 1 | 20 % × ICHG in JEITA cool region |
  | REG09 `JEITA_VSET` | 0 | VREG − 200 mV in JEITA warm region |
  | REG02 `ICO_EN` | 1 | Input current optimizer on |
  | REG02 `HVDCP_EN`, `MAXC_EN`, `AUTO_DPDM_EN` | 0 | Charger-side adapter detection off (F6) |
  | REG02 `BOOSTF` | 0 | 1.5 MHz boost |
  | REG0A `BOOSTV` | `0x7` | 4.998 V OTG boost |
  | REG0A `BOOST_LIM` | `0x3` | 1.4 A boost current limit (vendor comment says 1.3 A; TI table and the vendor's own `BOOST_CURRENT_LIMIT` array at `charging_hw_bq25890.c` lines 142–145 give 1400 mA) |
  | REG08 `BAT_COMP`=`0x4`, `VCLAMP`=`0x6` | 80 mΩ, 192 mV | IR compensation on (BIF not configured) |
  | REG08 `TREG` | `0x3` | 120 °C thermal regulation |
  | REG03 `SYS_MIN` | `0x5` | 3.5 V minimum system voltage |

  The matching live evidence is the 4.340 V setting / 4.336 V readback logged
  in the private 2026-07-14 capture
  ([index](../2026-07-12-charger-power-recovery/results/live-charger-battery-recovery-20260714.txt));
  the policy's CV enum is `BATTERY_VOLT_04_340000_V` when
  `high_battery_voltage_support` is set
  ([`switch_charging.c` lines 94, 153, 231](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/power/mediatek/switch_charging.c#L231)).
  However, the public `charging_set_cv_voltage()` ignores the requested value
  and writes a fixed `0x24` to REG06 `VREG`, which is 4.416 V in the vendor's
  own `VBAT_CV_VTH` table (index 36) and in TI's 3.840 V + 16 mV encoding
  ([`charging_hw_bq25890.c` lines 347–365](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/charging_hw_bq25890.c#L347-L365),
  table at lines 58–71). The live capture's 4.336 V readback is code `0x1F`,
  not `0x24`, so either the running binary differs from this public source
  here too (F2) or the readback was the gauge voltage rather than the register;
  see H10. Either way the vendor CV policy is **not** a safe source for a
  mainline `ti,battery-regulation-voltage`; this record treats the cell as a
  4.35 V-class part and recommends 4.2 V for any first mainline test (H3).
  The public DT and header also disagree on high-voltage support (`<0>` in
  `mt6797.dtsi` line 1037 versus `#define HIGH_BATTERY_VOLTAGE_SUPPORT` in
  `mt_charging.h` line 77).
- **F12. Charge and input current by cable type (public DT, 0.01 mA units,
  `mt6797.dtsi` lines 1016–1025; header defaults at `mt_charging.h` lines
  38–47 agree except AC 2050 mA):** USB SDP 500 mA (70 mA unconfigured), CDP
  650 mA, DCP/AC 800 mA in DT (2050 mA header default), non-standard 500 mA,
  Apple 0.5/1.0/2.1 A → 500/650/800 mA. `select_charging_current()` applies
  them as both `ICHG` and `IINLIM`
  ([`switch_charging.c` lines 709–790](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/power/mediatek/switch_charging.c#L709-L790)),
  and PE+ raises them for a DCP (F8). Because F2 shows the live DTB differs
  from the public one, the live AC value is unknown; the logged 3000 mA shows
  it is not the public 800 mA.
- **F13. "Full" is software-decided from the charger status field.**
  `charging_get_charging_status()` reads REG0B `CHRG_STAT` (bits 4:3) and
  reports full when it equals `0x3` ("charge termination done"); the policy
  requires `FULL_CHECK_TIMES` consecutive readings
  ([`charging_hw_bq25890.c` lines 433–445](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/charging_hw_bq25890.c#L433-L445),
  [`switch_charging.c` `charging_full_check`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/power/mediatek/switch_charging.c)).
  With `EN_TERM = 0` (F11) the chip never reaches that state on its own, so the
  stock kernel also uses the gauge current (`charging_full_current = 100 mA`,
  DT line 1013) and voltage thresholds (`v_cc2topoff_thres = 4050`,
  `recharging_voltage = 4110` mV, DT lines 1011–1012) in `BAT_thread`.
- **F14. A `BATFET_DIS` workaround exists for the RT5735 SDA-low fault.**
  `battery_disable_batfet()` sets REG09[5]
  ([`bq25890.c` lines 1063–1070](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/bq25890.c#L1063-L1070)).
  This cuts the battery FET (system off if no adapter). It is a vendor
  recovery hook, relevant to the GPU-rail record, not a charging feature.

### Fuel gauge and battery measurement

- **F15. The fuel gauge is the MT6351's internal FGADC coulomb counter; there
  is no separate gauge chip.** `fgauge_initialization()` ungates
  `RG_FGADC_ANA_CK_PDN`/`RG_FGADC_DIG_CK_PDN` (`TOP_CKPDN_CON2` `0x0246` bits
  2–3), programs `FGADC_CON0` (`0x0CA4`) and `FG_OSR` (`FGADC_CON15`), and
  the readers use `FG_CAR_34_19`/`FG_CAR_18_03` (`FGADC_CON1`/`CON2`),
  `FG_CURRENT_OUT` (`FGADC_CON11`) and `FG_R_CURR` (`FGADC_CON25`)
  ([`battery_meter_hal.c` lines 298–366, 386–470](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/battery_meter_hal.c#L298-L366);
  header lines 721–754, 2076–2081, 8748–8873). The current LSB is
  `UNIT_FGCURRENT = 158.122 µA` for a 20 mΩ sense base
  ([line 36](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/battery_meter_hal.c#L36)),
  rescaled by `20 / r_fg_value` and then by `car_tune_value / 100`
  (lines 507–533). This resolves the roadmap's "inferred" note: the gauge is
  MT6351-internal by source, and `SOC_BY_HW_FG` is defined
  ([`mt_battery_meter.h` line 21](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_battery_meter.h#L21)).
- **F16. Board sense parameters (public DT, F2 caveat):** `r_fg_value = 10`
  mΩ, `car_tune_value = 118` (%), `cust_r_sense = 56`, `fg_meter_resistance =
  0`, `r_bat_sense = r_i_sense = 4`
  ([`mt6797.dtsi` lines 1039–1077](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L1039-L1077)).
  Header defaults differ (`R_FG_VALUE 10`, `CAR_TUNE_VALUE 101/115`,
  `FG_METER_RESISTANCE 75`, `mt_battery_meter.h` lines 40, 74–84). A 10 mΩ
  battery sense resistor with an 18 % software gain correction is the
  vendor's own model; it is not a measured fact about this unit.
- **F17. Battery voltage uses PMIC AUXADC channel 0 (`BATSNS`), 15-bit,
  ratio 3 (5.4 V full scale); charge current uses channel 1 (`ISENSE`), same
  scale.** Channel table and ratios at
  [`pmic_auxadc.c` lines 244–259, 487–494](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_auxadc.c#L244-L259);
  result registers `AUXADC_ADC_OUT_CH0_BY_AP` (`AUXADC_ADC23`, `0x0E2E`) and
  `CH1_BY_AP` (`AUXADC_ADC25`, `0x0E32`), request bits in `AUXADC_RQST0`
  (`0x0E96`) (header lines 793–818, 868, 9705–9719, 10062–10070). The low-battery
  interrupt thresholds use the same `× 4096 / 5400` scale
  ([`pmic_irq.c` lines 358–360](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_irq.c#L358-L360)).
  Boot-time OCV comes from `AUXADC_ADC_OUT_WAKEUP_PCHR`/`SWCHR`
  (`AUXADC_ADC20`/`ADC21`, `battery_meter_hal.c` lines 195–225).
- **F18. Battery temperature uses PMIC AUXADC channel 3 (`BATON`), 12-bit,
  ratio 2, with `BATON_TDET_EN`/`RG_BATON_EN` enabled, converted through a
  pull-up model and an NTC table.** `read_adc_v_bat_temp()` reads
  `PMIC_AUX_BATON_AP`
  ([`battery_meter_hal.c` lines 1150–1165](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/battery_meter_hal.c#L1150-L1165));
  `BattVoltToTemp()` computes `R = Rpull × V / (Vpull − V)` and looks up a
  17-point table
  ([`battery_meter.c` lines 1065–1088](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/power/mediatek/battery_meter.c#L1065-L1088)).
  The public DT gives `rbat_pull_up_r = 24000`, `rbat_pull_up_volt = 1800`
  (lines 1115–1116) and a 10 kΩ-at-25 °C NTC table (lines 1118–1128); the header defaults are
  61.9 kΩ at 2.8 V (`mt_battery_meter_table.h` lines 33–36). `FIXED_TBAT_25`
  is only defined under `CONFIG_MTK_DISABLE_POWER_ON_OFF_VOLTAGE_LIMITATION`,
  which the defconfig does not set, and the DT `fixed_tbat_25 = <0>`, so the
  stock kernel does measure temperature. Charging stops outside 0–50 °C
  (DT lines 1004–1007). Note the BQ25896 `TS` pin is **not** the vendor's
  temperature source; the charger HAL only sets JEITA register fields (F11).
- **F19. The battery profile is a four-temperature, 82-point OCV/capacity
  table with `q_max_pos_25 = 2707` mAh (public DT lines 1052 and 1129
  onward).** The roadmap's rule stands: these tables are the vendor's
  calibration and are not copied; their origin and redistribution rights are
  unestablished. Only the shape (OCV table per temperature, Qmax per
  temperature) is recorded here because it maps onto the mainline
  `monitored-battery` schema (`ocv-capacity-table-*`, `charge-full-design-microamp-hours`,
  `resistance-temp-table`; `battery.yaml` in the pinned tree).

### Mainline 7.1.3 and this repository

- **F20. Upstream `bq25890_charger` matches the silicon and most of F11.**
  It identifies PN 0 / rev 2 as BQ25896
  ([`bq25890_charger.c` lines 1279–1327](https://github.com/gregkh/linux/blob/v7.1.3/drivers/power/supply/bq25890_charger.c#L1279-L1327)),
  and its binding requires `interrupts`, `ti,battery-regulation-voltage`,
  `ti,charge-current`, `ti,termination-current`, `ti,precharge-current`,
  `ti,minimum-sys-voltage`, `ti,boost-voltage`, `ti,boost-max-current`
  ([`bq25890.yaml`](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/power/supply/bq25890.yaml)).
  Optional properties cover `ti,use-ilim-pin`, `ti,thermal-regulation-threshold`,
  `ti,ibatcomp-micro-ohms`, `ti,ibatcomp-clamp-microvolt`,
  `linux,skip-reset`, `linux,read-back-settings`, `linux,iinlim-percentage`,
  `linux,pump-express-vbus-max` and `linux,secondary-charger-name`
  (lines 1354–1432). The probe order is identity → properties → `hw_init`
  (chip reset unless `linux,skip-reset`, watchdog **off**, limits written, ADC
  continuous when online) → IRQ lookup (`interrupts` or a `bq25890_irq` GPIO)
  → optional USB2 PHY notifier → regulator and power-supply registration →
  threaded IRQ (lines 1450–1535). The local
  [IRQ preflight patch](../2026-09-12-bq25890-irq-preflight/README.md) moves
  the IRQ lookup before `hw_init`. Differences from the vendor: upstream
  disables the I2C watchdog (vendor enables 40 s), leaves hardware termination
  enabled (vendor disables it), reports USB type from REG0B `VBUS_STAT`
  (vendor disables charger-side detection), reads temperature from the TS pin
  percentage (vendor uses the PMIC NTC), and only drives Pump Express when
  `linux,pump-express-vbus-max` is set.
- **F21. Mainline has no MT6351 ADC, gauge, BC1.1 or charger-detect
  support.** The PMIC AUXADC driver covers MT6357/58/59/63/73 only
  ([`mt6359-auxadc.c` lines 889–893](https://github.com/gregkh/linux/blob/v7.1.3/drivers/iio/adc/mt6359-auxadc.c#L889-L893));
  `drivers/power/supply/Kconfig` has MT6360/MT6370 chargers but nothing for
  MT6351/MT6397-family gauges; `mt6397-core.c` has no MT6351 entry (the local
  [patch 0010](../../patches/v7.1.3/0010-mfd-mt6397-add-MT6351-core-and-interrupt-support.patch)
  adds it). The local `registers.h` for MT6351 defines 23 symbols: interrupt
  control/status and regulator registers, but none of `CHR_CON*`, `FGADC_CON*`,
  `AUXADC_*` or `TOP_CKPDN_CON2`.
- **F22. The current Gemini DT has no charger, gauge, host AUXADC or VBUS
  consumer.** I2C0 carries only the disabled FAN49101 child
  ([patch 0055](../../patches/v7.1.3/0055-regulator-add-FAN49101-buck-boost-driver-and-Gemini-node.patch));
  the MTU3 port is `dr_mode = "peripheral"` with no `vbus-supply`
  ([patch 0078](../../patches/v7.1.3/0078-arm64-dts-mediatek-describe-Gemini-MTU3-peripheral-wiring.patch));
  the host AUXADC (`0x11001000`) is disabled
  ([patch 0057](../../patches/v7.1.3/0057-thermal-mediatek-add-MT6797-AUXADC-support.patch)).
  The upstream `mt6797.dtsi` has neither a PMIC wrapper nor an AUXADC node.

## Part 2: hypotheses, ranked by value per device minute

Each hypothesis states what would confirm or refute it and the cheapest test.
"Gemian read" means one bounded, read-only inspection of the running stock
kernel over the known-good LAN SSH path, under the existing standing
authorization; "mainline boot" means a new reviewed experiment with its own
candidate, hypothesis and stop conditions. None is admitted by this record.

1. **H1. The BQ25896 `INT` pin is wired to an MT6797 EINT, but the stock
   kernel never uses it (F3).** If true, a mainline node can satisfy the
   binding's `interrupts` requirement with a real line; if false, the fallback
   is the PMIC `CHRDET` interrupt plus polling, which the upstream driver does
   not support without a small change (it requires an IRQ at probe). Test, in
   order: (a) Gemian read of `/proc/interrupts` and the live DTB's EINT/GPIO
   nodes for any unclaimed EINT near the charger (cheap, probably inconclusive
   because F3 says nothing claims it); (b) the owner's schematic-class reference
   documents (X20 schematic is a different board; use it only for the TI
   reference wiring); (c) a mainline boot with the charger node carrying a
   candidate EINT and `linux,skip-reset`, logging whether the threaded IRQ
   fires on cable insertion. Confidence: medium that a line exists (TI
   reference designs always route `INT`), low on which EINT.
2. **H2. The MT6351 `CHRDET` interrupt (index 46 in patch 0010) will fire on
   cable insertion under mainline once the MFD IRQ domain is live, with no
   further PMIC configuration (F4, F5).** Test: a mainline boot with a trivial
   consumer (or `/proc/interrupts` on the existing MT6351 irqchip) counting
   `CHRDET` and `VBATON_UNDET` transitions across one attended cable change.
   This is the cheapest decision-changing device test in this record and it
   also validates the PMIC IRQ path for the roadmap's PMIC step. Confidence:
   high; the vendor enables it with nothing but the mask bit.
3. **H3. Conservative mainline limits can be taken from F11 and run the
   charger below the vendor envelope: VREG 4.352 V (or 4.2 V for a first
   test), ICHG 512 mA, IINLIM 500 mA, IPRECHG 128 mA, ITERM 128 mA, SYS_MIN
   3.5 V, BOOSTV 4.998 V, BOOSTI 1.3 A, `ti,use-ilim-pin`, no Pump Express.**
   The vendor's own first-step configuration (512 mA, 4.5 V VINDPM) is the
   source; 500 mA input keeps any adapter type safe without BC1.1. Test: a
   mainline boot that probes the charger with `linux,skip-reset` and
   `linux,read-back-settings` first (keeping the loader's register state),
   reads `status`, `online`, `voltage_now`, `current_now` and `input_current_limit`
   while unplugged and plugged, and only then compares with the vendor state.
   Confidence: high for the values, medium for whether `skip-reset` is needed
   (unknown whether LK leaves the watchdog running; if it does, upstream's
   watchdog-off write at init is the right first action anyway).
4. **H4. The BQ25896's own ADC and `VBUS_STAT` can replace the PMIC VCDT
   divider and BC1.1 for a first mainline charger (F6, F9, F20).** Enabling
   REG02 `AUTO_DPDM_EN` (upstream does this implicitly through `VBUS_STAT`
   reporting) would classify SDP/CDP/DCP on the charger itself. Risk: the
   vendor disabled it deliberately, possibly because the USB PHY owns D+/D-
   during enumeration. Test: in the H3 boot, read `usb_type` and
   `input_current_limit` with the gadget stack idle, then with the gadget
   enumerated, and record whether enumeration is disturbed. Confidence:
   medium.
5. **H5. A minimal mainline gauge is feasible without any vendor table: a
   PMIC AUXADC driver for MT6351 channels 0/1/2/3 (F17, F18) plus the FGADC
   current/charge counter (F15), exposed as IIO, with `simple-battery`
   properties providing only `voltage-min/max-design` and a rough OCV table
   later.** The driver shape already exists upstream for MT6357–MT6373; the
   MT6351 register offsets differ (`AUXADC_RQST0 0x0E96`, `ADC23/25` for the
   AP-owned channels, `FGADC_CON0 0x0CA4`, clock gates in `TOP_CKPDN_CON2`).
   Test: offline, write the channel/ratio table from F17/F18 and compile; on
   device, a mainline boot reading `BATSNS` and comparing with the charger
   ADC `voltage_now` (two independent paths must agree within tens of mV),
   and reading `BATON` to check the pull-up model gives roughly room
   temperature. Confidence: high for voltage, medium for temperature (the
   pull-up values differ between DT and header, F18), low for the coulomb
   counter calibration (`car_tune 118 %`, F16).
6. **H6. `AC online` in Gemian means a DCP was attached, and the Gemini's
   bundled adapter is a Pump Express capable DCP (F7, F8).** Test: a Gemian
   read of the battery log while the bundled adapter is attached, looking for
   the PE+ messages and `chr_type=4`; also useful to know what VBUS the
   adapter is sitting at before any mainline charger test (F9 gives the read
   path through `/sys/class/power_supply`). Confidence: high.
7. **H7. The live DTB's `bat_meter` node differs from the public one in at
   least `ac_charger_current` and probably the gauge/temperature constants
   (F2, F12, F16, F18).** Test: a Gemian read of the live flattened DT
   (`/proc/device-tree/.../bat_metter` and the `battery` node) under the same
   identity checks as earlier captures; this is read-only and settles which
   numbers in Part 1 carry the F2 caveat. Confidence: high that it differs.
8. **H8. LK (the retained loader) leaves the charger configured and the 40 s
   watchdog running at kernel entry, so a mainline probe that waits too long
   before touching the chip sees a watchdog reset to defaults (F11, F20).**
   Not harmful (defaults are conservative) but it changes which `read-back`
   values a first boot observes. Test: in the H3 boot, dump REG00–REG14 as
   the first I2C action and compare with the F11 table. Confidence: medium.
9. **H9. The RT5735 `BATFET_DIS` workaround (F14) is irrelevant to mainline
   unless the GPU regulator is enabled.** Keep it out of scope; revisit only
   with the RT5735 record. No test now.

10. **H10. The running Gemian charger binary differs from the public
    `charging_set_cv_voltage()` and holds `VREG` at `0x1F` (4.336 V), not the
    public source's fixed `0x24` (4.416 V) (F11).** Test: a Gemian read of the
    kernel log for the periodic vendor register dump (`[bq25890 reg@]` lines
    include REG06), with the usual identity checks; no register access is
    needed. If the dump shows `0x24`, the stock kernel is over-charging a
    4.35 V cell and the owner should know before any further long charge
    sessions. Confidence: medium that the binary differs (F2 precedent).

## Consequences for the roadmap (no changes applied here)

- The roadmap's three unknowns resolve as: charger IRQ line not recorded by
  the vendor (H1/H2 decide the mainline strategy); conservative limits
  available from F11 (H3); gauge is MT6351-internal FGADC plus AUXADC (F15,
  H5), and it needs a new small driver because mainline has none (F21).
- Charging and cable detection are coupled to the MT6351 MFD/IRQ foundation
  more tightly than the earlier design assumed: `CHRDET`, `BATON`, `VCDT` and
  the FGADC all sit behind the PMIC wrapper. The PMIC step before the battery
  step in the After-Wi-Fi order is confirmed as the right dependency.
- Nothing here authorizes Pump Express, OTG boost, or any VBUS role change on
  mainline. A first mainline charger boot should be read-only in intent
  (`linux,skip-reset`, `read-back-settings`, 500 mA input limit) and should
  precede any write of VREG above 4.2 V.

## Validation

Documentation-only change: `./scripts/check-repository` and link checks apply;
no kernel build, DT check or device action was performed. Line numbers were
taken from the exact fetched files recorded in `source-inputs.json`.

## Live passive baseline successor (2026-10-04)

The [identity-checked log/DT subset](../2026-10-04-gemian-session-a/README.md)
records logged selector `0x1f`, request 4.340 V and selection 4.336 V, without
a REG06 dump. `/soc/bat_metter` has `high_battery_voltage_support=0` and
`ac_charger_current=80000` (800 mA in the vendor's units). H7 now has an
attributable AC-current difference; other table differences remain unreviewed.
H10 remains open: selected-value logs do not prove hardware readback. Inspect
the retained running setter binary before asserting either the public fixed
`0x24` write or physical `0x1f` state. The current roadmap's separate read-only
C2a and programmed-limit C2b stages supersede the earlier H3/roadmap-consequence
suggestion to combine `skip-reset`/`read-back-settings` with DT limits.

The [matched-primary-boot binary audit](../2026-10-04-gemian-session-a/CHARGER_CV_BINARY.md)
resolves the log ambiguity: the computed `0x1f` value is printed before both
branches call the setter with fixed `0x24`, ignoring its result. The apparent
log/source discrepancy is not evidence of a different setter. H10's physical
REG06 state remains open; nominal `0x24` is 4.416 V in the binary table.

## Driver write review (2026-10-05)

The [driver review](DRIVER_REVIEW.md) lists every register write the pinned
`bq25890` driver can make. The unmodified driver cannot meet the C2b gate:
neither probe path keeps charging off until limits are written, the input
current limit is never set at probe, and nothing is read back. It proposes one
skip-reset driver change that writes limits with charging disabled, verifies
them, and only then enables charging. The driver also refuses to probe without
an interrupt, and the charger INT pin's wiring is unknown; that gates any C2b
node independently of the driver change.
