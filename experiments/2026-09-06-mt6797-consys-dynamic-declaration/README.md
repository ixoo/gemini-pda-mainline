# Experiment: passive Gemian dynamic CONSYS declaration

This bounded follow-up asks only for the dynamic-allocation properties omitted
by the consumed passive ownership snapshot. It does not repeat `/proc/iomem` or
platform-owner reads and cannot establish the allocated base, reservation,
protection, mapping or hardware ownership.

The exact protocol is in [SESSION.md](SESSION.md). Preparation targets the
already-running known-good Gemian identity recorded in [WORK_ITEM.md](WORK_ITEM.md).
One read-only collection may run only after the frozen scripts and refusal
fixtures pass specialist safety review. No physical interaction is needed.

## Result

The one permitted collection completed in 0.7 seconds with stable Gemian
release, boot identity and model. The live root and reserved-memory nodes both
use two address and two size cells; reserved-memory `ranges` is present-empty.
The exact `consys-reserve-memory` node is reg-less, declares a 2 MiB size and
2 MiB alignment, restricts allocation to one `0x40000000..0xbfffffff` window,
has `no-map`, and is not reusable.

Those fields form a valid dynamic declaration under the compile-tested parser:
equal supported cell widths, nonzero size/alignment and one nonoverflowing
allocation-range tuple. The reads were sequential rather than an atomic DT
snapshot. More importantly, they expose no initialized `reserved_mem` record,
allocated base or physical resource. This result therefore does not establish
successful allocation, reservation, no-map enforcement, EMI/MPU protection,
ownership, mapping permission or hardware support.

The sanitized [observation](results/observation.json) records the exact values,
collector identities, consumed budget and interpretation boundary. No write,
privilege, register, `/proc/iomem`, firmware, calibration or radio interface was
used. The device remains on Gemian and this protocol authorizes no repeat.

Status: complete; one live attempt consumed.
