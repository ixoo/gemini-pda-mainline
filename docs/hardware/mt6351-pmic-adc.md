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
| 3 | `BATON` / BIF | raw × 1800 / 4096 | 1.8 V, 12-bit |
| 4 | PMIC die temperature (or DCXO/TSX via mux) | raw × 1800 / 4096 | 1.8 V, 12-bit |
| 5 | `ACCDET` | raw × 1800 / 4096 | 1.8 V, 12-bit |
| 6 | reserved | raw × 1800 / 4096 | 1.8 V, 12-bit |
| 7 | `TSX` | raw × 1800 / 32768 | 1.8 V, 15-bit |
| 8 | - | raw × 1800 / 4096 | 12-bit |
| 9 | audio | raw, unscaled | raw code |
| 10-16 | - | raw × 1800 / 4096 | 12-bit |

The datasheet application table gives different input windows: channels 0 and 1
2.5-4.8 V, channel 2 0-1.5 V, channel 3 0.1-2.7 V, channel 5 0-1.8 V, channel 7
0-1.8 V, others internal. The vendor scaling for channel 2 therefore implies
either an external divider or a datasheet/vendor mismatch; the vendor comment
next to the channel enum claims 4-14 V. Treat channel 2's absolute scaling as
unresolved.

Channel 4 is time-multiplexed: a control bit selects the PMIC die temperature or
the 26 MHz crystal temperature for DCXO compensation
(`pmic_auxadc.c:277-280`). The thermal driver reads the die-temperature
selection and converts it with PMIC OTP constants (see
[thermal management](mt6797-thermal-management.md)).

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

What the modem samples is not established: `RQST1` is absent from the
extractable datasheet register text, and the single `0x0100` command bit does
not map to a channel through the documented `RQST0` layout. The THR_MD status
bit exists but its result register was not identified; `ADC32` (the "latest"
pointer target) is the most likely candidate. Recorded as an open question.

## 7. Firmware observations

| Image | ADC content |
| --- | --- |
| Preloader | contains the same immediate-conversion routine and charger/battery strings (`[PMIC_PRELOADER][AUXADC] ch=%d raw=%d data=%d`, invalid-channel message); exact channels not decoded |
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

1. Which channel the modem ring samples (`RQST1` bit 8 / `0x0100`).
2. Whether `ADC32` is the THR_MD result or only a snapshot register.
3. The true channel-2 divider and the mismatch with the datasheet window.
4. Which channels the preloader requests, and whether it applies any trim.
5. Whether the `AUTORPT`/`LBAT`/`DET` engines are used anywhere on this product.

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
