# Fuel-gauge inventory

Scope: the MT6351 FGADC and the vendor gauge layer on the named Gemini PDA.
Vendor paths are relative to commit `8cfe6596`; LK paths to `f4988d74`. The
identity and basic register set are in the
[2026-10-04 charging record](../../2026-10-04-gemini-charging-re/README.md)
(F15-F19); this file records the counter model, where the estimator actually
runs, the calibration that reaches the hardware, and the persistence split.

## 1. Hardware

Datasheet (MT6351 v12 table 2-16, section 3.2.10): 16-bit output, 1/16 s
conversion, over-sampling 2^11-2^18, input ±60 mV, 2.8 V supply, gain error
±2 %, accuracy 0.03 %. The driver uses `FG_OSR = 8`.

| Offset | Register | Contents |
| --- | --- | --- |
| `0x0CA4` | `FGADC_CON0` | enable/calibration/latch control; status bit 10; clear |
| `0x0CA6`-`0x0CAA` | `CON1`-`CON3` | `FG_CAR[34:19]`, `[18:3]`, `[2:0]` |
| `0x0CAC`-`0x0CB0` | `CON4`-`CON6` | `FG_NTER[32:17]`, `[16:1]`, `[0]` |
| `0x0CBA` | `CON11` | `FG_CURRENT_OUT[15:0]` |
| `0x0CC2` | `CON15` | OSR/filter control |
| `0x0CD6` | `CON25` | `FG_R_CURR` |
| `0x0CB8` | undocumented | per-chip gain trim at bits 11:7 |
| `0x02D4`/`0x02E6` | `FG_BAT_H/L` | battery voltage comparator interrupts |

## 2. Counter model and units

The driver does not read a plain 35-bit number. It builds a 17-bit slice and
takes the sign from `FG_CAR[34:19]` bit 15 (`battery_meter_hal.c:930-934`):

```
raw   = (FG_CAR[18:3] >> 11) | ((FG_CAR[34:19] & 0xFFF) << 5)
zero  if raw == 0 or raw == 0x1ffff
value = raw, or (0x1ffff - raw) when the sign bit says discharging
```

Scale chain (`battery_meter_hal.c:995-1050`):

```
counts = value * 35986 / 10 / 10          /* 359.86 µAh per count */
counts = counts / 8                       /* FG_OSR = 8 -> ~44.98 µAh/count */
counts = counts * 20 / r_fg_value         /* x2 on the 10 mOhm board */
counts = counts * car_tune_value / 100
counts = counts * chip_trim / 1000        /* kernel forces 1000 */
```

`precise = 0` returns mAh, `precise = 1` deci-mAh. The maximum magnitude is
about 2.95 Ah. The counter free-runs and is cleared only by an explicit
hardware reset (`fgauge_hw_reset`), not by reads; reads pulse the software
latch. Sampling is the 10 s battery task plus daemon requests and the PMIC
`FG_BAT_H/L` wake in suspend.

The instantaneous current is a separate register: `FG_CURRENT_OUT` uses a
**158.122 µA LSB** for a 20 mΩ base (`battery_meter_hal.c:36`), with the same
rescaling. That LSB does not apply to the counter.

## 3. Where the estimator runs

The kernel is not the estimator. Userspace `fuelgauged`/`libfgauge.so` owns
SOC, UI SOC, DOD, Rbat and Qmax and writes them into the kernel over
`NETLINK_FGD` (26) with `SET_SOC`, `SET_UI_SOC2`, `SET_QMAX` and `SET_RBAT`
(`battery_meter_fg_20.c:4481-4590`). The kernel republishes
`BAT_CAPACITY = UI_SOC2` (`battery_common_fg_20.c:1653`).

Publication is gated on `g_battery_soc_ready`, set by the first `SET_UI_SOC2`;
before that the capacity stays `-1`. In-kernel fallbacks:

- `fgauge_algo_run_get_init_data()` reads the first voltage/current pair;
- `dod_init_in_kernel()` reconciles the RTC spare SOC, a software SOC and the
  hardware SOC with 10/30-point rules.

`MTK_POWER_SMOOTH_SUPPORT` is **defined**, so the published pack voltage is
`fgauge_read_v_by_capacity(100 - UI_SOC2, temperature)` — a table lookup at the
reported SOC, not the ADC reading (`battery_common_fg_20.c:1645-1710`).
`USING_SMOOTH_UI_SOC2` is undefined, so the UI-SOC smoothing function is
compiled out, and `nPercent_ZCV` is a constant 3700 mV.

## 4. Qmax, OCV and aging

- The in-kernel `fgauge_get_Q_max()` interpolates 4211/4268/4312/4336 mAh over
  −10/0/25/50 °C but has **no caller** in the built path; the high-current
  variant is unreachable.
- Runtime Qmax is `gFG_BATT_CAPACITY_aging`, default **1200 mAh**, otherwise
  supplied by `SET_QMAX`.
- All `aging_*` state is dead; `aging1_load_soc`, `aging_tuning_value` and
  `mtk_enable_aging_algorithm` are only ABI constants, and lifetime-data
  support is not built.
- OCV profiles: the effective tables are the header's four ~96-point
  `{%, mV}` tables, selected at hardcoded 0/15/40/65 °C steps with linear
  interpolation inside a table. The DT's 82-point profiles never load because
  the parser is disabled (below).

## 5. Calibration and the device-tree defect

`batt_meter_init_cust_data()` returns the compile-time header path; the DT
parser call is commented out (`battery_meter_fg_20.c:1330-1338`), and its
property-read checks are inverted, so it would not apply even if called. The
effective values are the header defaults:

| Parameter | DT | Effective |
| --- | --- | --- |
| `R_FG_VALUE` | 10 mΩ | 10 mΩ |
| `CAR_TUNE_VALUE` | 118 | **115** |
| `FG_METER_RESISTANCE` | 0 | **75** |
| NTC pull-up voltage | 1800 mV | **2800 mV** |
| OCV / Qmax profiles | 82 points | **~96-point header tables** |

The factory per-chip trim lives in undocumented `0xCB8[11:7]` (factors
990-1081). **LK applies it** (`mt_battery.c:539-650`, `:733-780`); the kernel
hard-codes the selector to 0, i.e. neutral 1000
(`battery_meter_hal.c:67-73`). LK also uses `CAR_TUNE_VALUE = 86` (`LK:522`),
so the bootloader and the kernel scale current differently.

Temperature: a `BATON` reading above 2600 mV forces 20 °C and skips the NTC
table (`battery_meter_fg_20.c:1345-1375`).

## 6. Persistence, suspend and shutdown

- Only SOC 0-100 is persisted, in the RTC spare FG byte: the daemon writes it
  (`mtk_rtc_common.c:198-228`, setter rejects >100), and
  `dod_init_in_kernel()` reads it.
- LK does not seed SOC; it clears the spare byte when entering a low-battery
  charging cycle (`lk_set_rtc_to_zero`, `LK:275-283`).
- There is no `battery_meter_reset`; the daemon issues the FGADC reset.
- Suspend arms a PMIC coulomb window from `q_max_pos_25/100 × 0x4d14`; resume
  wakes the daemon lightly below the 600 s timer.
- No kernel SOC shutdown (`DLPT_POWER_OFF_EN` undefined). `kernel_power_off`
  comes from `SET_POWEROFF` (daemon) and KPOC charger removal;
  `shutdown_system_voltage` (3100 mV) and `shutdown_gauge0/1` are exported
  constants compared in userspace.
- There is no `bat_low` flag, and the FG_20 HAL does not implement the PMIC
  low-battery status command, so the PMIC LBAT wake path is always false.

## 7. Live evidence

```
[fgauge_algo_run_get_init_data](gFG_voltage_init 4129, gFG_current_init 5234, gFG_Is_Charging_init 0)
[kernel]AvgVbat 4126, bat_vol 4126, AvgI 0, VChr 0, AvgT 24, ZCV 0, SOC 0:-100:-1
[kernel]AvgVbat 4346, bat_vol 4346, AvgI 479, I -125, VChr 4957, AvgT 23, ZCV 0, CHR_Type 1, SOC 100:100:100
```

The `-100` middle and `ZCV 0` are the not-ready state before the daemon's first
`SET_UI_SOC2`.

## 8. Limits

- Static reading only; no gauge register was read and no discharge curve was
  measured.
- The counter unit and sentinels are source-derived; wrap behaviour was not
  observed.
- The userspace estimator (`fuelgauged`/`libfgauge.so`) was not analysed; only
  the netlink interface is documented here.
- Battery profile tables are not reproduced.
- The DT-parser defect means the public board values in F16/F18 do not
  describe the running kernel; the header values above do.
