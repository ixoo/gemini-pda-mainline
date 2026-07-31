# DA921x dual-modalias live-path validation state

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-path-state` |
| Status | `kernel inputs prepared; awaiting Buildbox validation` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Does exact ten-entry validation reach `validated` and remain serviceable
when the only changes from the safe `pending` candidate are the two
live-proven root-level path strings?

The candidate expects
`/devices/platform/1100e000.i2c/i2c-1/1-0068` and
`OF_FULLNAME=/i2c@1100e000/regulator@68`. It retains the same
no-printk read-only state, ordered OF and I2C modalias checks, numeric sequence
check, target transport suppression, normal cleanup, module-free initramfs,
real OF client, and CPU0–7 baseline.

## Decision

- Serviceability with state `validated` proves the complete exact
  event reached the intended checkpoint without transport or printk.
- Serviceability with state `pending` identifies another validation
  mismatch and requires a more granular read-only stage code.
- A pre-serviceability reset implicates the newly reached successful validation
  or cleanup boundary, not either corrected path string in isolation.

No result advances provider work unless the complete console, keyboard, USB,
CPU, handoff, unbound-client, and zero-I2C-activity baseline also passes.

## Safety

The patch changes only two experiment validator string constants under a new
configuration gate. It adds no driver, provider, transfer, register access, or
storage path. The target event remains fail-closed before transport on any
mismatch and is suppressed after successful validation. The DA921x driver
remains module-only and absent from the initramfs; CPUs 8 and 9 remain offline.

The experiment patch uses the actual author identity but carries no DCO
sign-off. It is experiment-only and not submission-ready.

## Build workflow

Build only through `./scripts/build-kernel --backend buildbox` from an
exact clean pushed commit. Do not run a native VM kernel build unless the owner
explicitly requests one. Use the validated Buildbox package for deterministic
candidate assembly.
