# DA921x real OF-modalias uevent insertion and rollback

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-of-modalias-real-env-rollback` |
| Status | `completed` |
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

## Selected candidate

The validated `7.1.3-gemini-da921x-ofrollback` package was assembled twice
from the exact Gate 3 real-compatible DT and module-free initramfs. Both
assemblies were byte-identical. The retained Android-v0 container passed all
32 LK gates.

| Item | SHA-256 |
| --- | --- |
| Kernel `Image.gz` | `92620e87657134a7479ed87df3c3fa74773672fd5089b68e69ecb1e7dfd3937c` |
| Kernel configuration | `46cb6d8eb286b03f831b252980dc365bcf6bffd4aa722287821097552ebf72ec` |
| Real-compatible DT | `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806` |
| Module-free initramfs | `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f` |
| Boot container | `9a92657fc9bbf29f6c425b9ea8737c9e521d2d6f4b304c1248c0d122cae3bb30` |
| Exact 16 MiB boot2 image | `254f3c969e564ae60040470b1a025d42f57e2a902e255ddeffcad76825a9fc94` |
| Candidate manifest | `dbdf31246bcfb2db698538caef4b92c441e755a793dffdfb1e42350b51ba95e6` |

The installer resolves `boot2` from the live GPT, requires the validated
private-insertion predecessor, performs a full post-write readback, creates no
new partition backup, and powers the device off after verified success.

## Deployment

The guarded installer resolved logical `boot2` to `/dev/mmcblk0p30` while the
known-good Gemian root was `/dev/mmcblk0p29`. The expected predecessor matched,
power was stable at 100% with good battery health, and the write, flush, target
checksum, and independent full readback all matched the exact candidate. No new
backup was created. The device shut down cleanly after verification and awaits
the first selected boot.

## Runtime result

Attempt 1 was serviceable on `7.1.3-gemini-da921x-ofrollback`, boot ID
`f54bcc63-59e6-45a7-bbdc-6c0f1c723c42`. The exact rollback marker confirmed
the 38-byte OF modalias and its terminated 47-byte `MODALIAS=` entry were
inserted into the real event environment, validated, and then restored across
the exact 48-byte buffer footprint with zero index deltas. The emitted event
used the safe I2C fallback.

The real-compatible `1-0068` client retained its OF node and stayed unbound.
Every I2C6 transfer, DMA, start, IRQ, and lifecycle-oracle counter remained
zero, while CPUs 0–7, USB, console, and the full serviceability baseline
survived. Native reboot returned Gemian `3.18.41+` on boot ID
`402198a4-541a-4535-a8dc-c74dcb04661d`.

This proves transient mutation of the real uevent environment safe. Combined
with the earlier unsuppressed reset, the remaining failure boundary is the OF
entry remaining present during event emission. A follow-up must add a durable,
independent observation around dispatch and cleanup; repeating an identical
unsuppressed artifact would not be decision-changing.
