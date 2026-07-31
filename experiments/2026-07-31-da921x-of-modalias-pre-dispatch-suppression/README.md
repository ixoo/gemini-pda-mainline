# DA921x complete OF uevent pre-dispatch suppression

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-of-modalias-pre-dispatch-suppression` |
| Status | `candidate preparation` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Does the pre-serviceability reset require transport of the completed real OF
device event, or is complete environment assembly and normal cleanup already
sufficient?

The candidate preserves the real OF child, unbound module-free baseline, and
normal OF event construction. After the exact target event receives its
sequence number, a focused kobject-core branch validates all nine ordered
entries, contiguous bounded storage, exact hardware identity, and numeric
sequence value. It then skips only netlink transport and frees the environment
through the normal cleanup path.

## Decision

- Serviceability isolates the reset trigger to event transport or receiver
  handling rather than OF construction or environment cleanup.
- A reset after the pre-dispatch marker implicates full event assembly or the
  normal cleanup path without any broadcast.
- Any target identity, ordering, storage, or sequence mismatch fails closed
  before transport and is not a hardware result.

## Safety

The patch adds no driver or transfer path and suppresses only the exact target
add-event. The DA921x driver remains module-only and absent from the initramfs.
CPUs 8 and 9 remain offline. Runtime acceptance requires the real OF node,
unbound client, exact pre-dispatch marker, zero I2C/oracle counters, and the
complete serviceability baseline. The candidate performs no partition access.

The experiment patch has actual author metadata but no DCO sign-off. It is
experiment-only and not submission-ready.
