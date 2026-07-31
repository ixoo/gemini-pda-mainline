# DA921x dual-modalias read-only validation state

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-state` |
| Status | `completed; safe attributable path-validation failure` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Does the immediate validation `pr_info()` account for the reset of the exact
dual-modalias pre-dispatch candidate, or does the reset persist when the same
ten-entry validation and transport suppression record state without printing?

The candidate retains the real OF child, module-free initramfs, exact ordered
OF and I2C modalias validation, numeric sequence validation, successful uevent
return, and normal cleanup. It replaces only the immediate printk with an
atomic state exposed later through the read-only
`/sys/kernel/gemini_da921x_dual_modalias_state` attribute.

## Decision

- Serviceability with state `validated` proves the exact checkpoint executed
  and isolates the removed printk as the effective difference from the failed
  predecessor.
- Serviceability with state `pending` is an attributable validation failure,
  not evidence about the printk.
- Another pre-serviceability reset rules out the immediate printk as a
  sufficient cause, but does not claim the unobservable state was set.

No result advances provider work unless the complete established console,
keyboard, USB, CPU0--7, handoff, and zero-I2C-activity baseline also passes.

## Safety

The patch adds no driver, provider, transfer, register access, or storage path.
The target event is still suppressed before netlink transport. The DA921x
driver remains module-only and absent from the initramfs, and CPUs 8 and 9
remain offline.

The experiment patch uses the actual author identity but carries no DCO
sign-off. It is experiment-only and not submission-ready.

## Build workflow

The named `da921x-dual-modalias-state` profile is built through
`./scripts/build-kernel --backend buildbox`. Buildbox fetched exact clean,
pushed commit `89316a4a88182d9fcfe632c9f44468b8002b5ad3`; its validated
package was assembled twice into byte-identical candidates. Native VM kernel
builds are not part of this experiment unless the owner explicitly requests
one. Only the validated package and bounded candidate were exported; generated
source and build trees remain on their builders.

The first three assembly invocations stopped before producing output while
the source-pinned wrapper was corrected. Their negative results are retained
in `results/`; the fourth invocation passed all 32 LK gates and the
independent byte-for-byte reproduction check. The selected exact candidate is
`candidate-Gate3-da921x-dualstate-53376218`, with full boot2 checksum
`5c3788905c6c3270d7416997c922f0774802fafb5086e10ff5f247ca0a26a1b3`.
It was written to live-GPT-resolved `boot2`, independently read back
byte-for-byte, and the device was shut down cleanly. No new partition backup
was created; recovery continues to rely on the verified project-wide backup.

The one-shot host collector authenticates the exact Gemini USB MAC, address,
route, and endpoint before sending the source-pinned read-only verifier over
the direct netcat shell. It stages the check only in writable initramfs
`/run`, records no partition reads or storage writes, removes the
temporary helper after execution, and deliberately leaves reboot as a separate
post-validation action.

## Runtime result

On the first selected boot, the owner reported that the console was
serviceable. USB/netcat then established exact kernel identity
`7.1.3-gemini-da921x-dualstate` and exposed validation state
`pending`. CPUs 0–7, the CPU8/9-offline policy, the real unbound OF
client, module-free baseline, USB serviceability, I2C6 handoff, and every
transfer/oracle counter all passed unchanged.

The live client path is
`/devices/platform/1100e000.i2c/i2c-1/1-0068`, while the validator
expected an extra `/soc` component. The live OF fullname is
`/i2c@1100e000/regulator@68`, while the ordered environment validator
also expected an extra `/soc`. Source ordering proves the devpath
comparison fails first, before any environment-entry validation; the caller
then suppresses transport through its fail-closed error path. This result is
therefore not evidence about the removed printk.

Collector attempts 1–4 stopped before verifier execution because the initial
MAC pin and then the assumed `/tmp` staging path were wrong. Those
failures are retained separately and make no kernel claim. Attempt 5 used the
exact inherited MAC and writable initramfs `/run`, captured the
attributable `pending` result, and performed no partition read,
storage write, or reboot request.
