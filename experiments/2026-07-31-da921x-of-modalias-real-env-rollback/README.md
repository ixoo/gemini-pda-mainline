# DA921x real OF-modalias uevent insertion and rollback

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-of-modalias-real-env-rollback` |
| Status | `installed to boot2; runtime pending` |
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
