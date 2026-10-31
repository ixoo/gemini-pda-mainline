# MT6797 / MT6351 thermal facts from the vendor datasheets

Offline documentary extraction. No device access, no kernel or firmware change.
Prepared for the thermal-management knowledge base.

## Sources and identity

| Ref | Document | Pages | SHA-256 |
| --- | --- | --- | --- |
| FS | `sources/collection/MT6797_Functional_Specification_V1_0.pdf` | 291 | `8d079e9447765b4a0ce68cb94241d686c3537546750d11cd4a6a92a80b69944e` |
| FS-owner | `sources/owner-supplied/MT6797.pdf` | 291 | `89a2929aed35f31d00e23be0ba8758980604d6d0ecdee6e8a28f1dc2711cb573` |
| RT1 | `sources/collection/MT6797_Register_Table_Part_1.pdf` | 1637 | `e8ef503a32a8bb318a000fe6727d2bcdaa3557992a0ffed344e9de37acc2caff` |
| RT2 | `sources/collection/MT6797_Register_Table_Part_2.pdf` | 1460 | `e31066d16d0e94fdd5c2a7f8c306ad6a3b5516f31482f54b59286b62393d2c3a` |
| PMIC | `sources/owner-supplied/MT6351_PMIC_Data_Sheet_V12-Final.pdf` | 322 | `05bd18e2ff98d9c887a97759d50343080ad0202d06fbff9ce308568cd019508a` |
| WCN | `sources/owner-supplied/MT6631_External_Data_Sheet_v02a_20160421.pdf` | 42 | `27ba4d5e44a30fcf87f4d03ca4a4313cc818d6774e826c4d11bcc75f1a63ea41` |

`FS-owner` and `FS` are content-equivalent: `pdftotext -layout` output is
byte-identical after whitespace/form-feed normalisation (291 pages each). The
collection copy was used for citations.

Method: `pdftotext -layout`, split on form feeds so every statement below is
tied to a one-based **PDF page**. Printed page numbers equal PDF page numbers in
all the MediaTek documents used here (footers read `Page N of 291/1637/1460/322/42`).

Labels: **[doc]** = vendor-stated in the document. **[inf]** = my inference,
not stated.

---

## 1. MT6797 thermal sensing architecture

### What is documented

| Fact | Where |
| --- | --- |
| The analog baseband feature list contains a bare entry "Temperature sensor". Nothing else on the page. | FS p.108 |
| AUXADC "is used to identify the plugged peripheral and perform temperature measurement"; 16 input channels. | FS p.188 |
| "Besides, there are several embedded temperature sensors. The module accepts signals from module of thermal controller to measure the temperature of the embedded sensors. The measurement result is able to be read in the command registers in the module of thermal controller." | FS p.188 |
| AUXADC feature list item 3: "Temperature measurement". | FS p.189, Table 5-4 |
| Only immediate conversion mode is offered: set `IMMn` in `AUXADC_CON1`, one sample per set/clear cycle; `AUTOSETn` in `AUXADC_CON0` re-triggers a channel when its data register is read. | FS p.188 |
| AUXADC channel map: CH0-CH4 external `AUX_IN0..4`, CH5-CH9 `NA`, **CH10 and CH11 "Internal use"**, CH12-CH15 `NA`. | FS p.115-116, Table 2-36 |
| `AVDD18_AP` is the 1.8 V supply "for AuxADC, TSENSE". | FS p.82 (abs. max), p.84 (recommended) |
| Thermal controller can assert a system reset: TOPRGU block diagram shows a "Thermal" input into the watchdog/reset mixer, alongside `PMIC RESET_B`. | FS p.154, Figure 4-5 |

### Sensor count, identity, accuracy, conversion

- **Not documented.** The FS never states how many on-die sensors exist, which
  block each one monitors, or any per-sensor accuracy, range or resolution.
  There is no occurrence of `TS_MCU`, `TS_ABB`, `VTS`, `ADC_GE_T`, `ADC_OE_T`,
  `DEGC`, `O_SLOPE` anywhere in FS, RT1 or RT2 (case-insensitive full-text
  search of all extracted pages).
- **[inf]** The two AUXADC channels marked "Internal use" (CH10, CH11, FS p.115-116)
  are the plausible AP-side temperature inputs, but the document does not say
  so, and it does not say what they measure. A four-`TS_MCU` + one-`TS_ABB`
  topology cannot be sourced from these documents.
- No sampling period, averaging, filtering or sensor polling rate is specified
  for the thermal path. Only the generic AUXADC timing exists (below).

### AUXADC electrical limits (the measurement engine behind the sensors)

| Parameter | Value | Where |
| --- | --- | --- |
| Resolution | 12 bit | FS p.116, Table 2-37 |
| Clock rate | 3.25 MHz | FS p.116 |
| Sampling rate | 3.25/(N+8) MSPS (about 0.1625 MSPS at N=12) | FS p.116 |
| Input swing | 0.05 - 1.45 V | FS p.116 |
| Accuracy | plus/minus 10 mV | FS p.116 |
| DNL / INL | plus/minus 1.0 / 2.0 LSB | FS p.116 |
| Operating temperature of the ADC block | -20 to 80 °C | FS p.116 |
| Raw data register | `AUXADC_DAT[n]`: bit 12 `RDYn` ("cleared after the register is read"), bits 11:0 `DATn` | RT1 p.1079 (map), p.1084 (fields) |

Documentary inconsistencies to keep in mind (do not build a contract on them):

- FS p.188 says the time-trigger mode "is removed now", then later on the same
  page describes timer-triggered sampling.
- The FS 5.8.3 block diagram on p.190 labels an "8-bit" SAR, while Table 2-37
  (p.116) and `AUXADC_DAT[11:0]` (RT1 p.1084) are 12-bit.
- FS p.115 states 12-bit for the AUXADC block while p.190 draws 8-bit stages.

---

## 2. "THERM_CTRL" register map

### Result: the register bank is absent from both register-table parts

- RT1 table of contents (p.2) contains chapters 1 (MCU/bus), 2 (clock and power)
  and 3 (peripherals, 3.1-3.18). There is **no thermal-controller chapter and no
  eFuse chapter**.
- RT2 (p.2) contains only chapter 4 "Multimedia" (4.1-4.10).
- The module-name/base-address list of RT1 has no thermal module; `0x1100Bxxx`
  (the usual MT6797 thermal base) occurs **zero** times in RT1 and RT2.
- `THERM_CTRL` appears exactly three times in RT1, all as a clock-gate target.
  `therm` appears nowhere in RT2.
- Consequence: no base address, no per-bank control/status register, no raw
  data register, no mux/selector, no threshold/interrupt register and no reset
  bit for the thermal controller can be cited from these documents. The FS
  defers measurement results to "command registers in the module of thermal
  controller" (p.188) but no document in the archive defines that module.

### What the documents *do* say about the thermal controller

| Address / field | Meaning (verbatim or near-verbatim) | Where |
| --- | --- | --- |
| `0x10001080` `MODULE_SW_CG_0_SET`, bit 10 `therm_cg_set` | "Sets up THERM_CTRL SWCG", `0: Enable / 1: Disable` | RT1 p.114-115 |
| `0x10001084` `MODULE_SW_CG_0_CLR`, bit 10 `therm_cg_clr` | "Clears THERM_CTRL SWCG", same polarity | RT1 p.117 |
| `0x10001090` `MODULE_SW_CG_0_STA`, bit 10 `therm_cg_sta` | "THERM_CTRL SWCG status", same polarity | RT1 p.121-122 |
| `0x10001120` `INFRA_GLOBALCON_RST0_SET`, bit 0 `therm_ctrl_swrst_set` | "Enables thermal control software reset", `0: Normal / 1: Enable reset` | RT1 p.135-136 |
| `0x10001124` `INFRA_GLOBALCON_RST0_CLR`, bit 0 `therm_ctrl_swrst_clr` | "Disables thermal control software reset" | RT1 p.137 |
| `0x10001128` `INFRA_GLOBALCON_RST0_STA`, bit 0 `therm_ctrl_swrst_sta` | Software-reset status | RT1 p.137 |
| `0x1000700C` `TOPRGU.WDT_STA`, bit 18 `thermal_rst` | "Indicates thermal controller reset is asserted" (read-only, not reset by WDT) | RT1 p.593 |
| `0x10007030` `TOPRGU.WDT_REQ_MODE`, bit 18 `thermal_ctl_en` | "Enables thermal controller reset"; register unlocked by writing `0x33` to `unlock_key[31:24]` | RT1 p.596 |
| `0x10007034` `TOPRGU.WDT_REQ_IRQ_EN`, bit 18 `thermal_ctl_irq` | "Triggers IRQ instead of reset when thermal controller reset is enabled", `0: Trigger reset / 1: Trigger IRQ` | RT1 p.597 |
| `0x10007504` `TOPRGU.DEBUG_1_REG`, bit 18 `shadow_thermal_rst` | Shadow of the thermal reset status | RT1 p.602 |
| `0x1000750C` `TOPRGU.DEBUG_3_REG`, bit 18 `shadow_thermal_ctl_irq`, bit 0 `shadow_thermal_en` | Shadow reset/IRQ-enable state | RT1 p.604 |

**[doc]** This is a real hardware-protection path: the thermal controller can
request a whole-chip reset through TOPRGU, and the request can be converted to
an IRQ by software (p.596-597). Nothing states the temperature at which the
controller raises it.

### SW-visible measurement path that *is* documented

AUXADC (`Module name: AUXADC Base address: (+11001000h)`, RT1 p.1079):

| Offset | Register | Relevant fields |
| --- | --- | --- |
| `0x11001000` | `AUXADC_CON0` | `AUTOSET0..15` (bits 0-15), auto re-sample on data read (RT1 p.1080-1081) |
| `0x11001004` | `AUXADC_CON1` | `IMM0..15` (bits 0-15), channel select / one-shot trigger (RT1 p.1081) |
| `0x11001008` / `0x1100100C` | `AUXADC_CON1_SET` / `_CLR` | set/clear aliases of `CON1` (RT1 p.1079) |
| `0x11001010` | `AUXADC_CON2` | bit 11 `PUWAIT_EN` (power warm-up, about 56 ADC clocks), bit 7 `SOFT_RST`, bit 0 `ADC_STA` (RT1 p.1084) |
| `0x11001014 + 4n` (`n`=0-15), through `0x11001050` | `AUXADC_DAT[n]` | bit 12 `RDYn`, bits 11:0 `DATn` (RT1 p.1079, p.1084) |
| `0x11001084` | `AUXADC_DET_VOLT` | background-detection threshold (RT1 p.1079) |
| `0x11001088` | `AUXADC_DET_SEL` | background-detection channel select (RT1 p.1079) |
| `0x1100108C` / `0x11001090` | `AUXADC_DET_PERIOD` / `AUXADC_DET_DEBT` | detection period and debounce (RT1 p.1079) |
| `0x11001094` | `AUXADC_MISC` | misc control (RT1 p.1079) |

Modem thermal-data path through the PMIC wrapper (`Module name: PMIC_WRAP
Base address: (+1000D000h)`, RT1 p.605):

| Offset | Register | Meaning |
| --- | --- | --- |
| `0x1000D1DC` | `ADC_CMD_ADDR` | "AuxADC command register address" |
| `0x1000D1E0` | `PWRAP_ADC_CMD` | "Command to AuxADC" |
| `0x1000D1E4` | `ADC_RDATA_ADDR` | "Address of thermal data [15:0] register in AuxADC" |
| `0x1000D1F4` | `MD_ADC_RDATA_ADDR_LATEST` | "Address of the latest thermal data [15:0] register in AuxADC" |
| `0x1000D1F8` | `MD_ADC_RDATA_ADDR_WP` | address of the latest buffer thermal-data pointer |
| `0x1000D1FC`-`0x1000D278` | `MD_ADC_RDATA_ADDR0..31` | 32-entry buffer of thermal data addresses |
| `0x1000D280` | `MD_ADC_STA0` | bits 31:16 `PWRAP_MD_ADC_TEMP_DATA` (thermal sample of the modem path) |

Citations: RT1 p.608 (register map), p.662 (`MD_ADC_STA0` and `PWRAP_MD_ADC_TEMP_DATA`).

Note the `therm`-adjacent clock-gate plumbing for this path: `MODEM_TEMP_SHARE`
gate, `0x100010A8` bit 28 `modem_temp_share_cg_set` and the matching clear and
status bits (RT1 p.109, p.127, p.129, p.132).

Analog trim register that is *not* the thermal calibration:
`0x10001B10 PLL_AUXADC_CON0`, bits 3:0 `auxadc_cali`, bit 4 `auxadc_fs`
(RT1 p.198-199). No description of what the trim compensates.

---

## 3. Thermal calibration / eFuse

**Not documented anywhere in the archive's MT6797 documents.** This is a hard
negative, verified by exhaustive search:

| Requested item | Status in FS / RT1 / RT2 |
| --- | --- |
| `ADC_GE_T`, `ADC_OE_T` | absent |
| `O_VTSMCU1`..`O_VTSMCU4`, `O_VTSABB` | absent |
| `DEGC_cali`, `ADC_CALI_EN_T` | absent |
| `O_SLOPE`, `O_SLOPE_SIGN`, thermal `ID` | absent |
| eFuse word `0x10206180` / `0x10206184` / `0x10206188` | absent; RT1 contains no `0x10206xxx` address at all. The `0x1020` space it covers is limited to `0x10200000-0x102043xx`, `0x1020D0xx`, plus (in RT2) the MIPI blocks at `0x10215000`, `0x10217000`, `0x10218000`, `0x1021E000` |
| eFuse chapter or OTP chapter | none; RT1 TOC p.2 lists only chapters 1-3; RT2 p.2 only chapter 4 |
| "efuse"/"OTP" in the FS | only in the WIFI-HIF CIS description, FS p.244-245 (unrelated) |

Therefore the addresses, bit positions and field meanings for the thermal
calibration words **cannot be cited to these documents**. Any such mapping in
the knowledge base must be attributed to its real source (e.g. vendor kernel
headers), not to the datasheet or register table.

What the documents do say about an *analog* trim only: `auxadc_cali[3:0]` at
`0x10001B10`, RT1 p.198-199, with no stated purpose or encoding.

---

## 4. Temperature conversion equation / calibration procedure

**None is documented.**

- FS: no occurrence of "slope", "intercept", "room temperature", "degC",
  "DEGC" in a thermal sense. The three "calibrat*" hits (FS p.17, 108, 113) are
  RF/analog calibration or the DETADC description, not temperature conversion.
- FS p.188-191 gives no formula, no reference temperature and no procedure for
  turning an AUXADC code into degrees Celsius.
- RT1/RT2: no thermal conversion register or constant.
- PMIC: no die-temperature conversion equation. (The only numeric formula on
  the pages near the thermal text, PMIC p.131, is the BUCK_VPA output-voltage
  equation and is unrelated.)

Consequence for the knowledge base: with these documents alone, raw thermal
codes are **uncalibrated integers**. A slope/intercept (or an equivalent
two-point calibration) must come from another source; a conversion function
cannot be justified as "documented".

---

## 5. MT6351 PMIC thermal behaviour

### Die temperature and shutdown

| Fact | Where |
| --- | --- |
| "Over-current and thermal overload protection" in the feature list. | PMIC p.6 |
| Thermal Shut-down: "PMIC shut-down threshold 150 degree"; "Shut-down release threshold 110 degree". | PMIC p.18, Table 2-4 (General electrical specifications) |
| **[inf]** 40 °C hysteresis between the 150 °C trip and the 110 °C release; the table gives no hysteresis figure and no accuracy/tolerance. | derived from p.18 |
| Thermal regulation interrupt: `THR_H` asserted when "PMIC die temperature is over thermal regulation high threshold (e.g. 125 °C)", `THR_L` when the die falls back "under thermal regulation low threshold (e.g. 110 °C)"; "The thermal regulation high/low threshold is adjustable." | PMIC p.59 |
| Power-on is refused while the PMIC is "in the thermal condition" (alongside UVLO). | PMIC p.37 |
| Thermal auto power-down: `THR_HWPDN_EN` bit 5 "Enables theraml [thermal] auto power-down. Powers down some PMU modules." | PMIC p.85 |
| Thermal detect/shutdown disable: `THR_DET_DIS` bit 0, "Disables thermal detection function and thermal shut-down", `0: Normal mode / 1: Disable thermal detection`. | PMIC p.85 |
| Vibrator thermal shutdown enable: `RG_VIBR_THER_SDN_EN` bit 4 of `LDO_VIBR_CON0` (`0x0A3A`). | PMIC p.165 |

Caveat: on p.85 the register header for the `THR_*` fields falls on the page
break and is not printed; the p.68 address summary lists `0000`, `0018`,
`001A`, `002E`... but not the intervening offset, so **no reliable address can
be assigned** to `THR_HWPDN_EN`/`THR_DET_DIS` from this PDF. Cite them by name
only.

### Thermal interrupts

| Signal | Enable | Status | Type | Debounce | Where |
| --- | --- | --- | --- | --- | --- |
| `THR_H` (AUXADC group) | `RG_INT_EN_THR_H` `0x02C2` bit 4 | `RG_INT_STATUS_THR_H` `0x02E0` bit 4 | edge (rising) | 50 ms | PMIC p.60 |
| `THR_L` (AUXADC group) | `RG_INT_EN_THR_L` `0x02C2` bit 5 | `RG_INT_STATUS_THR_L` `0x02E0` bit 5 | edge (rising) | 50 ms | PMIC p.60 |
| Battery NTC JEITA: `JEITA_HOT/WARM/COOL/COLD` | `0x02CE` bits 0-3 | `0x02E4` bits 0-3 | level | - | PMIC p.62 |

JEITA events are battery-pack temperature, not PMIC die temperature
(**[inf]** from the signal names and the "in AUXADC" source column).

### AUXADC thermal channel usage

| Fact | Where |
| --- | --- |
| "AUXADC: 15 bits of analog to digital converter for thermal/accessory detection monitor and measurement". | PMIC p.37 |
| "The auxiliary ADC ... Analog multiplexer: Selects signal from one of the input channels. Real-world messages to be monitored, e.g. temperature, should be transferred to the voltage domain." "15-bit A/D converter". | PMIC p.53 |
| Channel table: CH0 BATSNS, CH1 ISENSE, CH2 VCDT, CH3 BATON, CH5 ACCDET, CH7 AUXADC_VIN, "Others: Internal use". | PMIC p.53, Table 3-4 |
| Resolution: 15 bit on `AUXADC_VIN`, 12 bit on the others; sample rate 100 kHz; input bandwidth 50 kHz; offset and gain error plus/minus 1 % FS; INL/DNL plus/minus 2 LSB. | PMIC p.34, Table 2-15 |
| Result registers `AUXADC_ADC0..` at `0x0E00 + 2n`; bit 15 `AUXADC_ADC_RDY_CHn`, bits 14:0 `AUXADC_ADC_OUT_CHn`. | PMIC p.266 |
| Dedicated thermal result: `0x0E1A` `AUXADC_ADC13`, `AUXADC_ADC_RDY_THR_HW` (bit 15) and `AUXADC_ADC_OUT_THR_HW` (bits 11:0), described as "AUXADC channel 4 output data". | PMIC p.270-271 |
| Busy/status: `0x0E92` `AUXADC_STA1` bit 14 `AUXADC_ADC_BUSY_IN_THR_HW`, bit 15 `..._IN_THR_MD`. | PMIC p.293 |

The PMIC therefore exposes two thermal channels, `THR_HW` (hardware thermal
protection) and `THR_MD` (modem thermal path), each with its own conversion
result register.

Documentary inconsistency: `0x0E1A` is labelled "ADC Register 13" but its
description says "channel 4"; the field diagram shows 12 data bits while the
generic channel registers carry 15. Treat the thermal channel's scaling as
undocumented.

Other thermal-adjacent PMIC facts:
- Operating range (PMIC p.6): -20 to +85 °C.
- Absolute maximum free-air temperature -40 to +85 °C; storage -65 to +150 °C
  (PMIC p.13, Table 2-1).
- `theta_JA` = 36.42 °C/W "In free air", "mounted on a 4-metal-layer PCB and
  modeled per JEDEC51-9 condition" (PMIC p.13, section 2.2).

---

## 6. Thermal operating specifications

### MT6797

| Symbol | Parameter | Value | Where |
| --- | --- | --- | --- |
| - | Max. operating junction temperature | 125 °C | FS p.118, Table 2-39 |
| - | "Package thermal resistances in nature convection" | 22.5 °C/W | FS p.118, Table 2-39 |

Notes: only a maximum junction temperature is given - no minimum, no separate
`theta_JA`/`theta_JB`/`theta_JC`, no power dissipation budget, and the table's
symbol column is empty. Package: MWDPOP 14.0 x 14.0 mm, 950 balls, 0.4 mm pitch
(FS p.118, Figure 2-29).
Analog/interface blocks carry their own `T Operating temperature` of -20 to
80 °C (FS p.111, p.112, p.113, p.114, p.116, p.117); one table gives -20 to 85 °C
(FS p.115, APC-DAC). These are block-level test conditions, not package limits.

### MT6351

| Parameter | Value | Where |
| --- | --- | --- |
| Ambient temperature `TA` | -20 to 85 °C | PMIC p.17, Table 2-3 |
| Junction temperature `TJ` | -20 to 125 °C | PMIC p.17, Table 2-3 |
| Free-air temperature (absolute max) | -40 to 85 °C | PMIC p.13, Table 2-1 |
| Storage temperature | -65 to 150 °C | PMIC p.13, Table 2-1 |
| `theta_JA` | 36.42 °C/W (4-layer PCB, JEDEC51-9) | PMIC p.13, section 2.2 |
| Thermal shutdown / release | 150 °C / 110 °C | PMIC p.18, Table 2-4 |

Conflict to record: the overview text says the operating temperature range is
"-20 to +85 °C" (p.6) while Table 2-3 allows `TJ` up to 125 °C (p.17); the two
are consistent only if p.6 means ambient.

### MT6631 (Wi-Fi/BT/FM/GPS companion - relevant only for its own die)

| Parameter | Value | Where |
| --- | --- | --- |
| Thermal ADC: "low-speed ADC converts the output of thermal sensor to 8-cycle-average or 16-cycle-average ADC code"; "temperature coverage range is between -40 °C and 120 °C"; used for "PA/TX gain switching". | WCN p.16, section 3.6.2 |
| Absolute max: `TSTG` -60 to +120 °C, `TA` -40 to +85 °C. | WCN p.12, Table 3-1 |
| Recommended: commercial `Tj` 0/25/115 °C, industry `Tj` -20/25/125 °C, `Ta` -40/25/85 °C, `Tstg` -60/25/150 °C. | WCN p.12, Table 3-2 |

MT6631's thermal sensor is local to the connectivity die and no document here
connects it to the AP thermal controller (**[inf]**: no wiring statement exists
either way).

---

## 7. Gaps that matter for a thermal-management knowledge base

1. **No thermal-controller register map.** Base address, bank layout, mux,
   raw-data, threshold and interrupt registers for `THERM_CTRL` are in neither
   register-table part. Only its clock gate, software reset and its TOPRGU
   reset/IRQ request exist (RT1 p.114-137, p.593-604).
2. **No sensor inventory.** "Several embedded temperature sensors" (FS p.188)
   is the entire statement; `TS_MCU1..4`/`TS_ABB` are not named, located or
   characterised.
3. **No calibration data description.** eFuse words including `0x10206180`
   and the `ADC_GE_T`/`ADC_OE_T`/`O_VTS*`/`DEGC_cali`/`O_SLOPE` fields are
   absent from all three MT6797 documents.
4. **No conversion equation.** Temperature cannot be derived from a documented
   formula; only AUXADC electrical accuracy (plus/minus 10 mV, FS p.116) bounds
   the measurement itself.
5. **No thermal sample rate or filtering** for the on-die sensors. The AUXADC
   `DET_PERIOD`/`DET_DEBT` registers exist (RT1 p.1079) but are described only
   as background voltage detection, not as thermal sampling.
6. **PMIC threshold set-points are "adjustable" (p.59) but the set-point
   registers are not identified**; only the 150 °C/110 °C hardware shutdown
   (p.18) and the 125 °C/110 °C example ("e.g.") for `THR_H`/`THR_L` (p.59).
