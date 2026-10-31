# Fuel-gauge inventory

Scope: the MT6351 FGADC and the vendor HAFG_20 algorithm on the named Gemini
PDA. Vendor paths are relative to commit `8cfe6596`; LK paths to `f4988d74`.
The hardware identity and basic register configuration are already in the
[2026-10-04 charging record](../../2026-10-04-gemini-charging-re/README.md)
(F15-F19); this file adds the counter read path, the algorithm structure, the
calibration divergence and the boot-chain behaviour.

## 1. Hardware

Datasheet (MT6351 v12 table 2-16, section 3.2.10): 16-bit output, 1/16 s
conversion, over-sampling 2^11-2^18, input ±60 mV, 2.8 V supply, gain error
±2 %, accuracy 0.03 %.

| Offset | Register | Contents |
| --- | --- | --- |
| `0x0CA4` | `FGADC_CON0` | enable/calibration/read control; latch status bit 10; clear |
| `0x0CA6`-`0x0CAA` | `CON1`-`CON3` | `FG_CAR[34:19]`, `[18:3]`, `[2:0]` (35-bit charge) |
| `0x0CAC`-`0x0CB0` | `CON4`-`CON6` | `FG_NTER[32:17]`, `[16:1]`, `[0]` (33-bit charge time) |
| `0x0CBA` | `CON11` | `FG_CURRENT_OUT[15:0]` |
| `0x0CC2` | `CON15` | OSR/filter control |
| `0x0CD6` | `CON25` | `FG_R_CURR` (resistance/IM path) |
| `0x0CB8` | undocumented | per-chip gain trim at bits 11:7 (used by LK only) |
| `0x02D4`/`0x02E6` | `FG_BAT_H/L` enable/status | battery voltage comparator interrupts |

Reading is a latched transaction: write the read command to `FGADC_CON0`, poll
the latch status, read the counter/current registers, clear the latch. LK
implements exactly this sequence (`lk/platform/mt6797/mt_battery.c:685-760`).

## 2. Counter and current read path

- LSB: `UNIT_FGCURRENT = 158.122 µA` for a 20 mΩ sense base
  (`battery_meter_hal.c:36`), rescaled by `20 / R_FG_VALUE` and then by
  `CAR_TUNE_VALUE / 100`. With the board's 10 mΩ resistor the first factor is
  ×2.
- Sign: a 16-bit value above 32767 is negative (`LK:733-745`).
- Kernel counter read: `battery_meter_get_car()` issues
  `BATTERY_METER_CMD_GET_HW_FG_CAR_ACT` and rounds the result by 10
  (`battery_meter_fg_20.c:2231-2248`); the HAL performs the latched register
  access.
- Instantaneous current: `FG_CURRENT_OUT` through the same latch, with the
  charge/discharge sign reported separately
  (`battery_meter_get_battery_current_sign`).

## 3. Qmax, OCV and aging

- **Qmax** is interpolated over four temperature anchors: below 0 °C between
  `Q_MAX_NEG_10` and `Q_MAX_POS_0`, then 0→25 °C and 25→50 °C
  (`fgauge_get_Q_max`, `:1534-1596`). A high-current variant uses the
  `_h_current` table entries. The board DT gives `q_max_pos_25 = 2707` mAh and
  the anchors at `temperature_t0..t3` = 110/0/25/50 (the first is an invalid
  marker; the effective cold anchor is −10 °C).
- **OCV/ZCV** is a four-profile, 82-point table (one profile per anchor
  temperature). `fgauge_read_v_by_capacity()` and
  `fgauge_read_capacity_by_v()` interpolate between adjacent points
  (`:2312-2394`); out-of-range inputs clamp to 3700 mV or 100 %.
- **Tracking**: `gFG_voltage` is the ZCV, `gFG_15_vlot` the 15 % ZCV used for
  tracking, and `g_tracking_point` the capacity tracking point
  (`battery_meter_get_battery_zcv`, `_nPercent_zcv`, `_nPercent_UI_SOC`).
- **Aging**: `get_battery_aging_factor(cycle)` interpolates a
  `battery_aging_table` (cycle → factor, 100 = new) and the cycle counter is
  exposed through a `FG_Battery_Cycle` sysfs attribute (`:2659-2697`,
  `:2698-2740`). The algorithm enabling flag and load/update SOC thresholds
  come from the DT (`mtk_enable_aging_algorithm`, `aging1_load_soc`,
  `aging1_update_soc`, `aging_tuning_value`).
- **Smoothing**: `battery_meter_smooth_uisoc2()` filters the second UI SOC
  (`:2529-2585`), which is what the periodic log prints as the three-value
  `SOC a:b:c` field.

## 4. Initialisation and persistence

- `battery_meter_initial()` runs the hardware FG init, then
  `wakeup_fg_algo(FG_MAIN)`; if the work queue is not up it falls back to
  `fgauge_algo_run_get_init_data()` (`:2394-2432`). `SOC_BY_HW_FG` is defined,
  so the hardware counter is the primary source.
- The first reading establishes `gFG_voltage_init`, `gFG_current_init` and
  `gFG_Is_Charging_init` (the retained logs show these values).
- The kernel stores a coarse SOC in the RTC spare FG byte and reads it back on
  the next boot (`get/set_rtc_spare_fg_value`, `:4192`, `:4532`, `:4732`).
- LK does not store SOC; it clears the spare byte when entering a low-battery
  charging cycle (`lk_set_rtc_to_zero()`, `LK:275-283`), so a stale value does
  not survive a charger-assisted recovery.

## 5. Calibration and the LK/kernel divergence

- The FGADC has a factory per-chip gain trim in the undocumented register
  `0xCB8[11:7]`, mapping to factors 1000…1081 and 995/990 for the top codes
  (`battery_meter_hal.c:61-130`, `LK:539-650`).
- **LK applies it** (`fgauge_read_current`, `:733-780`); the **kernel does
  not**: `chip_diff_trim_value_4_0` is hard-coded to 0, which selects the
  neutral 1000 (`battery_meter_hal.c:67-73`).
- LK uses `CAR_TUNE_VALUE = 86` (`LK:522`) while the kernel DT supplies
  `car_tune_value = 118`. The two stages disagree by about 27 % on current
  scaling.
- Board parameters in the DT: `r_fg_value = 10` mΩ, `cust_r_sense = 56`
  (0.01 Ω), `fg_meter_resistance = 0`, `vbat_low_power_wakeup = 3500` mV,
  `rbat_pull_up_r = 24000`, `rbat_pull_up_volt = 1800`.

## 6. Temperature and shutdown

- Temperature comes from PMIC AUXADC channel 3 (`BATON`) through the NTC divider
  and `BattVoltToTemp()`; it is not a gauge temperature.
- `shutdown_system_voltage`, `shutdown_gauge0`/`1` and the low-battery wake
  threshold (3500 mV) are board values; the battery task uses them to raise
  `bat_low` and to trigger the shutdown path.

## 7. Live evidence

Retained Gemian logs show the initialisation split and the published triple:

```
[fgauge_algo_run_get_init_data](gFG_voltage_init 4129, gFG_current_init 5234, gFG_Is_Charging_init 0)
[kernel]AvgVbat 4126, bat_vol 4126, AvgI 0, VChr 0, AvgT 24, ZCV 0, SOC 0:-100:-1
[kernel]AvgVbat 4346, bat_vol 4346, AvgI 479, I -125, VChr 4957, AvgT 23, ZCV 0, CHR_Type 1, SOC 100:100:100
```

`-100` in the middle field and `ZCV 0` are the not-ready sentinels; they clear
once the gauge has run. This confirms the init path but is not a calibration
measurement.

## 8. Mainline position

No MT6351 gauge driver exists upstream. The PMIC is an MFD/regulator child and
`drivers/power/supply` has only MT6360/MT6370 chargers. A mainline gauge would
need a wrapper regmap, the latched 35-bit counter, the OCV/Qmax tables
(vendor calibration) and a power-supply presentation; the vendor SOC model is
not portable as-is.

## 9. Limits

- Static reading only; no gauge register was read and no discharge curve was
  measured.
- The counter's absolute unit and wrap behaviour are inferred from the vendor
  scaling and the rounding in `battery_meter_get_car()`, not measured.
- The battery profile tables are intentionally not reproduced; only their shape
  and public anchor values are recorded.
- The per-chip trim's true encoding is undocumented in the public datasheet.
