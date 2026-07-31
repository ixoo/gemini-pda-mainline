# DA921x private OF-modalias uevent insertion

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-of-modalias-private-insertion` |
| Status | `running` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Is adding the exact real-compatible `MODALIAS=` entry to a uevent environment
sufficient to reproduce the pre-serviceability reset, or must that entry be
emitted as part of the real device event?

The candidate preserves the real OF child and module-free serviceability
baseline. A focused I2C-core branch computes the exact OF modalias, adds it to
a zeroed private `kobj_uevent_env`, validates its index, length, buffer
placement, terminator, and all bytes, discards it, and emits only the safe I2C
fallback in the real event.

## Decision

- Serviceability proves private environment insertion safe and implicates
  emitting the real OF modalias entry.
- A reset after the private-insertion marker makes the insertion operation
  itself sufficient.
- Any generation, insertion, or layout mismatch fails the device add-event
  before serviceability and is not a hardware result.

## Safety

The patch adds no driver or transfer path. The DA921x driver remains
module-only and absent from the initramfs. CPUs 8 and 9 remain offline.
Runtime acceptance requires the real OF node, unbound client, exact
private-insertion marker, zero I2C/oracle counters, and the complete existing
serviceability baseline. The candidate performs no partition access.

The experiment patch has actual author metadata but no DCO sign-off. It is
experiment-only and not submission-ready.
