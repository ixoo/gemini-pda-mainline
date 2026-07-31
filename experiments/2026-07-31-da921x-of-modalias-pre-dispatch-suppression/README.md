# DA921x complete OF uevent pre-dispatch suppression

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-of-modalias-pre-dispatch-suppression` |
| Status | `ready for deployment` |
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

## Selected candidate

The validated `7.1.3-gemini-da921x-ofpredispatch` package was assembled twice
from the exact Gate 3 real-compatible DT and module-free initramfs. Both
assemblies were byte-identical. The retained Android-v0 container passed all
32 LK gates.

| Item | SHA-256 |
| --- | --- |
| Kernel `Image.gz` | `9462d48c8240a656155dc36f1acb5b3a572e7f913847ba8310f396c4ed1345ae` |
| Kernel configuration | `288a532de2ac512a1c95e5cf1b4ecfed3bd7a271305cc9abdb528d447872993e` |
| Real-compatible DT | `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806` |
| Module-free initramfs | `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f` |
| Boot container | `ffe3cbc21b67c5ad288873d78330a6cf30e2cb93471622c2d7f1fafe10eef1ec` |
| Exact 16 MiB boot2 image | `79c3bcb9afde686659be552cfb906f142f392b72c662db2dc9f623b52b3f3141` |
| Candidate manifest | `307cd9f51fce301522da07e5c3e59e96b708f059a13543cc8eadea50146b21ed` |

The installer resolves `boot2` from the live GPT, requires the validated real
environment rollback predecessor, performs a full post-write readback, creates
no new partition backup, and powers the device off after verified success.
