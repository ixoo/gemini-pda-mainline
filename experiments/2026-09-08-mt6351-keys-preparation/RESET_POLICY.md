# MT6351 reset duration and recovery policy

Status: duration conversion compile and schema validated, 2026-09-08.
No physical reset or register access was
performed. This follow-up does not admit a Gemini key node.

## Evidence

The public Gemian source at
[`59e00a9144d782e148332009a835b99c43382467`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467)
provides a timing contract independent of the upstream property's name:

| Source | Observation |
| --- | --- |
| `drivers/input/keyboard/mediatek/Kconfig`, lines 65–71 | `KPD_PMIC_LPRST_TD` accepts selectors 0–3, documented as 8, 11, 14 and 5 seconds |
| `drivers/input/keyboard/mediatek/mt6797/hal_kpd.c`, lines 240–290 | Normal and other boot paths select one-key or two-key reset from configuration, then pass the selector directly to `MT6351_PMIC_RG_PWRKEY_RST_TD`; factory modes disable both enables |
| `drivers/input/keyboard/mediatek/kpd.c`, line 921 | Keypad probe invokes that setup function |
| MT6797 `upmu_hw.h`, lines 2829–2840 | MT6351 timeout is a two-bit field at bits 13:12 of `TOP_RST_MISC`; power/home reset enables occupy bits 9/8 |

The retained [active Gemian configuration](../2026-07-23-gemian-a72-owner-observer/inputs/active-gemian.config)
enables one-key reboot in normal and other modes, disables both two-key
options, and sets `CONFIG_KPD_PMIC_LPRST_TD=1`. Its SHA-256 is
`231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4`.
The capture identity and limits are owned by the
[original reconciliation record](../2026-07-23-gemian-a72-owner-observer/README.md#provenance-and-environment).
The public source is not proven to be the exact source of the running kernel.
Therefore this is evidence for an eleven-second one-key policy, not proof of
current register values, a timed physical reset, or firmware behavior after it.

The [source receipt](results/reset-policy-source.json) pins all inspected
files. No retained firmware or vendor source is copied into this repository.

## Seconds are not selector values

The pinned upstream `input.yaml` defines `power-off-time-sec` in seconds.
The PMIC driver instead shifts that value directly into its timeout field.
For MT6351 this gives the following mismatch, after the two-bit mask:

| Requested seconds | Previous selector | Documented duration | Correct selector |
| --- | --- | --- | --- |
| 5 | 1 | 11 seconds | 3 |
| 8 | 0 | 8 seconds | 0 |
| 11 | 3 | 5 seconds | 1 |
| 14 | 2 | 14 seconds | 2 |

This invalidates the five-patch topic's explicit-duration contract despite
its successful compile and schema checks. Those earlier receipts remain
historical evidence. Its original 42 cases tested raw selector behavior;
they did not test the property's seconds semantics.

Two appended patches correct the new MT6351 compatible. The binding accepts
only 5, 8, 11 or 14 seconds, with an eight-second absent-property default.
The driver maps seconds to the hardware selector and returns `EINVAL` for an
unsupported explicit value before the reset-register update. The absent
property still selects zero. Existing chips retain their prior interpretation
until their timing/compatibility contracts are independently established.
No reset-enable mask changes or automatic recovery-policy selection are added.

The expanded [actual-function fixture](test-key-state.py) passes 94 cases:
key reads and transport errors, all four durations in all three reset modes,
update errors, absent duration, unsupported durations with zero register
updates, and the legacy no-table path. Restoring only the pre-conversion reset
function compiles but fails the expected register-value assertion. The fixture
still does not execute full probe or model physical timing.

## Validation

The [compile receipt](results/duration-compile.json) records the clean
`1611b52dc1b9a72be0b606a2768da346714222e2` build of all nineteen patches and
the checksum-verified fetched package. There are no compiler warnings or
errors. The configuration and MFD object match the original key-topic build;
the key object changes, and the compiled source matches the reviewed patch.
The 94-case fixture also passes against this prepared source on Buildbox.

Focused binding checks pass with all three completion markers. Direct
validation accepts each of 5, 8, 11 and 14 seconds for MT6351, rejects 1, and
still accepts 1 when only the key compatible is changed to MT6331. The combined
parent/regulator/power-key fixture passes all three schema selections; invalid
reset mode 3 remains rejected. The [schema receipt](results/duration-schema.json)
and [portable log](results/duration-schema-validation.txt) preserve the result.
`PYTHONDONTWRITEBYTECODE=1` prevents generated source-tree bytecode; the complete
source integrity digest is unchanged before and after validation.

Use the [parent reproduction commands](README.md#validation). For the duration
schema checks, substitute each of 5, 8, 11, 14 and 1 into `power-off-time-sec`
in the offline fixture; only 1 must fail MT6351 validation. The legacy check
changes just the key compatible to `mediatek,mt6331-keys` with duration 1.
These are configuration and compiler tests, not physical timing measurements.

The [retained-kernel follow-up](RESET_BINARY.md) confirms that the captured
Gemian binary requests the one-key/selector-1 policy and resolves its actual
field-table entries. It also shows that the setter discards update errors and
that `pmic_access` can return cached data after a failed read. These compiled
facts narrow the policy hypothesis but do not supply live register evidence.

## Device admission remains separate

An explicit one-key mode with an eleven-second duration would encode the
retained configuration's policy intent. Do not install that policy merely
from this source comparison. Establish the attributable live boot/configuration
and reset-field state through an admitted bounded observation, reconcile the
physical recovery path, and review the candidate before a timed physical test.
Absent reset policy still disables both hardware long-press reset enables.
Disabling them is not a demonstrated safe default for this device.

The older recovery experiment's wording that disabled reset was a safe default
is superseded by this admission boundary. Preserve its historical artifacts;
do not reuse that assertion as authority for a new board node. Neither the
property name nor the vendor function name proves whether a physical event
powers down, resets, or restarts through retained firmware.
