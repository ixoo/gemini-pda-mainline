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

1. The gauge is the MT6351 FGADC: 16-bit, 1/16 s, ±60 mV, with a 35-bit charge
   counter (`FG_CAR`) and a 33-bit charge-time counter (`FG_NTER`), read with a
   latch transaction through `FGADC_CON0`.
2. Current uses a 158.122 µA LSB for a 20 mΩ base, rescaled by
   `20 / R_FG_VALUE` (×2 on this 10 mΩ board) and by `CAR_TUNE / 100`.
3. Qmax is interpolated across temperature anchors and corrected by an aging
   table; OCV is a four-profile, 82-point table with ZCV tracking.
4. The kernel persists a coarse SOC in the RTC spare byte; LK clears that byte
   when entering a low-battery charging cycle instead of storing its own.
5. LK applies the factory per-chip gain trim from the undocumented
   `0xCB8[11:7]`; the kernel hard-codes the neutral trim, and LK's
   `CAR_TUNE = 86` differs from the kernel DT's 118.
6. Battery temperature is the PMIC `BATON` NTC, not a gauge sensor; shutdown
   and wake thresholds come from the board DT.
7. Upstream has no MT6351 gauge driver; the closest power-supply drivers cover
   other PMIC families.

## Analysis

The measurement chain is conventional coulomb counting anchored by an OCV
profile, but the product depends heavily on vendor calibration: the OCV
profiles, Qmax tables, aging curve and per-chip trim are the actual model, and
none of them is a portable hardware constant. The LK/kernel divergence is the
most concrete finding: the same physical current is scaled differently in the
two stages, and the factory trim is applied only in the bootloader. That is
consistent with the bootloader using its own conservative charge decisions and
the kernel relying on its own `CAR_TUNE`; it also means any mainline gauge
should not blindly copy either constant.

The RTC spare handoff is one-way in the bootloader (clear on recovery) and
kernel-owned otherwise, so a reboot without charging preserves the coarse SOC
but a low-battery recovery intentionally invalidates it.

## Conclusion

`confirmed`, scoped to the vendor tree, LK tree, datasheet and retained logs:
the FGADC register model, counter read path and units, the Qmax/OCV/aging
structure, the RTC persistence split, the per-chip trim divergence and the
absence of an upstream driver.

Not established: the counter's absolute/wrap behaviour by measurement, the
true encoding of the undocumented trim register, the origin/rights of the OCV
profiles, and whether the LK/kernel tune difference is intentional.

## Follow-up

- Durable summary: [Gemini fuel gauge](../../docs/hardware/gemini-fuel-gauge.md).
- Next discriminating step: a read-only counter comparison against a known
  discharge current (for example over USB gadget load) before proposing any
  mainline gauge or power-supply integration.
