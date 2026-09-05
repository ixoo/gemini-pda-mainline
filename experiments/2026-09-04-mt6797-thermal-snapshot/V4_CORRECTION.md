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
