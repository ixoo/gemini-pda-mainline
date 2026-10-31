# MT6351 auxiliary ADC: source, document and firmware inventory

Scope: the built MT6797 vendor kernel path (`drivers/misc/mediatek/power/mt6797/`
and `pmic_wrap/mt6797/`), the MT6351 datasheet, the MT6797 register table and the
retained firmware images. All paths are relative to the vendor tree at commit
`8cfe6596a503612e3332d9c26e292a19525a7f07` unless stated otherwise.

## 1. Access path

`PMIC_IMM_GetOneChannelValue()` (`power/mt6797/pmic_auxadc.c:235`):

1. force the ADC clock on (`PMIC_AUXADC_CK_AON`, `CLK_AUXADC_SMPS_CK_PDN`);
2. take the ADC mutex;
3. write `1 << channel` to `MT6351_AUXADC_RQST0_SET` (PMIC `0x0E98`);
4. poll the channel's ready bit with a bounded count (`usleep_range(1300,
   1500)`), logging a timeout;
5. read the result register and scale it;
6. unlock.

Special cases inside the same function:

- channel 3 and channel 11 are scaled by `r_val_temp = 2` in the built MT6797
  file (`:499-506`, `:541-560`); the non-built MT6353 copy uses ×1;
- channel 4 mux: `PMIC_AUXADC_DCXO_CH4_MUX_AP_SEL` selects die temperature or
  DCXO/TSX (`:277-280`);
- channel 11 is not passive: before the conversion it disables
  `BATON_TDET_EN`, clears clock gating and enables `RG_ADCIN_VSEN_MUX_EN`;
  after it, every time, it restores the mux, writes
  `RG_VBIF28_ON_CTRL=1`, `RG_VBIF28_MODE_CTRL=1`, `RG_VBIF28_EN=0`, re-gates
  the clocks and re-arms `BATON_TDET_EN` (`:441-460`, `:541-560`). Results
  outside 2700-2912 mV are replaced with **2770 mV** (`:543-548`);
- channel 9 is returned unscaled (audio);
- unknown channels return -1.

`pmic_get_vbif28_volt()` has one consumer:
`BattVoltToTemp()` divides the battery NTC equation by
`pmic_get_vbif28_volt() - V_baton` (`battery_meter_fg_20.c:1670`), so the NTC
divider is fed from VBIF28 and the temperature conversion depends on that rail
and on the 2770 mV substitute.

## 2. Register window (PMIC 16-bit register space)

From `include/mt-plat/mt6797/include/mach/upmu_hw.h:793-900` and the datasheet
register summary (pages 82-85):

| Range | Contents |
| --- | --- |
| `0x0E00`-`0x0E4E` | `AUXADC_ADC0`..`ADC39`, 2-byte stride |
| `0x0E50`-`0x0E8E` | `AUXADC_BUF0`..`BUF31` |
| `0x0E90`-`0x0E94` | `STA0`, `STA1` (THR_HW/THR_MD busy), `STA2` |
| `0x0E96`/`0x0E98`/`0x0E9A` | `RQST0`, `RQST0_SET`, `RQST0_CLR` |
| `0x0E9C`/`0x0E9E`/`0x0EA0` | `RQST1`, `RQST1_SET`, `RQST1_CLR` |
| `0x0EA2`-`0x0EC6` | `CON0`..`CON16` |
| `0x0EC8` | `AUTORPT0` |
| `0x0ECA`-`0x0ED6` | `LBAT0`..`LBAT6` |
| `0x0F18` | `MDBG_1` (modem ring pointer) |

Result layout: bit 15 ready, data bits below. Channel 0, 1 and 7 have `_BY_AP`
result aliases (`ADC23`, `ADC25`, `ADC18`); the others use their own register.

Wrapper side (MT6797 register table part 1, page 608; vendor
`pwrap_hal.h:308-352`):

| Offset | Register |
| --- | --- |
| `0x1000D1DC` | `ADC_CMD_ADDR` |
| `0x1000D1E0` | `PWRAP_ADC_CMD` |
| `0x1000D1E4` | `ADC_RDATA_ADDR` |
| `0x1000D1F4` | `MD_ADC_RDATA_ADDR_LATEST` |
| `0x1000D1F8` | `MD_ADC_RDATA_ADDR_WP` |
| `0x1000D1FC`-`0x1000D278` | `MD_ADC_RDATA_ADDR0..31` |

The `pwrap_hal_d2.h` header carries the same names at offsets 0x4C lower and
omits `HARB_SLEEP_GATED_CTRL`; it is not the header this build includes.

## 3. Channels and scaling

Constants: `VOLTAGE_FULL_RANGE = 1800`, `ADC_PRECISE = 32768` (15-bit),
12-bit divisor 4096 (`pmic_auxadc.c:64-68`).

| Ch | Name | Scaling (vendor) | Result |
| --- | --- | --- | --- |
| 0 | `BATSNS` | raw × 3 × 1800 / 32768 | mV |
| 1 | `ISENSE` | raw × 3 × 1800 / 32768 | mV |
| 2 | `VCDT` | raw × 1800 / 4096 | mV |
| 3 | `BATON` / BIF | raw × 2 × 1800 / 4096 | mV (battery NTC) |
| 4 | PMIC temperature / DCXO | raw × 1800 / 4096 | mV or thermal code |
| 5 | `ACCDET` | raw × 1800 / 4096 | mV |
| 6 | reserved | raw × 1800 / 4096 | mV |
| 7 | `TSX` | raw × 1800 / 32768 | mV |
| 8 | - | raw × 1800 / 4096 | mV |
| 9 | audio | raw | code |
| 11 | VBIF28 pad | raw × 2 × 1800 / 4096 | mV |
| 10, 12-16 | - | raw × 1800 / 4096 | mV |

The built MT6797 file sets `r_val_temp = 2` for channels 3 and 11
(`power/mt6797/pmic_auxadc.c:499-506`, `:541-560`). The non-built MT6353 copy
has the ×2 commented out and uses ×1, which is a trap when citing the wrong
file.

Datasheet application ranges (`Table 3-4`): 0/1 2.5-4.8 V, 2 0-1.5 V, 3
0.1-2.7 V, 5 0-1.8 V, 7 0-1.8 V, others internal. Channel 2 uses the 1.8 V
converter transfer with a 1.5 V characterised window; the board divider
(`r_charger_1 = 330`, `r_charger_2 = 39` in `mt6797.dtsi:1042-1043`, 9.46:1)
sets the 4-14 V range quoted by the vendor comment, and
`battery_meter_hal.c:1175-1180` restores the pack voltage.

Accuracy (datasheet Table 2-15): 15-bit on `AUXADC_VIN`, 12-bit on the others,
100 kHz sample rate, offset/gain error ±1 % FS, INL/DNL ±2 LSB.

## 4. Calibration

- No gain/offset correction: `deCount` and `trimd` are accepted but never used
  in `PMIC_IMM_GetOneChannelValue()`; the scaled value is returned directly.
- `g_I_SENSE_offset` appears only in the current calculation
  (`pmic_auxadc.c:214`); no assignment was found in the tree.
- The AP analog block's `auxadc_cali[3:0]` (`0x10001B10`, register table part 1
  page 198) belongs to the AP AUXADC, not the PMIC.
- The PMIC OTP constants that do calibrate something are the thermal-channel
  Vbe terms (`O_VTS`, `DEGC_cali`, `O_SLOPE`), used by `mtk_pmic_efuse.c`.

## 5. Consumers

| Caller | Channels | Citation |
| --- | --- | --- |
| Battery meter (`read_adc_v_bat_temp`, `read_adc_v_charger`, ZCV) | `BATON`, `VCDT`, `BATSNS`, `ISENSE` | `power/mt6797/battery_meter_hal.c:1140-1180` |
| Charger/OCV-ZCV accounting | `BATSNS`, `ISENSE` | `power/mt6797/pmic.c:3068-3078`, `:3376-3378` |
| PMIC die temperature | ch4 | `thermal/mt6797/src/mtk_pmic_efuse.c:154` |
| VBIF28 workaround | ch11 | `pmic_auxadc.c:441-460`, `:520-560` |
| DCXO crystal | ch4 mux | `pmic_auxadc.c:277-280` |
| Audio | ch9 | channel comment only |
| Accessory | ch5 | no AP caller found (userspace or modem side) |

The MT6353 DLPT/PBM code paths are not built for this product
(`CONFIG_MTK_PMIC_CHIP_MT6353` and `CONFIG_MTK_PBM` unset in the retained Gemian
configuration), so they are not consumers here.

## 6. Modem share configured by the wrapper

`_pwrap_adc_set()` (`pmic_wrap/mt6797/pwrap_hal.c:820-855`, called at `:1181`):

```
ADC_CMD_ADDR            <- MT6351_AUXADC_RQST1_SET   (0x0E9E)
PWRAP_ADC_CMD           <- 0x0100
ADC_RDATA_ADDR          <- MT6351_AUXADC_ADC16       (0x0E20)
MD_ADC_RDATA_ADDR_LATEST<- MT6351_AUXADC_ADC32       (0x0E40)
MD_ADC_RDATA_ADDR_WP    <- MT6351_AUXADC_MDBG_1      (0x0F18)
MD_ADC_RDATA_ADDR0..31  <- MT6351_AUXADC_BUF0..BUF31 (0x0E50..0x0E8E)
```

The AP configures the pointers once and never reads the ring in the open tree.
The modem firmware consumes it and applies its own NVRAM calibration; the AP can
query modem ADC values through CCCI RPC (`FEATURE_GET_MD_ADC_NUM`/`_VAL`,
`eccci/port_rpc.c:71-102`).

`RQST1` uses the same bit-per-channel layout as `RQST0`: the modem helper
`PMIC_IMM_GetOneChannelValueMD()` (`pmic_auxadc.c:599`) documents channels 0
(BATSNS), 1 (ISENSE), 4 (PMIC temp), 7 (TSX by MD) and 8 (TSX by GPS), and
writes `1 << channel` to `AUXADC_RQST1_SET`. Command `0x0100` is therefore
channel 8, the GPS/DCXO crystal temperature, whose result register is
`ADC_OUT_CH7_BY_GPS` = `ADC16` — the address the wrapper puts in
`ADC_RDATA_ADDR`.

`ADC32` is `ADC_OUT_MDRT`/`ADC_RDY_MDRT` (0x0E40), the modem real-time result,
so `MD_ADC_RDATA_ADDR_LATEST` points at the newest modem sample. `ADC33` is the
separate `MDBG` debug result (busy bit in `STA1`). `MDBG_0` (0x0F16) holds the
detection period/enable and `MDBG_1` (0x0F18) the pointer. No built AP file
enables `MDBG_DET_EN`, `AUTORPT0` or `LBAT`.

## 7. Firmware strings

| Image | Strings / findings |
| --- | --- |
| Preloader `boot0`/`boot1` | ARM32 Thumb-2 image; `[PMIC_PRELOADER][AUXADC] ch=%d raw=%d data=%d`, invalid-channel message, charger/battery detection messages, and its own copy of the helper. No AArch64 `ret` in the whole image; no resolvable literal/`adr` reference to the ADC strings under any candidate base, so channels are not decoded |
| SCP `scp1`/`scp2` | no PMIC ADC strings; PWRAP used for DVFS/clock only |
| ATF/TEE `tee1`/`tee2` | no PMIC ADC strings |
| Modem `md1img`/`md3img` | `l1cal_temperatureADC_T` size check, `+EADC`, `MmiATADC`, `[MMRF_DRDI] AP ADC Query is abnormal` |
| Wi-Fi, touch, filters | no PMIC ADC content |

## 8. Upstream coverage

- MT6351 MFD: `mt6351` compatible and children regulator/RTC/keys/sound in
  `drivers/mfd/mt6397-core.c:223`; binding
  `mediatek,mt6397.yaml` lists `mediatek,mt6351`.
- No MT6351 IIO ADC. `drivers/iio/adc/mt6359-auxadc.c` covers MT6357/58/59/63
  with impedance/DCM blocks; `drivers/mfd/mt6392-auxadc.c` and
  `mt6323-auxadc.c` are legacy in-MFD helpers.
- `drivers/soc/mediatek/mtk-pmic-wrap.c` `mt6797_regs[]` stops at
  `PWRAP_DCM_DBC_PRD` (`0x1D4`) and has no `0x1DC`-`0x278` ADC entries.

## 9. Limits

- Static reading only; no register was read on hardware.
- The datasheet register chapter is partly unextractable (tables), so `CON`,
  `AUTORPT`, `LBAT` and `DET` semantics are not documented here beyond their
  existence and the vendor's use of `RQST0`/`RQST1`.
- Preloader channel use stays undecoded: the image is ARM32 Thumb-2 and its
  file layout does not map linearly to runtime addresses.
- Resolved in this revision: the modem ring channel (8, GPS/DCXO TSX), the
  `ADC32` meaning (MDRT real-time result), and channel 2 (board divider
  330/39 kΩ, 1.5 V characterised window).
