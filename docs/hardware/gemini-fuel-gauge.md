# Gemini fuel gauge

Scope: how the named MT6797X Gemini measures battery current, voltage,
temperature and state of charge, and how the vendor HAFG_20 algorithm turns
those into the reported battery state. This is a source, datasheet and
boot-chain study; no runtime measurement is claimed.

The charging-side context is in [Gemini charging](gemini-charging.md); the ADC
block itself is in [MT6351 PMIC auxiliary ADC](mt6351-pmic-adc.md). The
chronology and citations are in the
[2026-10-04 charging record](../../experiments/2026-10-04-gemini-charging-re/README.md)
(F15-F19) and the
[2026-10-31 fuel-gauge record](../../experiments/2026-10-31-gemini-fuel-gauge/README.md).

## 1. Topology

| Element | Part / interface | Role |
| --- | --- | --- |
| Coulomb counter | MT6351 FGADC, sense resistor on `CS_P`/`CS_N` | Charge and charge-time integration |
| Battery voltage | MT6351 AUXADC channel 0 (`BATSNS`, ×3) | Pack voltage and OCV/ZCV |
| Battery current (fast) | MT6351 AUXADC channel 1 (`ISENSE`, ×3) | Instantaneous current for charging policy |
| Battery temperature | MT6351 AUXADC channel 3 (`BATON`), NTC divider to VBIF28 | Temperature compensation and charge gating |
| Gauge algorithm | Vendor `battery_meter_fg_20.c` (HAFG_20) | SOC, Qmax, aging, impedance, UI smoothing |

There is no separate gauge chip: the gauge is internal to the MT6351 and is
reached through the PMIC wrapper like every other PMIC register.

## 2. FGADC hardware

Datasheet (MT6351 v12, table 2-16 and section 3.2.10): 16-bit output, 1/16 s
conversion, over-sampling ratio 2^11-2^18, input range ±60 mV, 2.8 V supply,
gain error ±2 %, accuracy 0.03 %.

Register window (PMIC offsets):

| Offset | Register | Contents |
| --- | --- | --- |
| `0x0CA4` | `FGADC_CON0` | enable, calibration, latch/read control (status bit 10), clear |
| `0x0CA6` | `FGADC_CON1` | `FG_CAR[34:19]` |
| `0x0CA8` | `FGADC_CON2` | `FG_CAR[18:3]` |
| `0x0CAA` | `FGADC_CON3` | `FG_CAR[2:0]` |
| `0x0CAC`-`0x0CB0` | `FGADC_CON4`-`CON6` | `FG_NTER[32:17]`, `[16:1]`, `[0]` |
| `0x0CBA` | `FGADC_CON11` | `FG_CURRENT_OUT[15:0]` |
| `0x0CC2` | `FGADC_CON15` | OSR and filter control |
| `0x0CD6` | `FGADC_CON25` | `FG_R_CURR` (resistance/IM path) |
| `0x02D4`/`0x02E6` | `FG_BAT_H`/`FG_BAT_L` interrupt enable/status | battery voltage comparator interrupts |

The counter is 35-bit (`FG_CAR`) and has a matching 33-bit time counter
(`FG_NTER`), so the hardware integrates both charge and elapsed time. Reading is
a latched transaction: the driver writes the read command into `FGADC_CON0`,
polls the latch status, reads `FG_CAR`/`FG_NTER`/`FG_CURRENT_OUT`, and clears
the latch.

The current LSB is `158.122 µA` for a 20 mΩ sense base, rescaled by
`20 / R_FG_VALUE` and by `CAR_TUNE_VALUE / 100`; the board uses a 10 mΩ sense
resistor, so the effective LSB is doubled before the tune factor.

## 3. Board and calibration parameters

The board DT (`mt6797.dtsi` battery node, public tree) sets:

| Parameter | Value | Meaning |
| --- | --- | --- |
| `r_fg_value` | 10 mΩ | battery sense resistor |
| `car_tune_value` | 118 | current gain correction in the kernel |
| `cust_r_sense` | 56 (0.01 Ω) | charger-current sense resistor |
| `fg_meter_resistance` | 0 | meter resistance compensation disabled |
| `q_max_pos_25` | 2707 mAh | design capacity at 25 °C (public table) |
| `temperature_t0..t3` | 110 / 0 / 25 / 50 | profile anchor temperatures |
| `rbat_pull_up_r` / `_volt` | 24 kΩ / 1800 mV | NTC divider for channel 3 |
| `vbat_low_power_wakeup` | 3500 mV | low-battery wake threshold |

The same tree also carries four OCV/capacity profiles (82 points each) and the
Qmax table variants. Those tables are vendor calibration; this document records
their shape only.

## 4. Boot-chain behaviour

- The **preloader** has no fuel-gauge code or strings.
- **LK** initialises the FGADC, reads current through the latched
  `FG_CURRENT_OUT` transaction, applies the sign, the 158.122 µA LSB, the
  `R_FG_VALUE` rescale, the board slope, a `CAR_TUNE_VALUE` of **86**, and a
  **per-chip gain trim** read from the undocumented register `0xCB8[11:7]`
  before handing over the boot-time battery state. It does not store SOC
  itself; instead it clears the RTC spare FG byte (`RTC_AL_HOU` upper bits) when
  it enters a low-battery charging cycle.
- The **kernel** uses the same trim table but hard-codes the trim selector to
  **0**, i.e. a neutral 1000, so the factory per-chip trim is applied by LK and
  ignored by Linux. The kernel does persist a coarse SOC in the RTC spare FG
  value (`get/set_rtc_spare_fg_value`).
- The **kernel** uses the same trim table but hard-codes the trim selector to
  **0**, i.e. a neutral 1000, so the factory per-chip trim is applied by LK and
  ignored by Linux.
- LK's current tune (86) and the kernel's `car_tune_value` (118) differ by
  about 27 %; the bootloader and the kernel are not using the same current
  calibration.

These are source facts; whether the divergence matters in practice depends on
which current consumer is compared (bootloader charge decisions vs kernel
SOC/charge policy).

## 5. Live evidence

The retained Gemian boot logs show the gauge initialisation and the published
values:

```
[fgauge_algo_run_get_init_data](gFG_voltage_init 4129, gFG_current_init 5234, gFG_Is_Charging_init 0)
[kernel]AvgVbat 4126, bat_vol 4126, AvgI 0, I 0, VChr 0, AvgT 24, ZCV 0, CHR_Type 0, SOC 0:-100:-1
...
[kernel]AvgVbat 4346, bat_vol 4346, AvgI 479, I -125, VChr 4957, AvgT 23, ZCV 0, CHR_Type 1, SOC 100:100:100
```

`gFG_voltage_init`/`gFG_current_init` are the first FG readings, the `-100`
middle SOC is the "not ready" sentinel (also `ZCV 0`), and the triple becomes
valid once the gauge has data. This is consistent with the recorded SOC
pipeline but is not a calibration measurement.

## 6. SOC algorithm

The vendor HAFG_20 pipeline is documented in the
[fuel-gauge inventory](../../experiments/2026-10-31-gemini-fuel-gauge/results/fuel-gauge-inventory.md):

- initial SOC from the OCV/ZCV profile at the measured pack voltage and
  temperature;
- coulomb counting from the 35-bit counter, with the sign and `CAR_TUNE`
  scaling above;
- Qmax interpolation between temperature anchors, with the aging-factor table
  applied by cycle count;
- ZCV and tracking-point refresh for the 15 % capacity anchor;
- UI SOC smoothing before publication;
- persistence across reboot through the kernel's RTC spare FG value, with LK
  clearing it on a low-battery charging recovery.

The exact functions, units and control flow are in the inventory; the battery
profile tables themselves stay private (vendor calibration with unestablished
redistribution rights).

## 7. Shutdown and low-battery handling

- `shutdown_system_voltage`, `shutdown_gauge0`/`1` and
  `vbat_low_power_wakeup` (3500 mV) come from the board DT.
- The battery task publishes `bat_low`/`bat_full` flags to the power-supply
  class and triggers the shutdown path at the configured gauge/SOC/voltage
  conditions.
- The kernel power-off charging path is separate (see
  [Gemini charging](gemini-charging.md)).

## 8. Mainline position

Upstream Linux 7.1.3 has **no MT6351 fuel-gauge driver**. The PMIC is only an
MFD/regulator child, and `drivers/power/supply` contains MT6360/MT6370 charger
drivers but no MT6351 gauge. A mainline implementation would need:

- a regmap over the PMIC wrapper for the `FGADC_*` window;
- the latched counter transaction and the 35-bit accumulation;
- the OCV/ZCV and Qmax tables (vendor calibration, not redistributable as-is);
- a policy decision on the per-chip trim and `CAR_TUNE` value;
- a power-supply device that exposes voltage, current, temperature and capacity
  without pretending the vendor SOC model is portable.

## 9. Open questions

1. Which SOC value the UI actually consumes on Gemian (`0:-100:-1` sentinel vs
   the published triple) and when the middle value becomes valid.
2. Whether the LK/kernel `CAR_TUNE` divergence (86 vs 118) is intentional or a
   stale bootloader constant.
3. The purpose and encoding of the undocumented per-chip trim register
   `0xCB8[11:7]` and why the kernel disables it.
4. Whether the coulomb counter is readable across suspend without loss, and
   what the RTC spare handoff actually restores.
5. The origin and redistribution rights of the four OCV profiles.

## Evidence index

- Vendor kernel commit `8cfe6596a503612e3332d9c26e292a19525a7f07`;
  `battery_meter_fg_20.c`, `battery_common_fg_20.c`,
  `power/mt6797/battery_meter_hal.c`, DT battery node.
- LK commit `f4988d74bb70a0a15d7f362f412afba7e7fcda46`;
  `platform/mt6797/mt_battery.c`.
- MT6351 PMIC datasheet v12, table 2-16, section 3.2.10 and the FGADC register
  chapter.
- Retained private Gemian boot logs (gauge init and periodic telemetry).
- [2026-10-04 charging record](../../experiments/2026-10-04-gemini-charging-re/README.md),
  [2026-10-31 fuel-gauge record](../../experiments/2026-10-31-gemini-fuel-gauge/README.md).
