# Experiment: Gemini fuel gauge

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-fuel-gauge` |
| Status | `running`: the static study is complete; the mainline gauge (0367-0373) reads correctly on station 13b, capacity uncalibrated |
| Subsystem | MT6351 FGADC coulomb counter, HAFG_20 SOC algorithm, OCV/Qmax/aging tables, RTC persistence |
| Device variant | Planet Computers Gemini PDA, MT6797X, vendor Android/Gemian 3.18 stack |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | M5 power gate (battery telemetry) |

## Question or hypothesis

How does the Gemini measure charge and turn it into a state of charge, which
calibration and board parameters are actually applied, and where do the
bootloader and the kernel disagree?

The hypothesis was that the gauge is entirely MT6351-internal, that the
vendor algorithm is table-driven (OCV/Qmax by temperature), and that the
bootloader and kernel do not apply the same calibration.

## Provenance and environment

- Vendor kernel `planet-community/android_kernel_planetcom_mt6797`, commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`: `battery_meter_fg_20.c`,
  `battery_common_fg_20.c`, `power/mt6797/battery_meter_hal.c`, DT battery node.
- LK `dguidipc/gemini-lk-android8`, commit `f4988d74`: `platform/mt6797/mt_battery.c`.
- MT6351 PMIC datasheet v12 (table 2-16, section 3.2.10, FGADC register chapter).
- Retained private Gemian boot logs (gauge init and periodic telemetry).
- Prior record: [2026-10-04 charging reverse engineering](../2026-10-04-gemini-charging-re/README.md)
  (F15-F19), which owns the gauge identity and basic register set.

## Safety assessment

Read-only. No device access, no PMIC write, no discharge test. Private logs and
tables stayed outside Git; only conclusions, register offsets and a few public
anchor values are recorded.

## Procedure

1. Read the FGADC register map and specifications from the datasheet.
2. Read the kernel counter read path, Qmax/OCV/aging functions and the UI SOC
   smoothing.
3. Read the LK gauge initialisation, current scaling, per-chip trim and RTC
   spare handling.
4. Compare the board DT parameters and the two calibration paths.
5. Check the live Gemian logs for the init/telemetry shape.
6. Compare against the upstream power-supply tree.

## Observations

- [Fuel-gauge inventory](results/fuel-gauge-inventory.md) — registers, counter
  read, Qmax/OCV/aging, persistence, calibration divergence and limits.

Decisive observations:

1. The gauge is the MT6351 FGADC: 16-bit, 1/16 s, ±60 mV, with a charge
   counter read as a 17-bit slice plus a sign bit and 0/0x1ffff sentinels; each
   count is ~44.98 µAh after the OSR-8 division.
2. The **SOC estimator is userspace**: `fuelgauged`/`libfgauge.so` writes SOC,
   UI SOC, DOD, Rbat and Qmax over `NETLINK_FGD`, and the kernel republishes
   `UI_SOC2` as capacity. The in-kernel Qmax interpolator has no caller.
3. The published pack voltage is a table lookup at the reported SOC
   (`MTK_POWER_SMOOTH_SUPPORT`), not the ADC reading; UI-SOC smoothing is
   compiled out.
4. The battery DT parser is disabled and its checks are inverted, so the
   effective calibration is the header set: `CAR_TUNE 115`,
   `FG_METER_RESISTANCE 75`, NTC pull-up 2800 mV, ~96-point OCV tables — not
   the DT's 118/0/1800/82.
5. With `SWCHR_POWER_PATH` the ADC reads are swapped: the kernel's "battery
   voltage" comes from `ISENSE` (channel 1), not `BATSNS`.
6. Current uses a separate 158.122 µA LSB for `FG_CURRENT_OUT`, rescaled by
   `20/R_FG` (×2 on 10 mΩ) and `CAR_TUNE`; LK applies the factory per-chip
   trim from undocumented `0xCB8[11:7]` while the kernel hard-codes neutral,
   and LK uses `CAR_TUNE 86`.
7. The kernel persists a coarse SOC in the RTC spare byte; LK clears it on a
   low-battery charging recovery and never seeds SOC itself.
8. No kernel SOC shutdown and no `bat_low` flag: shutdown thresholds and the
   PMIC low-battery path are userspace/unimplemented.
9. Upstream has no MT6351 gauge driver; the closest power-supply drivers cover
   other PMIC families.

## Analysis

The hardware is conventional coulomb counting anchored by an OCV profile, but
the *model* is not in the kernel: a proprietary userspace daemon owns SOC,
Qmax and Rbat, and the kernel is a hardware accessor and publisher. That
changes what a mainline implementation would replace: not just a driver, but
the estimator and its OCV/Qmax tables.

Two source defects dominate the calibration picture: the battery DT parser is
disabled and inverted (so board values lost to header defaults), and the
factory per-chip trim is applied only by the bootloader. The LK/kernel
`CAR_TUNE` split (86 vs 115) is a third disagreement. Any mainline gauge
should pick one calibration path deliberately rather than copying either.

The RTC spare handoff is one-way in the bootloader (clear on recovery) and
daemon-owned otherwise, so a normal reboot preserves the coarse SOC while a
low-battery charging recovery intentionally invalidates it.

## Conclusion

`confirmed`, scoped to the vendor tree, LK tree, datasheet, vendor userspace
identities and retained logs: the counter model and units, the userspace
estimator and netlink split, the table-lookup voltage publication, the DT
parser defect, the ADC channel swap, the per-chip trim and CAR_TUNE
divergences, the RTC persistence split and the absence of an upstream driver.

Not established: the estimators inside `fuelgauged`/`libfgauge.so`, the
counter's absolute/wrap behaviour by measurement, the trim encoding, the
origin/rights of the OCV tables, and whether any of the calibration splits are
intentional.

## Follow-up

- Durable summary: [Gemini fuel gauge](../../docs/hardware/gemini-fuel-gauge.md).
- Next discriminating step: a read-only counter comparison against a known
  discharge current (for example over USB gadget load) before proposing any
  mainline gauge or power-supply integration.

## Mainline implementation (2026-10-31, owner request)

The owner cleared the calibration profiles for use in the kernel: they were
measured independently. The gauge reports what the MT6351 measures and uses
those profiles for capacity. No vendor estimator is involved.

**Read-only check on station 12** (boot `7750236b…`, regmap debugfs, no
write): LK leaves the gauge running.
- `FGADC_CON0` `0x0029`: `FG_ON` and the vendor's calibration bits;
- `FGADC_CON15` `0x0008`: OSR 8;
- `TOP_CKPDN_CON2` `0x3270`: the FGADC clocks on;
- `FG_CURRENT_OUT` `0xfdf2`: a latched value, discharging;
- `ADC25`, the AP's channel 1 result: `0xe404`, about 4219 mV, the pack
  voltage, agreeing with the BQ25896's 4.20-4.26 V.

**Patches:**
- [0367](../../patches/proposals/0367-dt-bindings-iio-adc-mt6351-auxadc-add-the-battery-vo.patch)-[0368](../../patches/proposals/0368-iio-adc-mt6359-auxadc-add-the-MT6351-battery-voltage.patch),
  the battery voltage channel:
  - channel 1 (ISENSE, the pack voltage on this power-path board);
  - the RQST0 request bit, and the AP's 15-bit result in ADC25;
  - scaled ×3 against 1.8 V.
- [0369](../../patches/proposals/0369-dt-bindings-power-supply-add-the-MediaTek-MT6351-fue.patch)-[0371](../../patches/proposals/0371-mfd-mt6397-add-the-MT6351-fuel-gauge-cell.patch),
  `mt6351-fuel-gauge`, its binding and MFD cell. It registers the
  `battery` power supply:
  - **voltage** from the channel above;
  - **current and charge counter** from one latched FGADC read, the vendor
    sequence: `0x0200` to `CON0`'s upper byte, wait for latch status bit 10,
    read, `0x0800`, wait for the bit to clear, `0x0000`. The lower byte and
    the reset bits are never written.
    - Current: 158.122 µA per count, the vendor sign rule, charging
      positive.
    - Counter: the vendor's 17-bit slice and sentinels, 44.98 µAh per step.
    - Both are scaled by 20/10 mΩ and by `CAR_TUNE` 115, the vendor
      kernel's effective value. LK uses 86, and the per-chip trim is not
      applied, as in the vendor kernel.
  - **temperature** from the `battery-thermal` zone;
  - **capacity** from the monitored battery's OCV table nearest the
    temperature, at `V − I × R`;
  - **status** from the current: ±20 mA.
- [0372](../../patches/proposals/0372-arm64-dts-mediatek-gemini-station-add-the-battery-an.patch),
  the station's `simple-battery`:
  - 4268 mAh, 3.4-4.352 V;
  - the four OCV profiles (−10, 0, 25, 50 °C; 85-94 points each, from the
    vendor `battery_profile_t0`-`t3`);
  - an internal resistance of 165 mΩ: the 25 °C profile's mid-range 90 mΩ
    plus the 75 mΩ meter path.

**Tested in the VM:**
- the station profile builds with the gauge built in;
- W=1 is clean in `drivers/power/supply`, `drivers/iio/adc` and
  `drivers/mfd`;
- the DTB carries the battery and the gauge;
- the station series tail, with the keyboard patches, applies to exactly
  that tree.

**Not tested:** any device run.

**Readings (predeclared, station 13):**

| Observation | Reading |
|---|---|
| `/sys/class/power_supply/battery` present; `voltage_now` within 50 mV of `power-status`; `temp` within 1 °C of the battery zone; `current_now` positive while charging (`charging=fast`) | The gauge reads correctly |
| `current_now` negative while the charger reads `fast` | The sign or the power-path wiring differs; the raw `FG_CURRENT_OUT` decides |
| `capacity` between 85 and 100 at 4.2 V on the charger | The OCV lookup and the I × R correction are plausible; a calibrated capacity needs a full discharge |
| `-ENODATA`, `-ETIMEDOUT` or no device | `FG_ON`, the latch or the probe order is the item; the log names it |

### Station 13, boot `66b68797…`: the gauge reads, one units bug

- **Identity:**
  - built at `dad24105` (846 patches, including keyboard 0362-0366), boot2
    `61b1218e…`;
  - `mt6351-fuel-gauge` deferred twice, then probed at 1.04 s, after the
    battery zone;
  - `/sys/class/power_supply/battery` is present. The power-supply core also
    registers a `battery` thermal zone from its temperature.
- **One read with the cable in, the charger `fast` at about 150 mA
  (REG12 `0x03`):**

  | Property | Gauge | Cross-check |
  |---|---|---|
  | `voltage_now` | 4314166 µV | BQ25896 4.32 V |
  | `temp` | 277 (27.7 °C) | battery zone 27.7 °C, `power-status` 27.8 °C |
  | `capacity` | 96 | 4.31 V near the top of the 25 °C profile |
  | `current_now` | 74 | see below |
  | `charge_counter` | 0 | see below |
  | `status` | Not charging | the charger reads `fast` |
  | `charge_full_design` | 4268000 | |

**Reading:**
- **Voltage, temperature and capacity** match the predeclared rows: within
  6 mV, within 0.1 °C, and 96 % at 4.31 V on the charger.
- **The current's sign is right,** positive while charging.
- **A units bug:** the scale helper already returns µA and µAh, and the
  callers divided by 1000 again.
  - So `current_now` read 74 mA as `74`, and `charge_counter` was under
    1 mAh.
  - The 20 mA threshold then saw a charging current as idle.
  - **Fix:** [0373](../../patches/proposals/0373-power-supply-mt6351-fuel-gauge-report-microamps-and-.patch)
    drops the second division; W=1 is clean.
  - At 74 mA the I × R correction is about 12 mV, under 1 % of capacity,
    so the capacity above stands.
- **74 mA from the gauge against about 150 mA from the charger's ICHG:**
  the charger's 50 mA steps, and the system load drawn through the power
  path, make an exact match unlikely. This is not resolved.

### Station 13b, boot `a930528e…`: the gauge works

- **Identity:** built at `1347c1ec` (0373 added), `Image.gz` `3af32c3c…`,
  boot2 `696cbc66…`, flashed with a matching readback.
- **Three reads, 5 s apart, from 12 s of uptime,** cable in; the charger
  read `fast` at 4.32 V:

  | `status` | `voltage_now` | `current_now` | `charge_counter` | `capacity` | `temp` |
  |---|---|---|---|---|---|
  | Charging | 4315814 | 114559 | −206 | 95 | 276 |
  | Charging | 4315484 | 79282 | 0 | 94 | 277 |
  | Charging | 4312188 | 72372 | 103 | 95 | 276 |

**Reading:** every predeclared row of the first table holds.
- **Current:** positive while charging, 72-115 mA as the top-off tapers.
- **Charge counter:** it steps by the expected resolution, 44.98 µAh ×
  20/10 × 1.15 = 103.4 µAh.
- **Capacity:** 94-95 % at 4.31 V on the charger.
- **Voltage and temperature** agree with the charger and the battery zone.

**Not shown:**
- a calibrated capacity, which needs a full discharge against the coulomb
  count;
- the CAR_TUNE choice (115) against a reference current;
- behaviour on battery alone.

## Charge limit (2026-10-31, owner request)

**The request:** stop charging at a set capacity, 80 % by default and
configurable, to slow the cell's aging.

**The change:** [`charge-guard`](../2026-10-30-mainline-dev-station/charge-guard.c)
(`46c7695a…`) gains a capacity stop beside its 50/47 °C window:
- it stops charging when the gauge's `capacity` reaches the limit and
  resumes 5 points below it, through the same REG03 `CHG_CONFIG` write;
- the limit is `-l` (default 80), or the number in
  `/run/station/charge-limit` whenever that file exists, read at every
  pass; 100 turns the limit off;
- an unreadable capacity does not stop charging, since only the
  temperature window is a safety stop;
- with `-q`, holding passes are no longer logged, only stops and resumes.

**Tested live on station 13b** (boot `a930528e…`), by replacing
`/bin/charge-guard` in the RAM root and letting init respawn it; the boot2
image still holds `b3eb2fb9…`:

| Step | REG03 | REG0B | `status` | `capacity` |
|---|---|---|---|---|
| New guard starts, limit 80 | `0x0a` | `0x26` | Not charging | 93 |
| `charge-limit` 100 | `0x1a` | `0x36` | Discharging | 90 |
| `charge-limit` 96, then 90 | `0x1a` | `0x36` | Discharging | 89-90 |
| File removed (80 again) | `0x0a` | `0x26` | Not charging | 92 |

- **The log shows** `action=stop full` at start, `action=resume` with
  `limit=100`, and `action=stop full` once the file was removed.
- **Limit 90 did not stop** because the capacity read 89 while the charger
  ran; that is the rule, not the hysteresis. The hysteresis itself
  (stopped, then a limit between the capacity and capacity + 5) was not
  exercised.

**An observation with charging enabled at 92 %:** the battery discharged.
- With `CHG_CONFIG` set, `current_now` read −190 to −210 mA and the battery
  fell from 4.27 to 4.20 V.
- With it clear, it read about 0 mA, and the system ran from USB.
- **Inference:** the battery sat above the charger's default 4.208 V
  regulation (REG06 `0x5e` after the watchdog restores defaults), so an
  enabled charger lets the system draw it toward that voltage. This was
  not investigated further.
- The capacity reads about 3 points lower under that load than at rest,
  so in practice the resume point sits further below the limit.

**Not shown:** a stop reached by charging up to the limit, and a resume
after discharging below it.

**At boot on station 14** (boot `42cfede4…`; built at `b2e08e97`, boot2
`65df6579…`, RAM root `a3b2486…` with `charge-guard` `46c7695a…`):
- the log's first pass, at 2 s of uptime, reads
  `cap=87 limit=80 reg03=0x0a action=stop full`;
- REG03 stays `0x0a` and `status` reads Not charging at 92 %.

The limit now survives a reboot.
