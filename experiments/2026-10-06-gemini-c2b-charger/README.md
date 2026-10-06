# Experiment: C2b charger profile with a verified charge start

| Field | Value |
| --- | --- |
| ID | `2026-10-06-gemini-c2b-charger` |
| Status | Driver change and compile profile; interrupt wiring awaits a Gemian check; not booted |
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

## Candidate DT (planned, not yet written)

The C2b candidate DT will be derived from the exact C1-5 parent like the
[board-services DT](../2026-10-06-mt6797-board-only-profile/board-services-dt.sh),
plus: I2C0 (`/i2c@11007000`) enabled, and a `ti,bq25896` node at `0x6b` with
`linux,skip-reset`, `linux,verified-charge-start`, a 500 mA input limit,
4.2 V, 512 mA charge current, conservative precharge and termination, and the
interrupt chosen from the Gemian answer.

## Validation

- Local `W=1` compile of `bq25890_charger.o` with the board-services config plus
  `CHARGER_BQ25890`: no warnings.
- `dt-doc-validate` and `dt_binding_check` for the binding: pass.
- checkpatch `--strict`: 0001 clean. 0002 has one alignment note matching the
  neighbouring `linux,read-back-settings` lines in the same function.
- The 110-patch series via the build's apply method reproduces the author
  tree.
