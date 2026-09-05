# Focused V4 conversion correction

This implements the [arithmetic audit](V4_CONVERSION_AUDIT.md) as a deterministic
single-function edit. It normalizes encoded ADC OE by 512, uses the existing
sensor-to-calibration map, and rejects out-of-range sensor IDs before indexing.
The calibration decoder, bank layout, raw masking, signed shifts, denominator
checks, other SoCs and observation budgets remain unchanged. This does not
claim to fix the multi-degree runtime response or establish thermal freshness.

[correct-v4-conversion.py](scripts/correct-v4-conversion.py) accepts only the
pinned production file and writes an exclusive output.
[test-v4-correction.py](scripts/test-v4-correction.py) extracts the actual
corrected converter, unchanged decoder, enum and mapping into a host harness.
It tests distinct synthetic coefficients (including a poison VTS5), all five
sensor IDs, ID-controlled slope, zero raw codes, invalid IDs, calibration enable
and boundary refusals, monotonicity, quantization and upper-bit masking. The
independent reference uses explicit expected indices rather than the production
mapping. Ten mutations must compile successfully and fail execution. Source
identity and the single-function edit boundary are also checked.

Initial execution on Buildbox passed 177 decode cases, 3,316,950 conversion grid
cases, 6,633,900 upper-mask checks, 81,900 distinct-sensor/ID cases and all ten
mutations. These are synthetic tests, not device measurements. The corrected
file SHA256 is `0e833aac1850c3e2910f5feb463f5e7a1a8943b77b1f99bfac4ca9e708f1ded4`.
No kernel source was changed in the managed tree, and temporary harnesses were
removed. No kernel build or device access occurred.

[generate-v4-correction-on-buildbox](scripts/generate-v4-correction-on-buildbox)
requires a clean published checkout, exact production state and full-tree
integrity. It reruns the tests, edits only a bounded copy of one source file,
creates one normal format-patch, checks it, replays it to an identical tree,
and removes temporary work. Its output is exclusive. The archive uses the
repository's explicitly synthetic experimental author with no certifying
sign-off and is not submission-ready. No vendor code is copied into the fix.

Generation, patch admission, profile choice and compilation remain separate
from this initial host test. No existing runtime protocol is authorized for a
changed image. A new candidate must bind its corrected source identity and
retain all admission, accounting, cleanup and thermal-refusal constraints.
Ordered work remains in the [roadmap](../../docs/ROADMAP.md).


## Generated patch and compilation admission

Clean published revision `7d8688815e8925258eb3cad635a94e5c6322645e` generated
[patch 0541](../../patches/v7.1.3/0541-thermal-mediatek-correct-MT6797-offset-and-calibration-index.patch).
The [generation receipt](results/v4-correction-generation.txt),
[repeated exact-function tests](results/v4-correction-tests.txt), and
[sanitized style check](results/v4-correction-checkpatch.txt) pass. Replay
produced an identical source tree. Patch SHA256:
`670dba907508d4b2001ee44facb5c07a182a403f14b668e685a0285c31665d34`.

The isolated `mt6797-thermal-v4-correction-compile` profile inherits the snapshot
configuration for a compile check only. It is not a boot candidate, and the old
configuration binding/release must not be used to claim a corrected runtime.
All 187 pre-existing profiles retain their exact patch bytes and configuration
inputs; 159 previous canonical-series users now name the frozen predecessor
series. Only the new profile selects the correction. The canonical superset
still orders all patches. This avoids silently changing the default or the
identity of the deployed snapshot profile. No new runtime protocol is admitted.


## Compile result

The [Buildbox compile/package receipt](results/v4-correction-build-pass.json)
passes for clean published revision `57c07ecb89c6c8401da1946a85c55547216de04f`.
The built production file matches the tested corrected SHA256. Kernel Image,
compressed Image and DTBs were packaged and validated; the required package
fetch and independent local manifest replay passed. Host/Buildbox available
space was checked before building. No native VM build or device operation ran.
The package remains private under the managed Buildbox export root for the
open correction work. This is compile evidence only; no runtime support is
promoted and no slot write or physical boot is selected.
