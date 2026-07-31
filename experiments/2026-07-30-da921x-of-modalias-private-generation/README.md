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

## Selected candidate

The validated `7.1.3-gemini-da921x-ofgen` package was assembled twice from the
exact Gate 3 real-compatible DT and module-free initramfs. Both assemblies were
byte-identical. The retained Android-v0 container passed all 32 LK gates.

| Item | SHA-256 |
| --- | --- |
| Kernel `Image.gz` | `b0b9f5aea15c553e8dea65e42247a240f9b5bedb06f6a4768e19a1147328a5bf` |
| Kernel configuration | `cc7b5fc393f4db17f722b2c210b0d85f7b998d8ceb8ce63bcdc6eb84b83d07e5` |
| Real-compatible DT | `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806` |
| Module-free initramfs | `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f` |
| Boot container | `281b4e95e8cd2ef96e921bf06f4016fe2592bc71b2337b41296f867abde2bb60` |
| Exact 16 MiB boot2 image | `5f7b48336034ff13608483f29c322213cdcf3914e54aa2a9603bb9962fc3a8eb` |
| Candidate manifest | `63a2220d78559526a26170bacbf1dad8308423675a246072b765fe74a3dab3ea` |

The installer resolves `boot2` from the live GPT, requires the currently
validated OF-modalias-suppression predecessor, performs a full post-write
readback, creates no new partition backup, and powers the device off after
verified success.

## Runtime result

Attempt 1 was serviceable on `7.1.3-gemini-da921x-ofgen`, boot ID
`7b4e14ce-3546-41b6-ae40-cb971d4ca3cd`. The exact read-only verifier confirmed
the enabled real-compatible `1-0068` client, attached OF node, unbound state,
and one private-generation marker with the exact 38-byte modalias. The add
event still emitted only the safe I2C fallback. Every I2C6 transfer, DMA,
start, IRQ, and oracle counter remained zero, and the complete serviceability
baseline survived.

Native reboot returned Gemian `3.18.41+` on boot ID
`d09926de-7dd7-48ca-92f5-d76dfd140c15`. See the
[runtime result](results/runtime-attempt-1-20260731.txt).

This proves that generating the exact real-compatible OF modalias is safe.
The remaining boundary is adding that value to an event environment or
emitting the resulting event. The next discriminator must insert the exact
`MODALIAS=` entry into a private bounded `kobj_uevent_env`, validate its
layout, discard it, and retain the safe I2C fallback in the real event.
