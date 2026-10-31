# MT6351 PMIC auxiliary ADC

Scope: the auxiliary ADC inside the MT6351 PMIC on the named MT6797X Gemini
PDA. This document covers the block, its register interface, channel scaling,
consumers in the working vendor stack, the modem sharing path, and what upstream
Linux models. It is a source, firmware and document study; no runtime claim is
made. Evidence chronology is in the
[PMIC ADC experiment](../../experiments/2026-10-31-mt6351-pmic-adc/README.md).

## 1. Block and access model

The PMIC contains a 15-bit successive-approximation auxiliary ADC behind an
analog multiplexer (MT6351 datasheet section 3.2.9). It serves battery voltage
and temperature, charger voltage and battery-on detection, accessory detection,
the PMIC's own die temperature, and a shared path for the modem.

The PMIC is not directly mapped. The AP reaches these registers only through the
PMIC wrapper over the SPI link; the SCP and the modem use the same wrapper (or
the wrapper's modem side). A conversion is a three-step transaction:

1. set the channel bit in `AUXADC_RQST0` through its `_SET` alias;
2. poll the result register until bit 15 (ready) reads 1;
3. read the channel's data bits.

The vendor immediate-mode helper is `PMIC_IMM_GetOneChannelValue()`
(`drivers/misc/mediatek/power/mt6797/pmic_auxadc.c:235`); it takes a mutex,
forces the ADC clock on, issues the request, polls with a bounded timeout and
scales the result.

## 2. Register window

PMIC register offsets, all 16-bit unless noted (`upmu_hw.h` definitions in
`drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/`):

| Range | Registers | Purpose |
| --- | --- | --- |
| `0x0E00`-`0x0E4E` | `AUXADC_ADC0`..`ADC39` | conversion results, ready bit 15 |
| `0x0E50`-`0x0E8E` | `AUXADC_BUF0`..`BUF31` | 32-entry modem share ring |
| `0x0E90`-`0x0E94` | `AUXADC_STA0`..`STA2` | busy/status (including THR_HW and THR_MD) |
| `0x0E96`-`0x0EA0` | `AUXADC_RQST0/1` and `_SET`/`_CLR` | channel request aliases |
| `0x0EA2`-`0x0EC6` | `AUXADC_CON0`..`CON16` | per-channel configuration |
| `0x0EC8` | `AUXADC_AUTORPT0` | auto-repeat control |
| `0x0ECA`-`0x0ED6` | `AUXADC_LBAT0`..`LBAT6` | low-battery detect |
| `0x0F18` | `AUXADC_MDBG_1` | modem ring write pointer |
| `0x0E1A` | `AUXADC_ADC13` | `THR_HW` thermal result (12-bit) |

Every result register carries the same layout: bit 15 ready, data in the lower
bits (15-bit channels use bits 14:0). The immediate path uses direct channel
registers for most channels and dedicated `_BY_AP` aliases for channels 0, 1
and 7 (for example channel 0's result is `ADC23`).

The MT6797 wrapper side is documented at `0x1000D1DC`-`0x1000D278`
(register-table part 1, page 608): `ADC_CMD_ADDR` `0x1DC`, `PWRAP_ADC_CMD`
`0x1E0`, `ADC_RDATA_ADDR` `0x1E4`, `MD_ADC_RDATA_ADDR_LATEST` `0x1F4`,
`MD_ADC_RDATA_ADDR_WP` `0x1F8`, then the 32 `MD_ADC_RDATA_ADDRn` entries from
`0x1FC`. The vendor header agrees (`pmic_wrap/mt6797/pwrap_hal.h:308-318`); a
second header (`pwrap_hal_d2.h`) carries different offsets and is not the one
this build includes.

## 3. Channels and scaling

The vendor helper applies one of three integer scalings with a 1800 mV
reference: 15-bit channels divide by 32768, 12-bit channels by 4096, and channel
0 and 1 additionally multiply by 3 for their external divider
(`pmic_auxadc.c:64-68`, `:487-560`).

| Channel | Name | Vendor scaling | Full scale |
| --- | --- | --- | --- |
| 0 | `BATSNS` | raw × 3 × 1800 / 32768 | 5.4 V, 15-bit |
| 1 | `ISENSE` | raw × 3 × 1800 / 32768 | 5.4 V, 15-bit |
| 2 | `VCDT` | raw × 1800 / 4096 | 1.8 V, 12-bit |
| 3 | `BATON` / BIF (battery NTC) | raw × 2 × 1800 / 4096 | 3.6 V, 12-bit |
| 4 | PMIC die temperature (or DCXO/TSX via mux) | raw × 1800 / 4096 | 1.8 V, 12-bit |
| 5 | `ACCDET` | raw × 1800 / 4096 | 1.8 V, 12-bit |
| 6 | reserved | raw × 1800 / 4096 | 1.8 V, 12-bit |
| 7 | `TSX` | raw × 1800 / 32768 | 1.8 V, 15-bit |
| 8 | - | raw × 1800 / 4096 | 12-bit |
| 9 | audio | raw, unscaled | raw code |
| 11 | VBIF28 pad | raw × 2 × 1800 / 4096 | 3.6 V, 12-bit |
| 10, 12-16 | - | raw × 1800 / 4096 | 12-bit |

The ×2 on channels 3 and 11 is easy to miss: the non-built MT6353 copy under
`drivers/misc/mediatek/pmic/mt6353/` has it commented out
(`/*r_val_temp = 2;*/ r_val_temp = 1; /*--VTREF--*/`) while the built MT6797
path (`power/mt6797/pmic_auxadc.c:499-506`, `:541-560`) sets
`r_val_temp = 2`. Read the built file for the product contract.

The datasheet application table gives the characterised input windows:
channels 0 and 1 2.5-4.8 V, channel 2 0-1.5 V, channel 3 0.1-2.7 V, channel 5
0-1.8 V, channel 7 0-1.8 V, others internal.

Channel 2 is not a mismatch. The converter keeps the 1.8 V transfer function,
the 1.5 V figure is the characterised linear window (about 14.2 V at the
connector), and the board divider sets the range: the device tree gives
`r_charger_1 = 330` and `r_charger_2 = 39` (kΩ) in `mt6797.dtsi:1042-1043`, a
9.46:1 ratio, and the battery meter restores the pack voltage by multiplying
the channel reading by `(r_charger_1 + r_charger_2) / r_charger_2`
(`battery_meter_hal.c:1175-1180`). The vendor comment "4-14 V" describes that
post-divider range.

Channel 4 is time-multiplexed: a control bit selects the PMIC die temperature or
the 26 MHz crystal temperature for DCXO compensation
(`pmic_auxadc.c:277-280`). The thermal driver reads the die-temperature
selection and converts it with PMIC OTP constants (see
[thermal management](mt6797-thermal-management.md)).

### 3.1 Battery NTC conversion (vendor fuel-gauge path)

The built path (`CONFIG_MTK_HAFG_20=y`) converts the `BATON` voltage in
`BattVoltToTemp()` (`drivers/power/mediatek/battery_meter_fg_20.c:1659-1690`):
- **The NTC:** a 10 kΩ part (`BAT_NTC_10`) behind a 24 kΩ pull-up
  (`RBAT_PULL_UP_R` for a non-MT6353 PMIC, `mt_battery_meter_table.h:21-36`),
  with no pull-down defined.
- **The pull-up voltage:** `RBAT_PULL_UP_VOLT_BY_BIF` is defined
  (`upmu_sw.h:21`), so it is the VBIF28 rail as measured by
  `pmic_get_vbif28_volt()` through channel 11, not a constant:
  `R_ntc = 24000 × V_baton / (V_bif28 − V_baton)`.
- **The table:** `R_ntc` is interpolated over the 17-entry table
  (−20 to 60 °C in 5 °C steps, 10000 Ω at 25 °C).
- **Not used here:** the device tree's battery node also carries
  `rbat_pull_up_r = <24000>`, `rbat_pull_up_volt = <1800>` and a 17-entry
  table (`mt6797.dtsi:1115-1131`). `battery_meter.c` parses them, but the
  built fuel-gauge formula uses the compile-time macros, so the 1800 mV
  value is not the effective pull-up (inference from the source).
- **The header's own constant:** `RBAT_PULL_UP_VOLT` (2800 mV) is the
  fallback only without `_BY_BIF`.

### 3.2 ADC clock

The immediate helper forces the ADC clocks on before a request
(`RG_AUXADC_CK_PDN`, `RG_AUXADC_SMPS_CK_PDN` and its hardware-enable,
`pmic_auxadc.c:171-174`, `:270-273`). A mainline driver must do the same,
and in the same order, before its first request.

### 3.2 Channel 11 is not a passive measurement

Reading channel 11 switches the VBIF28 pad onto the ADC input and then puts it
back (`pmic_auxadc.c:441-460`, `:541-560`):

- before the conversion (only while `g_pmic_pad_vbif28_vol == 1`, the
  "not measured" sentinel): `BATON_TDET_EN = 0`, `CKPDN_CON2_CLR = 0x70`,
  `RG_ADCIN_VSEN_MUX_EN = 1`, 3 ms delay;
- after the conversion, every time: `RG_ADCIN_VSEN_MUX_EN = 0`,
  `RG_VBIF28_ON_CTRL = 1`, `RG_VBIF28_MODE_CTRL = 1`, `RG_VBIF28_EN = 0`,
  `TOP_CKPDN_CON2_SET = 0x70`, 3 ms delay, `BATON_TDET_EN = 1`.

So a channel-11 read touches the VBIF28 pad path and battery-on detection. It
is also why the vendor validates the result: outside 2700-2912 mV it logs
`VBIF28_def_volt` and substitutes **2770 mV** (`:543-548`).

The measured value has exactly one consumer: `BattVoltToTemp()` divides the
battery NTC by `pmic_get_vbif28_volt() - V_baton`
(`drivers/power/mediatek/battery_meter_fg_20.c:1670`). The battery NTC divider
is therefore fed from VBIF28, and the temperature conversion is wrong if that
rail is off or if the substitute differs materially from the real rail.
`pmic_read_vbif28_volt()` keeps the sentinel-1 semantics of "not measured".

## 4. Calibration

The vendor ADC path performs **no** gain or offset calibration. The `deCount`
and `trimd` parameters of the immediate helper are accepted but unused, and the
scaled result is returned directly. Accuracy is the datasheet's block
specification: offset and gain error ±1 % of full scale, INL/DNL ±2 LSB,
100 kHz sample rate.

The AP-side `auxadc_cali[3:0]` field at `0x10001B10` belongs to the AP's own
AUXADC block, not to the PMIC. The only PMIC OTP values used for an ADC-derived
quantity are the thermal channel's `O_VTS`, `DEGC_cali` and `O_SLOPE` constants,
which convert the channel-4 Vbe reading to degrees.

## 5. Consumers in the vendor stack

| Consumer | Channels | Evidence |
| --- | --- | --- |
| Battery meter voltage/current/temperature | `BATSNS`, `ISENSE`, `BATON`, `VCDT` | `power/mt6797/battery_meter_hal.c:1140-1180` |
| Charger/OCV-ZCV power accounting | `BATSNS`, `ISENSE` | `power/mt6797/pmic.c:3068-3078`, `:3376-3378` |
| PMIC die temperature | channel 4 | `thermal/mt6797/src/mtk_pmic_efuse.c:154` |
| VBIF28 rail check (MT6351 workaround) | channel 11 | `pmic_auxadc.c:441-460`, `:520-560` |
| DCXO crystal | channel 4 via mux | `pmic_auxadc.c:277-280` |
| Audio | channel 9 raw | channel table comment in `pmic_auxadc.c` |
| Accessory / headset | `ACCDET` | defined in the channel enum; no open AP consumer found |

The battery meter reads its temperature input from `BATON` (channel 3), so the
battery NTC is a PMIC ADC channel rather than a fuel-gauge input. The datasheet
separates the two measurement engines: a dedicated fuel-gauge ADC measures
battery current, while the auxiliary ADC measures battery voltage and
temperature. The vendor stack follows that split.

Note that the MT6353-family sources under `drivers/misc/mediatek/pmic/mt6353/`
are not built here (`CONFIG_MTK_PMIC_CHIP_MT6353` is unset); the built MT6797
PMIC path is `drivers/misc/mediatek/power/mt6797/`.

## 6. Sharing the ADC with the modem

At wrapper init the vendor driver programs the modem share
(`pmic_wrap/mt6797/pwrap_hal.c:820-855`, called from `:1181`):

- `ADC_CMD_ADDR` points at `AUXADC_RQST1_SET`, with `PWRAP_ADC_CMD = 0x0100`;
- `ADC_RDATA_ADDR` points at `AUXADC_ADC16`;
- `MD_ADC_RDATA_ADDR_LATEST` points at `AUXADC_ADC32`;
- `MD_ADC_RDATA_ADDR_WP` points at `AUXADC_MDBG_1`;
- `MD_ADC_RDATA_ADDR0..31` point at `AUXADC_BUF0..BUF31`.

The PMIC therefore fills a 32-entry ring of conversions that the modem reads
through the wrapper, with the newest value also available directly. The AP never
reads this ring in the open vendor code; it only configures the pointers. The
CCCI RPC layer exposes modem ADC values to userspace
(`FEATURE_GET_MD_ADC_NUM`/`_VAL`, `eccci/port_rpc.c:71-102`).

The retained modem image carries its own calibration table for these samples
(`l1cal_temperatureADC_T`, size-checked at load) and the AT commands
`+EADC`, `MmiATADC` plus the diagnostic "AP ADC Query is abnormal". Byte-level
decoding of the table was not attempted.

What the modem samples is now resolved. The PMIC driver's modem helper
`PMIC_IMM_GetOneChannelValueMD()` (`pmic_auxadc.c:599`) documents the
`RQST1` channel map and shows that it is the same bit-per-channel layout as
`RQST0`:

```
CH0 BATSNS   CH1 ISENSE   CH4 PMIC TEMP   CH7 TSX by MD   CH8 TSX by GPS
```

It writes `1 << channel` to `AUXADC_RQST1_SET` and reads `_BY_MD` results
(channels 0, 1, 4, 7) or `ADC_OUT_CH7_BY_GPS` (channel 8). The wrapper's
command `0x0100` is therefore bit 8, **channel 8, the 26 MHz TSX/GPS crystal
temperature**, and the matching result register is `ADC16` (0x0E20) — which is
exactly what `ADC_RDATA_ADDR` points at.

The ring is not the PMIC die temperature and not the battery NTC. It is the
crystal temperature used for GPS/radio clock compensation, which is why the
datasheet calls the wrapper registers "thermal data" and why the modem firmware
holds a temperature ADC calibration table.

`ADC32` is resolved too: it is `ADC_OUT_MDRT` / `ADC_RDY_MDRT` (0x0E40), the
modem real-time result, so `MD_ADC_RDATA_ADDR_LATEST` points at the newest
sample rather than at an inert snapshot. `ADC33` is the separate `MDBG` debug
result, with its busy bit in `STA1`. `MDBG_0` (0x0F16) holds the detection
period and enable, `MDBG_1` (0x0F18) is the pointer the wrapper writes, and
`BUF0..31` are the ring entries.

Who enables the detection engine is not visible in the AP code: `_pwrap_adc_set`
writes only the pointers, and no built file configures `MDBG_DET_EN`,
`AUTORPT0` or `LBAT`. That remains open (modem firmware or hardware default).

## 7. Firmware observations

| Image | ADC content |
| --- | --- |
| Preloader | ARM32 Thumb-2 image (no AArch64 code) containing the same immediate-conversion routine and charger/battery strings; exact channels not decoded (see open questions) |
| SCP | no PMIC ADC strings; PWRAP is used for DVFS/clock registers only |
| ATF/TEE | no PMIC ADC strings |
| Modem | `l1cal_temperatureADC_T` NVRAM calibration, `+EADC`/`MmiATADC` commands, AP-query diagnostic |
| Wi-Fi/touch/other | no PMIC ADC content |

## 8. Upstream coverage

Upstream Linux 7.1.3 does **not** provide an MT6351 ADC driver. The MT6351 is
only an MFD child with regulator, RTC, keys and sound cells
(`drivers/mfd/mt6397-core.c:223`, binding
`Documentation/devicetree/bindings/mfd/mediatek,mt6397.yaml`), plus
`drivers/regulator/mt6351-regulator.c`.

The nearest upstream models are:

- `drivers/iio/adc/mt6359-auxadc.c` — IIO driver for MT6357/MT6358/MT6359/MT6363.
  It uses the same request/ready/result shape but a different register layout,
  impedance and DCM blocks, and a per-SoC channel table.
- `drivers/mfd/mt6392-auxadc.c` and `drivers/mfd/mt6323-auxadc.c` — legacy
  in-MFD ADC helpers for older PMIC families.
- `drivers/soc/mediatek/mtk-pmic-wrap.c` — models the MT6797 wrapper's WACS and
  interrupt registers only; the ADC command and modem-ring registers
  (`0x1DC`-`0x218`) are absent from the `mt6797_regs` table.

A future MT6351 driver would need: a wrapper-backed regmap, the request/ready/
result sequence, the per-channel scaling above, the channel-4 mux, and an
explicit decision about the modem ring (configure it read-only, or leave it to a
firmware owner). It would also need to coexist with the SPM/DVFSP and thermal
users of the same PMIC register space.

## 9. Open questions

1. Which channels the preloader requests. The image is ARM32 Thumb-2 (no
   AArch64 `ret` anywhere, 151 Thumb `bx lr`), and its file layout does not map
   linearly to the runtime addresses: no literal-pool or `adr` reference to the
   ADC strings resolves under any candidate base. Its messages imply battery
   voltage, charger voltage and charging current (channels 0, 2 and 1), but
   that is inference.
2. Who enables the MDBG detection engine, `AUTORPT0` or `LBAT`: the AP
   configures only the pointer registers.
3. Whether `THR_MD` has a dedicated output register distinct from `MDRT`.

Resolved since the first version of this document: the modem ring samples the
GPS/DCXO crystal temperature (channel 8), `ADC32` is the MDRT result, and the
channel-2 range is set by the 330/39 kΩ board divider.

## Evidence index

- Vendor kernel `planet-community/android_kernel_planetcom_mt6797`, commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`; built MT6797 PMIC path under
  `drivers/misc/mediatek/power/mt6797/` and wrapper under
  `drivers/misc/mediatek/pmic_wrap/mt6797/`.
- MT6351 PMIC datasheet v12, section 3.2.9 and register summary; MT6797
  register-table part 1, page 608.
- Retained private preloader, SCP, TEE and modem images (see
  [firmware boundary](firmware.md)).
- [PMIC ADC experiment](../../experiments/2026-10-31-mt6351-pmic-adc/README.md).
