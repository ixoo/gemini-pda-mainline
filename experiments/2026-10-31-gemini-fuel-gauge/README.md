# Experiment: Gemini fuel gauge

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-fuel-gauge` |
| Status | `completed` for the static source, datasheet and boot-chain study; no runtime measurement is claimed |
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
