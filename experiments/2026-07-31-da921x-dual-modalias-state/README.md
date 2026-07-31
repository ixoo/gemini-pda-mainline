# DA921x dual-modalias read-only validation state

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-state` |
| Status | `kernel inputs prepared; awaiting Buildbox package` |
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
`./scripts/build-kernel`. Buildbox is the primary backend and must fetch the
exact clean, pushed commit. Native ARM64 VM kernel builds are not part of this
experiment unless the owner explicitly requests one. Deterministic independent
candidate assembly remains the byte-level reproduction oracle. Only validated
packages are exported; generated source and build trees remain on their
builders.
