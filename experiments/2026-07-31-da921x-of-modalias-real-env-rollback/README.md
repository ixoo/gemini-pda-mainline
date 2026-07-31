# DA921x real OF-modalias uevent insertion and rollback

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-of-modalias-real-env-rollback` |
| Status | `candidate preparation` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Is transient presence of the exact real-compatible `MODALIAS=` entry in the
real device-event environment sufficient to reproduce the pre-serviceability
reset, even when the environment is restored before emission?

The candidate preserves the real OF child and module-free serviceability
baseline. A focused I2C-core branch snapshots the real environment's next
pointer slot, indices, and exact 48-byte buffer range; inserts and validates
the exact OF entry; restores and validates every snapshot; and then adds only
the safe I2C fallback for emission.

## Decision

- Serviceability proves transient presence in the real environment safe and
  implicates the OF entry remaining present during event emission.
- A reset after the rollback marker makes transient real-environment mutation
  sufficient, despite exact restoration before emission.
- Any generation, insertion, layout, or rollback mismatch fails the device
  add-event before serviceability and is not a hardware result.

## Safety

The patch adds no driver or transfer path. The DA921x driver remains
module-only and absent from the initramfs. CPUs 8 and 9 remain offline.
Runtime acceptance requires the real OF node, unbound client, exact rollback
marker, zero I2C/oracle counters, and the complete existing serviceability
baseline. The candidate performs no partition access.

The experiment patch has actual author metadata but no DCO sign-off. It is
experiment-only and not submission-ready.
