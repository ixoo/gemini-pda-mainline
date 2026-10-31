# Charging chain inventory

Scope: the built vendor kernel charging path, the LK bootloader and the
retained preloader for the named Gemini PDA. Kernel paths are relative to
vendor commit `8cfe6596`; LK paths to `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
The earlier [2026-10-04 record](../../2026-10-04-gemini-charging-re/README.md)
owns charger identity (F1), the register configuration (F11), the per-type
current table (F12), BC1.1 as implemented in the kernel (F6) and the fuel
gauge (F15-F19).

## 1. Boot chain

### Preloader (private image)

- String set shows the BC1.2 sequence (`step A1 : Apple 2.1A CHARGER!`,
  `step A1 : Non STANDARD CHARGER!`, `step B2 : STANDARD CHARGER!`,
  `step B2 : Charging Host!`) and the battery decisions
  (`check VBAT=%d mV with %d mV, VCHR %d mV,VCHR_HV=%d start charging`,
  `charger voltage is too high`, `charging current and charger volt too low`).
- It contains no BQ25896 or `bq` strings, so it does not drive the external
  charger over I2C. Until LK runs, the charger operates on its power-on
  defaults (2.048 A, 4.208 V, EN_TERM set, 12 h timer), which is what the live
  register dump also shows when no kernel driver is bound.
- The image is ARM32 Thumb-2; its ADC/charger strings are not reachable by a
  simple literal scan, so exact thresholds are not decoded here.

### LK

- `bq25890_hw_init()` (`lk/platform/mt6797/bq25890.c:767-805`): watchdog
  reset, OTG off, safety timer enabled, `ITERM=0x2`, `VREG=0x20` (4.352 V),
  `VCLAMP=0x7` (+224 mV), IR compensation 80 mΩ, `BATLOWV` 3.0 V,
  `IPRECHG=0x1` (128 mA), `ICHG=0x20` (2048 mA), `IINLIM=0x3F` (3.25 A),
  absolute `VINDPM=0x13` (4.5 V), HIZ off.
- `hw_charging_get_charger_type()`
  (`lk/platform/mt6797/bq25890.c:871-1116`) runs the MT6351 BC1.1 sequence
  (DCD, A1, B2) through `RG_BC11_*` registers and classifies standard host,
  charging host, standard charger, non-standard and Apple 2.1 A.
- Type mapping to input limit (`:820-860`): standard charger → 2 A when the
  large-current flag is set, otherwise 1.2 A; host/non-standard → 500 mA; the
  charger is enabled only after the limit is set.
- `check_bat_protect_status()` (`lk/platform/mt6797/mt_battery.c:286-380`):
  while `VBAT < 3450 mV` it restarts the watchdog, powers off if no charger is
  present and battery is below 3200 mV, rejects charger voltage above
  `V_CHARGER_MAX`, checks battery presence through `BATON` (`RGS_BATON_UNDET`),
  enables charging, zeroes the RTC, and powers off if eight consecutive polls
  show current < 100 mA and charger voltage < 4400 mV.
- `mt65xx_bat_init()` (`:385-500`) enables charging first, then reads charger
  voltage and decides between booting and kernel power-off charging; the
  power path is disabled and re-enabled around the IMIX measurement.

## 2. Kernel state machine

`mt_battery_charging_algorithm()` (`drivers/power/mediatek/switch_charging.c:1258-1295`)
runs every battery-task period and does, in order: kick the charger watchdog
(`CHARGING_CMD_RESET_WATCH_DOG_TIMER`), run AICL unless PE+ is connected, run
the PE+ check, dispatch the state, and dump the charger registers.

| State | Action (function) | Exit |
| --- | --- | --- |
| `CHR_PRE` | `BAT_PreChargeModeAction()` (`:1062-1120`): enable charger, restart PRE timer, set LED on | UI SOC 100 and full check → `CHR_BATFULL`; `V_PRE2CC_THRES` exceeded → `CHR_CC` |
| `CHR_CC` | `BAT_ConstantCurrentModeAction()` (`:1123-1146`): enable charger, increment CC timer | full check → `CHR_BATFULL` |
| `CHR_BATFULL` | `BAT_BatteryFullAction()` (`:1149-1195`): LED off, reset timers, re-select CV | full check false → recharging, back to `CHR_CC` |
| `CHR_HOLD` | `BAT_BatteryHoldAction()` (`:1198-1219`): charger disabled for talking | `VBAT < TALKING_RECHARGE_VOLTAGE` or call idle → `CHR_CC` |
| `CHR_ERROR` | `BAT_BatteryStatusFailAction()` (`:1222-1256`): charger off, PE+ reset | only after error clears (JEITA recovery or battery status) |

`charging_full_check()` (`:629-646`) asks the charger for its status and
requires `FULL_CHECK_TIMES` consecutive "full" readings. With `EN_TERM = 0`
(F11) the chip does not terminate by itself, so the vendor also uses gauge
current (`charging_full_current = 100 mA`), `v_cc2topoff_thres = 4050 mV` and
`recharging_voltage = 4110 mV` from the DT (F13).

PE+ 1.0 (`drivers/power/mediatek/mtk_pep_intf.c`): started from pre-charge,
first target 7 V with 3 retries and ±1 V tolerance (`:192-245`), then the
higher steps recorded in F8, exit resets the adapter to the original voltage
(`:310-340`). PE+ raises the allowed charge/input current (F8).

## 3. Thermal gates

Three independent mechanisms feed the charging decision; only one lives in the
charger driver.

1. **Battery NTC window** (`battery_common_fg_20.c:1958-2010`,
   `do_batt_temp_state_machine`): `T >= max_charge_temperature` (50 °C) fails
   the charge check; recovery below `max_charge_temperature_minus_x_degree`
   (47 °C) returns to pre-charge. The low-temperature gate only runs when
   `bat_low_temp_protect_enable` is set; the retained DT has it at 0, so
   low-temperature charging is not blocked on this unit.
2. **PCB limiter** (`switch_charging.c:668-700`, `hw_charger_limit_status`):
   reads `mtk_thermal_get_temp(MTK_THERMAL_SENSOR_AP)` — the board NTC — and
   returns a level: <42 °C → 0, <44 °C → 1, `<44 °C` again → 2 (duplicated
   branch, unreachable), ≤45 °C → 3, else 4. It returns 0 when the backlight
   is below 5. Levels 1/2/3/other map to charge-current caps 1500/1400/1350/
   1300 mA (900/800/700/650 mA with PE+ or VBUS above 6 V) in
   `pchr_turn_on_charging()` (`:968-1060`). Level 4 has no explicit mapping and
   falls into the most restrictive branch.
3. **Thermal-zone coolers** (`.tp` policy, see the
   [thermal document](../../../docs/hardware/mt6797-thermal-management.md)):
   battery-zone trips at 46/47/48 °C drive `mtk-cl-bcct00/01/02`, which call
   the charger-limiter API `set_bat_charging_current_limit()` /
   `set_chr_input_current_limit()` (`switch_charging.c:382-500`,
   `thermal/common/coolers/mtk_cooler_bcct.c:204-210`); the board zone gates
   `abcct` at 47 °C and the LCD-off variant at 56 °C.

## 4. Hardware limits and the datasheet

BQ25896 (TI SLUSC76C):

- default input limit 3.25 A, default charge current 2.048 A, default VREG
  4.208 V, default pre-charge 128 mA, default termination 256 mA;
- I2C watchdog default 40 s after power-on; once it expires the device returns
  to default mode, which is why the kernel kicks it every battery period and
  LK resets it on entry;
- safety timer 12 h in fast charge (4 h below `VBATLOWV`), halved during input
  or thermal regulation, `CHRG_FAULT = 11` on expiry;
- JEITA via TS thresholds with current/voltage derating bits in REG07/REG09;
  the vendor enables JEITA (`JEITA_ISET = 1`, `JEITA_VSET = 0`), but the live
  TS register has read a fixed `0x3e` across many sessions, consistent with a
  fixed divider rather than a thermistor, so hardware JEITA does not trip;
- `EN_TERM = 0` in the vendor kernel, so termination is a software decision;
  `CHRG_STAT` still reports the chip's own state for the full check.

## 5. Safety and presence

- Charger presence is the MT6351 `CHRDET` comparator, not the charger's PG pin
  (F4); the PMIC external interrupt is EINT176 (F5).
- Battery presence is checked through the PMIC `BATON` detection
  (`RGS_BATON_UNDET`) in LK and by the gauge in the kernel.
- VBUS over-voltage: `charging_set_hv_threshold()` / `RG_VCDT_HV_EN` (F9),
  with `V_CHARGER_MAX = 6500 mV` outside PE+.
- LK enforces the 4.4 V/100 mA "charger not delivering" rule and powers off.
- A vendor `BATFET_DIS` workaround exists for the RT5735 SDA-low fault (F14).

## 6. Limits

- Static reading only; no charger register was written or read in this study.
- Preloader thresholds are not decoded (ARM32 image, non-linear layout).
- The live DTB differs from the public DTS (F2), so public board values are
  not authoritative for the unit.
- Which `.tp` policy a SKU selects, and the exact effect of `clbcct` parameters,
  remain unresolved.
