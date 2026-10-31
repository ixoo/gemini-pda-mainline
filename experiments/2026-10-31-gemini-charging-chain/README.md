# Experiment: Gemini charging logic across the boot chain and kernel

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-charging-chain` |
| Status | `completed` for the static source, datasheet and firmware study; no hardware behaviour is claimed |
| Subsystem | BQ25896 switch charger, MT6351 BC1.1 detection, charge state machine, thermal current limits, boot-chain policy |
| Device variant | Planet Computers Gemini PDA, MT6797X, vendor Android/Gemian 3.18 stack |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | M5 power gate (charging protection) |

## Question or hypothesis

How does the vendor stack actually decide to charge, at what current and
voltage, when to stop, and when to reduce current for heat — from the
bootloader through the kernel state machine — and which of those decisions are
thermal rather than electrical?

The hypothesis was that the visible charger configuration (already recorded in
the [2026-10-04 charging record](../2026-10-04-gemini-charging-re/README.md))
is only half the logic: the state machine, the boot-chain policy and three
independent thermal gates carry the rest.

## Provenance and environment

- Vendor kernel `planet-community/android_kernel_planetcom_mt6797`, commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`. Built charging path:
  `drivers/power/mediatek/switch_charging.c` and
  `battery_common_fg_20.c`, `drivers/misc/mediatek/power/mt6797/`
  (`bq25890.c`, `charging_hw_bq25890.c`, `pmic_chr_type_det.c`), PE+ 1.0 in
  `drivers/power/mediatek/mtk_pep_intf.c`.
- Bootloader `dguidipc/gemini-lk-android8`, commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`: `platform/mt6797/bq25890.c`,
  `mt_battery.c`, `atags.c`.
- Retained private preloader, LK, SCP/TEE/modem images; TI BQ25896 datasheet;
  MT6351 PMIC datasheet; Android `.tp` thermal policy.
- Prior record: [2026-10-04 charging reverse engineering](../2026-10-04-gemini-charging-re/README.md)
  owns the charger identity, register configuration (F11), per-type current
  table (F12), fuel gauge and mainline gap. This record does not repeat them.

## Safety assessment

Read-only. No device access, no charger write, no boot candidate. Private
firmware and documents stay outside Git; only conclusions and short public
source citations are recorded.

## Procedure

1. Read the built kernel charging algorithm, its state machine, timers and
   full/recharge logic.
2. Trace every thermal input that can change charge current or enable state.
3. Read the LK charger driver init, BC1.2 implementation and low-battery boot
   policy; scan the preloader for the same stages.
4. Reconcile with the BQ25896 datasheet limits and the recovered `.tp` policy.
5. Compare against the earlier record and the mainline 7.1.3 tree.

## Observations

- [Charging chain inventory](results/charging-chain.md) — boot chain, state
  machine, thermal gates and safety limits with citations.

The decisive observations:

1. The kernel algorithm is a five-state loop (`CHR_PRE`, `CHR_CC`,
   `CHR_BATFULL`, `CHR_HOLD`, `CHR_ERROR`) driven every battery-task period; it
   kicks the charger watchdog, runs AICL, starts PE+ in pre-charge and decides
   "full" in software because hardware termination is disabled.
2. LK charges before Linux exists: it initialises the BQ25896 (2.048 A, 4.352 V,
   128 mA pre-charge and termination, 3.25 A input, 4.5 V VINDPM), runs BC1.2
   through the MT6351, and holds the device in a low-battery loop until the
   battery reaches 3450 mV (3200 mV without a charger means power-off).
3. The preloader has no BQ25896 driver; it runs BC1.2, checks VBAT/VCHR and
   relies on the charger's power-on defaults until LK takes over.
4. There are three independent thermal gates: the battery NTC window (high
   gate 50 °C, low gate disabled by DT), a PCB-temperature charger-current
   limiter at 42/44/45 °C that only runs with the backlight on, and the
   thermal-zone `bcct`/`abcct` coolers from the `.tp` policy.
5. The PCB limiter has a duplicated `else if` branch, so its level 2 is
   unreachable, and a level 4 with no explicit current mapping.
6. Hardware JEITA is configured but the board's TS input is a fixed divider, so
   the real temperature protection is software (battery NTC and `.tp`).

## Analysis

The charging path is layered rather than a single policy: the bootloader
guarantees a chargeable battery and a safe current, the kernel algorithm
selects current/voltage by cable type and PE+ state, and thermal protection is
split between the battery NTC gate, the PCB limiter and the thermal framework.
That split matters for a mainline port: reproducing only the register
configuration would leave the current limiter and the `.tp` gates absent, and
reproducing only a generic `bq25890_charger` would leave the NTC window and
charge-enable policy absent.

The unreachable limiter branch and the unhandled level 4 are vendor defects
worth recording because a naive port that copies the function would copy them.

## Conclusion

`confirmed`, scoped to the vendor sources, LK tree, datasheet and retained
images above: the state machine, boot-chain policy, three thermal gates,
safety timers and the preloader/LK division of labour.

Not established: which `.tp` policy a given SKU selects, whether the live
BQ25896 TS input is truly a fixed divider on every Gemini variant, and any
runtime current/voltage measurement in this study.

## Follow-up

- Durable summary: [Gemini charging](../../docs/hardware/gemini-charging.md).
- Next discriminating step: read the BQ25896 status/fault registers and the
  battery NTC while charging on the station, then compare against the three
  gates above before any mainline charging patch.
