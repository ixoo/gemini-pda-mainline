# DA921x private OF-modalias uevent insertion

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-of-modalias-private-insertion` |
| Status | `completed` |
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

## Selected candidate

The validated `7.1.3-gemini-da921x-ofinsert` package was assembled twice from
the exact Gate 3 real-compatible DT and module-free initramfs. Both assemblies
were byte-identical. The retained Android-v0 container passed all 32 LK gates.

| Item | SHA-256 |
| --- | --- |
| Kernel `Image.gz` | `eb41b8db9b889ae60b103d35590e8916ef33e12890760674d628b45e86142e32` |
| Kernel configuration | `2a714a8139f24fe9d8e6cbb1b809c8f496351cc92254f90f00238e5e89913c12` |
| Real-compatible DT | `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806` |
| Module-free initramfs | `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f` |
| Boot container | `d04348ab72bcdb3b78615881fe952995c2b17ffea409ae3307b90468de9caace` |
| Exact 16 MiB boot2 image | `a987ff8be9d12b9d13c223341dc5659b2d2fc27d29f30e5b2273be6646cd97e7` |
| Candidate manifest | `d6c383e33269b17f84b71cfbe98277fadf6744e18067c308aaa552ea39762f40` |

The installer resolves `boot2` from the live GPT, requires the validated
private-generation predecessor, performs a full post-write readback, creates
no new partition backup, and powers the device off after verified success.

## Runtime result

Attempt 1 was serviceable on `7.1.3-gemini-da921x-ofinsert`, boot ID
`5a6f69a9-956a-431a-a46a-6f08c081103c`. The kernel marker confirmed the exact
38-byte OF modalias was inserted as one 47-byte `MODALIAS=` entry in a private
environment with a 48-byte terminated buffer. The real-compatible `1-0068`
client retained its OF node and remained unbound while the real event used the
safe I2C fallback. Every I2C6 transfer, DMA, start, IRQ, and oracle counter
remained zero, and the complete serviceability baseline survived.

The initial verifier stopped before classification because it incorrectly
treated the `MODALIAS=` prefix as eight bytes. The raw marker exposed the
correct nine-byte prefix; the corrected, committed verifier passed on the same
live boot. This changed only the observation classifier, not the candidate.

Native reboot returned Gemian `3.18.41+` on boot ID
`d6629d14-f809-423c-b433-8df84b8e14a2`. See the
[runtime result](results/runtime-attempt-1-20260731.txt).

This proves private environment insertion mechanics safe. The remaining
boundary is the real OF modalias entry being present when the device event is
emitted. The next discriminator must insert and validate that entry in the
real event environment, restore the original environment state byte-for-byte,
and then add only the safe I2C fallback before emission.
