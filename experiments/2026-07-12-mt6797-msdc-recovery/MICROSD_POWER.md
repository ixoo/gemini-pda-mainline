# microSD power-state and trim follow-up

Offline source and retained-kernel review, 2026-09-09. No live PMIC, GPIO,
calibration, storage or boot operation occurred. This narrows the
[initial power contract](MICROSD_CONTRACT.md); it supplies no electrical result
or board-enablement sequence.

## The retained off request does not disable a rail

The compiled `msdc_ldo_power()` has different meanings for software status and
regulator requests. With `on == 0`, a nonzero status is cleared, but there is
no call to `msdc_hwPowerDown()` or `regulator_disable()`. With status already
zero it only logs. The pinned public source has that power-down call commented
out, matching the retained Image.

The voltage-change branch is different: a nonzero status at another voltage
calls power-down and then power-on. A first on request calls power-on; an
on request at the same recorded voltage calls neither helper. Thus an
on/off/on sequence requests enable twice without a matching disable between
them. This is a compiled call sequence, not an observed rail or reference count.

`msdc_hwPowerOn()` ignores `regulator_set_voltage()`'s result and checks only
`regulator_enable()`. Its boolean result is then ignored by `msdc_ldo_power()`,
which records the requested microvolts and returns zero even when that helper
fails. `msdc_hwPowerDown()` likewise discards the disable result. The status
variables and power log strings therefore cannot establish regulator success,
actual voltage, or successful power removal.

A six-case host execution of the exact public `msdc_ldo_power()` function
confirms these control-flow results with mocked power helpers:

| Sequence / initial status | Power-on calls | Power-down calls | Final software status |
| --- | --- | --- | --- |
| On at 3.0 V / zero | 1 | 0 | 3000000 |
| On at 3.0 V / 3000000 | 0 | 0 | 3000000 |
| Off / 3000000 | 0 | 0 | 0 |
| Change to 1.8 V / 3000000 | 1 | 1 | 1800000 |
| On at 3.0 V, helper fails / zero | 1 | 0 | 3000000 |
| On, off, on at 3.0 V / zero | 2 | 0 | 3000000 |

All calls return zero. These cases do not execute a regulator, model hardware
or prove that these paths ran on the current boot.

## The standard regulator operations preserve trim bits

The current unsigned MT6351 regulator topic describes VMCH voltage selection
at `0xace`, mask `0x100`, and VMC at `0xae2`, mask `0x700`. Nominal 3.0 V is
selector 0 and selector 6, respectively. Both trim fields use mask `0x1f`,
which is disjoint from those voltage masks. Enable/disable uses bit 1 in
separate registers `0xa2e` and `0xaaa`.

The upstream voltage-selector helper calls `regmap_update_bits()` with the
descriptor's voltage mask; the MT6351 descriptors have no extra apply-bit
operation. The wrapper selects its 16-bit regmap configuration, with no custom
update-bits callback. The generic update computes `(old & ~mask) | (value & mask)`.
Consequently these operations preserve the trim bits they read, assuming a
successful transaction and no competing writer. They do not recreate the
retained MMC probe's relative trim adjustments. Adding those adjustments to
the regulator driver is not justified by a nominal 3.0 V request.

This resolves the software field-overlap question only. It does not establish
the trim value supplied by preloader/LK, its retention through shutdown or
reset, another firmware writer, or the effect of the pad's separate bias tune.
The retained probe's modulo-32 plus/minus-five adjustment is not idempotent;
repeating it without an established initial state changes its result.

## The 1.8 V trim subtraction has a refusal boundary

The retained `msdc_sd_power_switch()` subtracts 2 from the saved default using
32-bit arithmetic and passes the result to `pmic_config_interface()` without
reducing it to five bits. That routine clears the destination mask but does
not mask its input value before forming the write word.

For hypothetical saved defaults 0 or 1, the result is `0xfffffffe` or
`0xffffffff`. The retained WACS2 HAL rejects write data with any upper 16 bits
set, returning 4 before issuing its hardware command. The compiled HAL
initialization installs this handler. The MMC caller ignores the trim result
and continues its 1.8 V request. This is a conditional code-path result, not
an assertion that either default occurred on Gemini. It must not be described
as a successful wrapped five-bit trim write.

## Consequence for board admission

Keep 1.8 V switching excluded from the proposed first microSD test. In addition,
a future 3.0 V protocol must establish the trim state at mainline entry and
separately observe the enable/disable and recovery transitions. A mainline
power-off request must not be treated as reproducing the retained helper's
off behavior. Do not compensate with `regulator-always-on` or a copied trim
write without establishing the required board behavior. Pad tuning and SMT
ownership remain unresolved in the [pad record](MICROSD_PADS.md).

## Reproduction

The [receipt](results/microsd-power-review-20260909.json) pins the inspected
vendor and upstream files, current regulator patch, retained Image and exact
symbol spans. Use the [retained Image method](MICROSD_CONTRACT.md#reproduction-and-identities)
in the RE VM; the ELF kernel section was rechecked against the complete Image.
Only independently described facts and hashes are published.

For the host probe, extract `u32 msdc_ldo_power(` through its closing brace
from the pinned public file. Define `u32` as unsigned int, make `pr_err` a no-op,
and replace only the two external power helpers with call counters returning
the receipt's success flag. Run its six request sequences and assert the
recorded status, call counts and zero return values. The receipt records the
compiler and flags; `-Wno-sign-compare` permits the unmodified vendor function's
signed microvolt comparison. This is an analysis probe, not a new driver test
or hardware acceptance protocol. No kernel rebuild is needed for these facts.
