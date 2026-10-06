# Experiment: C2b charger profile with a verified charge start

| Field | Value |
| --- | --- |
| ID | `2026-10-06-gemini-c2b-charger` |
| Status | Built; candidate DT derivation and protocol draft ready for review; interrupt semantics await a Gemian check; not booted |
| Profile | `mt6797-a53-c2b-charger-compile` |
| Date | 2026-10-06 |
| Device action | None |

## Purpose

Roadmap step C2b binds `bq25890` only after a reviewed sequence programs and
verifies 4.2 V and 500 mA before charging starts. The
[driver review](../2026-10-04-gemini-charging-re/DRIVER_REVIEW.md) found that
the unmodified driver cannot do that, and that the charger interrupt wiring is
unknown. This experiment implements the review's smallest change and narrows
the interrupt question.

## Driver change

[c2b/0002](../../patches/v7.1.3/c2b/0002-power-supply-bq25890-add-an-opt-in-verified-charge-start.patch)
adds an opt-in `linux,verified-charge-start`, valid only with
`linux,skip-reset`. At probe it:

1. writes `CHG_CONFIG=0` before anything else;
2. disables the watchdog and writes the limits, as before;
3. writes `linux,verified-input-current-limit-microamp` to `IINLIM`, and
   clears `ICO_EN` and `AUTO_DPDM_EN` so the chip's own detection and
   optimiser cannot raise it;
4. reads back every written field (17 in all) and fails probe on any mismatch,
   leaving charging disabled;
5. only then writes and reads back `CHG_CONFIG=1`.

Afterwards the input-limit property refuses values above the verified limit.
Without the property the driver behaves exactly as before.
[c2b/0001](../../patches/v7.1.3/c2b/0001-dt-bindings-power-supply-bq25890-describe-verified-charge-start.patch)
documents the properties, including the existing `linux,skip-reset`.

The profile also selects the upstream
[IRQ preflight](../2026-09-12-bq25890-irq-preflight/README.md), so a missing
interrupt fails probe before any register write.

That auto-detection stays off after `AUTO_DPDM_EN=0`, so `IINLIM` survives a
cable plug, comes from the TI datasheet. The first boot must confirm it by
reading `IINLIM` back after a plug.

## Profile

`mt6797-a53-c2b-charger-compile`: the 107 board-services patches, the
preflight, and the two patches above (110 in canonical order). The fragment
keeps the board-services RTC scope and adds `CHARGER_BQ25890`.

## Interrupt wiring (open)

The public board DWS (`drivers/misc/mediatek/dws/mt6797/aeon6797_6m_n.dws` at
`c5b0be85…`) names EINT158 `CHR_STAT`: level, active low, no debounce. GPIO246
is in EINT mode 0 as an input with a pull-up, and the mainline MT6797 pin table
maps GPIO246 to EINT158. The vendor `chr_stat` node is disabled, and the vendor
charger driver requests no interrupt.

The name suggests the BQ25896 STAT pin (held low while charging) rather than
`/INT` (256 µs pulses). A read-only Gemian check has been requested to
distinguish them. The candidate DT node waits for that answer.

## Candidate DT

[c2b-dt.sh](c2b-dt.sh) runs the
[board-services DT derivation](../2026-10-06-mt6797-board-only-profile/board-services-dt.sh)
on the exact C1-5 parent, then makes these edits and checks that the
decompiled difference is exactly them:

- `/i2c@11007000` (I2C0) status okay. Its existing disabled child, an
  `onsemi,fan49101` regulator, stays disabled.
- New `/i2c@11007000/charger@6b`, compatible `"ti,bq25896", "ti,bq25890"`:

  | Property | Value | Programmed |
  | --- | --- | --- |
  | `ti,battery-regulation-voltage` | 4192000 | 4.192 V, the step at or below 4.2 V |
  | `ti,charge-current` | 512000 | 512 mA, exact |
  | `ti,precharge-current`, `ti,termination-current` | 128000 | 128 mA |
  | `ti,minimum-sys-voltage` | 3500000 | 3.5 V |
  | `ti,boost-voltage`, `ti,boost-max-current` | 5126000, 500000 | chip-default voltage, lowest limit; OTG unused |
  | `linux,skip-reset`, `linux,verified-charge-start` | present | |
  | `linux,verified-input-current-limit-microamp` | 500000 | 500 mA |
  | `interrupts` | EINT158 via the pin controller | the driver requests falling edge |

- The output is reproducible: SHA-256
  `fdb4d3c96afc0935032a4cebe141ebc602c9a2fc5a00c6b54372395777c784be`.
- **Schema.** No new diagnostic relative to the board-services derived DT,
  against the C2b tree schema (`676b977c…`, which includes c2b/0001). The
  checks caught and fixed three mistakes before this: a zero `reg`, 1-byte
  boolean properties, and a missing `ti,bq25890` fallback compatible.

I2C0 itself is on GPIO37/38 in mode 1 (`SCL0_0/SDA0_0`) per the public board
DWS, which the loader applies; the DT adds no pinctrl state for it
([I2C1 record](../2026-10-06-gemini-i2c1-sensors/README.md)). GPIO246 has no pinctrl state: mainline's MT6797 table lacks its pull fields
(C1 added them only for GPIO66), so the loader's pull-up, set to pull-high in
the vendor DWS, is relied on. EINT setup at IRQ request writes mode 0, input
and Schmitt, as for the lid.

## Protocol draft (for the custodian's review)

Hypothesis: the verified start programs and reads back every limit before
charging starts, and the 500 mA input limit survives a cable plug with
`AUTO_DPDM_EN=0`.

Admitted effects, beyond board-services:

- I2C0 controller probe: its clocks and controller init, with no transfer
  until a client.
- BQ25896 probe: identity read; `CHG_CONFIG=0`; watchdog off; limit writes;
  `IINLIM`, `ICO_EN=0`, `AUTO_DPDM_EN=0`; 17 read-backs; `CHG_CONFIG=1` and
  its read-back; the existing ADC conversion-rate write; registration of the
  power supply and of the OTG regulator, which is not enabled.
- EINT158 setup at IRQ request.

There is no reset, unbind, OTG enable, input-limit write above 500 mA or
Pump Express.

Run, before any cable for longer than the observation:

1. Boot with no cable. Record the probe line, which is either
   `verified start: 17 limits read back, input limit 500000 uA, charging
   enabled` or the field mismatch, and the power-supply sysfs values:
   `constant_charge_current`, `constant_charge_voltage`,
   `input_current_limit`, `online`, `status`. Record the EINT158 interrupt
   count.
2. Attach a known 5 V USB source for at most 5 minutes. After 10 s, read the
   same values again; `input_current_limit` must still be 500000. Read the
   interrupt count, then detach.
3. Read the values once more; preserve the log; reviewed recovery.

Decision branches:

- **Probe mismatch.** Charging stays disabled. Record the field and stop.
- **`input_current_limit` above 500000 after the plug.** The datasheet
  assumption is false. Detach at once; no further C2b boot until reviewed.
- **Values as programmed, status charging.** C2b's gate is met; the next step
  is the gauge/ADC comparison boot.
- **EINT158 count change.** Interpret it with the Gemian STAT/INT answer.

## Validation

- Local `W=1` compile of `bq25890_charger.o` with the board-services config plus
  `CHARGER_BQ25890`: no warnings.
- `dt-doc-validate` and `dt_binding_check` for the binding: pass.
- checkpatch `--strict`: 0001 clean. 0002 has one alignment note matching the
  neighbouring `linux,read-back-settings` lines in the same function.
- The 110-patch series via the build's apply method reproduces the author
  tree.
- [c2b-dt.sh](c2b-dt.sh): ShellCheck clean; refuses existing outputs and
  symlinks (inherited from the board-services script for the parent).

## Build

| Item | Value |
| --- | --- |
| Input commit | `cfca5ee606809ebeb04d3624d2e56d94e21ceeac` |
| Job | `cfca5ee6…-mt6797-a53-c2b-charger-compile-m0`, buildbox-1, 32 jobs |
| Package inventory | `f3b2a202ab2fc28735fe020af25701050a4de4f36addab24911214510e126a84` |
| Release | `7.1.3-gemini-a53-c2b-charger-compile` |

Compilation, remote validation, fetch and local checksums pass, with no
compiler warning. The resolved config has `CHARGER_BQ25890` and
`RTC_DRV_MT6397` built in, with `SUSPEND` and `DEBUG_FS` off, and the image
contains the verified-start property. The packaged DT has no charger node and
is not a candidate DT.
