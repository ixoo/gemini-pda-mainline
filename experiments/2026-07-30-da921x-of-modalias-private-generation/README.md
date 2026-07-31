# DA921x private OF-modalias generation

| Field | Value |
| --- | --- |
| ID | `2026-07-30-da921x-of-modalias-private-generation` |
| Device | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Is generating the exact real-compatible OF modalias sufficient to reproduce
the pre-serviceability reset, or is adding that value to the device uevent
environment required?

The candidate preserves the real OF child and module-free serviceability
baseline. A focused I2C-core branch calls `of_modalias()` into a private buffer
whose size is exactly the expected string plus its terminator, validates the
returned length and every byte, discards the value, and emits only the safe I2C
fallback.

## Decision

- Serviceability proves private OF modalias generation safe and implicates
  insertion or emission of the real OF modalias environment value.
- A reset after the private-generation marker makes string generation itself
  sufficient.
- A length or content mismatch fails the device add-event before
  serviceability and is not a hardware result.

## Safety

The patch adds no driver or transfer path. The DA921x driver remains
module-only and absent from the initramfs. CPUs 8 and 9 remain offline.
Runtime acceptance requires the real OF node, unbound client, exact
private-generation marker, zero I2C/oracle counters, and the complete existing
serviceability baseline. No candidate partition access occurs.

The experiment patch has actual author metadata but no DCO sign-off. It is
experiment-only and not submission-ready.
