# DA921x dual-modalias live-path validation state

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-path-state` |
| Status | `deployed and shut down; awaiting selected boot` |
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

The named `da921x-dual-modalias-path-state` profile was built only through
`./scripts/build-kernel --backend buildbox`. Buildbox fetched exact clean,
pushed commit `75285adfd59b93078be09219c69c7bd9dd451ebb`; its validated
package was assembled twice into byte-identical candidates. No native VM
kernel build ran. The VM was used only for script validation and deterministic
boot-container assembly.

Two preparation invocations stopped before output: the first exposed a wrapper
generation error and the second rejected an incorrectly selected inherited
candidate as the pinned Gate 3 input. The corrected third invocation used the
exact retained Gate 3 inputs, passed all 32 LK gates, and selected
`candidate-Gate3-da921x-pathstate-3cda4b88`. Its full boot2 checksum is
`f3ef6a90777b14f3b1ffed2fa23f9497ec5472d380aaaa59db0fb8bd706c4015`.
No device access or hardware write occurred during build and assembly.

## Deployment

The bounded installer resolved logical `boot2` from the live GPT as
`/dev/mmcblk0p30`, distinct from active root `/dev/mmcblk0p29`. The exact
predecessor checksum matched, battery state was 100% and healthy, and the
candidate was written, synced, flushed, and independently read back in full.
The readback was byte-identical with checksum
`f3ef6a90777b14f3b1ffed2fa23f9497ec5472d380aaaa59db0fb8bd706c4015`.
No new partition backup was made; the verified project-wide backup remains the
recovery source. The temporary readback was removed and the device shut down
cleanly so the owner can physically select `boot2`.
