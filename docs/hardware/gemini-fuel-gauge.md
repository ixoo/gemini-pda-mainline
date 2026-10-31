# Gemini fuel gauge

Scope: how the named MT6797X Gemini counts charge, where the state-of-charge
model actually runs, and which calibration reaches the hardware. This is a
source, datasheet, boot-chain and vendor-userspace study; no runtime
measurement is claimed.

Related: [Gemini charging](gemini-charging.md),
[MT6351 PMIC auxiliary ADC](mt6351-pmic-adc.md), and the evidence records
[2026-10-04 charging](../../experiments/2026-10-04-gemini-charging-re/README.md)
(F15-F19) and
[2026-10-31 fuel gauge](../../experiments/2026-10-31-gemini-fuel-gauge/README.md).

## 1. Topology

| Element | Part / interface | Role |
| --- | --- | --- |
| Coulomb counter | MT6351 FGADC, sense resistor on `CS_P`/`CS_N` | Charge and charge-time integration |
| Pack voltage / current ADC | MT6351 AUXADC channels 0/1 (`BATSNS`/`ISENSE`, ×3) | Voltage and fast current readings |
| Battery temperature | MT6351 AUXADC channel 3 (`BATON`), NTC divider | Temperature for compensation and gating |
| **SOC estimator** | **vendor userspace `fuelgauged` + `libfgauge.so`**, via `NETLINK_FGD` (26) | SOC, UI SOC, DOD, Rbat, Qmax |
| Kernel gauge layer | `battery_meter_fg_20.c` / `battery_common_fg_20.c` | Hardware access, fallback init, `power_supply` publication |

The hardware is entirely MT6351-internal, but the **estimator is not in the
kernel**: the kernel reads the counter and publishes values that the userspace
daemon writes back over netlink.

A build detail matters for the voltage path: with `SWCHR_POWER_PATH` (the
BQ25896 configuration) the two ADC readings are **swapped** — `read_adc_v_bat`
uses `ISENSE` (channel 1) and `read_adc_v_i_sense` uses `BATSNS` (channel 0)
(`battery_meter_hal.c:1115-1145`).

## 2. FGADC hardware and counter

Datasheet (MT6351 v12, table 2-16 and section 3.2.10): 16-bit output, 1/16 s
conversion, over-sampling 2^11-2^18, input ±60 mV, 2.8 V supply, gain error
±2 %, accuracy 0.03 %. The vendor driver uses `FG_OSR = 8`.

| Offset | Register | Contents |
| --- | --- | --- |
| `0x0CA4` | `FGADC_CON0` | enable/calibration/latch control (status bit 10, clear) |
| `0x0CA6`-`0x0CAA` | `CON1`-`CON3` | `FG_CAR[34:19]`, `[18:3]`, `[2:0]` |
| `0x0CAC`-`0x0CB0` | `CON4`-`CON6` | `FG_NTER[32:17]`, `[16:1]`, `[0]` |
| `0x0CBA` | `CON11` | `FG_CURRENT_OUT[15:0]` |
| `0x0CC2` | `CON15` | OSR/filter control |
| `0x0CD6` | `CON25` | `FG_R_CURR` |
| `0x0CB8` | undocumented | per-chip gain trim at bits 11:7 |
| `0x02D4`/`0x02E6` | `FG_BAT_H/L` | battery voltage comparator interrupts |

The kernel does not read the full 35-bit value as a plain number. It forms a
17-bit slice and takes the sign separately
(`battery_meter_hal.c:930-934`):

```
raw   = (FG_CAR[18:3] >> 11) | ((FG_CAR[34:19] & 0xFFF) << 5)
sign  = FG_CAR[34:19] bit 15            /* 1 = discharging */
zero  if raw == 0 or raw == 0x1ffff     /* sentinels */
value = raw, or (0x1ffff - raw) when discharging
```

Each count is `359.86 µAh`, divided by the OSR 8 → **≈44.98 µAh per count**,
then rescaled by `20 / r_fg_value` (×2 on this 10 mΩ board), by
`car_tune_value / 100`, and by the per-chip trim
(`battery_meter_hal.c:1005-1050`). Maximum magnitude is about 2.95 Ah. The
counter free-runs; only an explicit hardware reset clears it, and reads just
pulse the software latch.

The instantaneous current register is separate: `FG_CURRENT_OUT` uses a
**158.122 µA LSB** for a 20 mΩ base (`battery_meter_hal.c:36`), with the same
r_fg/car_tune/trim rescaling. This LSB does not apply to the counter.

## 3. Calibration and the device-tree defect

The board DT carries charger and gauge values, but the gauge parser is
**unreachable**: `batt_meter_init_cust_data()` returns the compile-time header
path and the DT path is commented out
(`battery_meter_fg_20.c:1330-1338`). Its property reads are also inverted
(`__batt_meter_init_cust_data_from_dt`), so even if it ran the values would not
land.

Consequently the effective values are the header defaults, not the DT:

| Parameter | DT value | Header value (effective) |
| --- | --- | --- |
| sense resistor `R_FG_VALUE` | 10 mΩ | 10 mΩ |
| `CAR_TUNE_VALUE` | 118 | **115** |
| `FG_METER_RESISTANCE` | 0 | **75** |
| NTC pull-up voltage | 1800 mV | **2800 mV** |
| OCV / Qmax profiles | 82 points | **~96 points** from the header tables |

The per-chip gain trim is read from undocumented `0xCB8[11:7]` and applied by
**LK**; the kernel hard-codes the trim selector to 0 (neutral 1000)
(`battery_meter_hal.c:61-130`). LK also uses `CAR_TUNE_VALUE = 86`
(`LK mt_battery.c:522`) against the kernel's effective 115, so the bootloader
and Linux scale the same current differently.

Temperature has another quirk: a `BATON` reading above 2600 mV forces 20 °C and
skips the NTC table (`battery_meter_fg_20.c:1345-1375`).

## 4. SOC pipeline

- The userspace daemon owns the estimator: the kernel accepts
  `FG_DAEMON_CMD_SET_SOC`, `SET_UI_SOC2`, `SET_QMAX` and `SET_RBAT`
  (`battery_meter_fg_20.c:4481-4590`) and republishes
  `BAT_CAPACITY = UI_SOC2` (`battery_common_fg_20.c:1653`).
- Publication is gated on `g_battery_soc_ready`, set only by the first
  `SET_UI_SOC2`; before that the capacity stays at `-1` (the `-100` in the log
  triple is the raw not-ready sentinel).
- In-kernel fallbacks exist for the first boot and for recovery:
  `fgauge_algo_run_get_init_data()` reads the initial voltage/current, and
  `dod_init_in_kernel()` reconciles the RTC spare SOC, a software SOC and the
  hardware SOC.
- **Published voltage is a table lookup, not the ADC reading.**
  `MTK_POWER_SMOOTH_SUPPORT` is defined, so `battery_update()` replaces the
  pack voltage with `fgauge_read_v_by_capacity(100 - UI_SOC2, temperature)`
  (`battery_common_fg_20.c:1645-1710`).
- `battery_meter_smooth_uisoc2()` is compiled out (`USING_SMOOTH_UI_SOC2`
  undefined), and `nPercent_ZCV` is a constant 3700 mV: `gFG_15_vlot` is never
  recomputed.
- The in-kernel `fgauge_get_Q_max()` interpolator (anchors −10/0/25/50 °C) has
  **no caller** in the built path. Runtime Qmax is the daemon's
  `gFG_BATT_CAPACITY_aging`, default 1200 mAh and otherwise supplied by
  `SET_QMAX`. The kernel aging state and the DT `aging_*` values are inert.

## 5. Persistence, suspend and boot

- Only a coarse SOC (0-100) is persisted, in the RTC spare byte: the daemon
  writes it, `dod_init_in_kernel()` reads it back.
- LK does not seed SOC; when it enters a low-battery charging recovery it
  clears the spare byte (`lk_set_rtc_to_zero`), so a stale value does not
  survive that path.
- Suspend arms a PMIC coulomb window derived from `q_max_pos_25/100 × 0x4d14`
  and resumes with a light daemon wake below the 600 s timer; there is no
  kernel SOC shutdown.
- Shutdown and low-battery policy are userspace decisions
  (`SET_POWEROFF`); `shutdown_system_voltage` (3100 mV) and
  `shutdown_gauge0/1` are exported constants, not kernel comparisons. There is
  no `bat_low` flag, and the FG_20 HAL does not implement the PMIC low-battery
  status command, so that wake path is always false.

## 6. Live evidence

Retained Gemian boot logs show the fallback init and the not-ready state:

```
[fgauge_algo_run_get_init_data](gFG_voltage_init 4129, gFG_current_init 5234, gFG_Is_Charging_init 0)
[kernel]AvgVbat 4126, bat_vol 4126, AvgI 0, VChr 0, AvgT 24, ZCV 0, SOC 0:-100:-1
[kernel]AvgVbat 4346, bat_vol 4346, AvgI 479, I -125, VChr 4957, AvgT 23, ZCV 0, CHR_Type 1, SOC 100:100:100
```

The `-100` middle value and `ZCV 0` clear once the daemon has run. This
confirms the init/notification shape, not a calibration.

## 7. Mainline position

Upstream Linux 7.1.3 has no MT6351 gauge driver; `drivers/power/supply`
contains MT6360/MT6370 chargers only. A mainline implementation would need:

- a wrapper regmap and the latched counter/current transaction;
- a decision on the 17-bit slice, sentinels and 44.98 µAh unit;
- the OCV/Qmax/aging model, which on this product lives in a proprietary
  userspace daemon (`fuelgauged`, `libfgauge.so`) and is not portable;
- an explicit choice of `CAR_TUNE` and chip trim, which currently disagree
  between LK and the kernel;
- a power-supply presentation that does not present a table lookup as a
  measured voltage.

## 8. Open questions

1. What `fuelgauged`/`libfgauge.so` actually implement: the netlink protocol is
   visible, the estimator is not.
2. Whether `CAR_TUNE = 115` (kernel header), `118` (unused DT) or `86` (LK) is
   the intended board calibration.
3. The encoding and purpose of the undocumented `0xCB8[11:7]` trim and why the
   kernel disables it.
4. Why the battery DT parser is disabled and inverted, and which values the
   live DTB would have supplied.
5. Counter wrap/absolute behaviour across a full discharge, and the real effect
   of the 2600 mV `BATON` clamp.

## Evidence index

- Vendor kernel commit `8cfe6596a503612e3332d9c26e292a19525a7f07`:
  `battery_meter_fg_20.c`, `battery_common_fg_20.c`,
  `power/mt6797/battery_meter_hal.c`, DT battery node.
- LK commit `f4988d74bb70a0a15d7f362f412afba7e7fcda46`:
  `platform/mt6797/mt_battery.c`.
- Vendor userspace: `fuelgauged`, `libfgauge.so` in
  `planet-community/android_vendor_planetcom_geminipda` (proprietary blobs;
  behaviour not analysed here).
- MT6351 PMIC datasheet v12 (table 2-16, section 3.2.10, FGADC chapter).
- Retained private Gemian boot logs.
- [2026-10-04 charging record](../../experiments/2026-10-04-gemini-charging-re/README.md),
  [2026-10-31 fuel-gauge record](../../experiments/2026-10-31-gemini-fuel-gauge/README.md).
