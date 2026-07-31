# DA921x dual-modalias event pre-dispatch suppression

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-pre-dispatch-suppression` |
| Status | `failed before serviceability; exact checkpoint unobserved` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Does the pre-serviceability reset require netlink processing of the complete
dual-modalias device event, or is successful ten-entry environment assembly,
normal cleanup, and a successful uevent return already sufficient?

The candidate preserves the real OF child, unbound module-free baseline, and
normal event construction. It requires the exact ordered OF and I2C modaliases,
then the numeric sequence entry, before skipping only transport. The existing
caller converts this exact match to success and frees the environment normally.

## Decision

- Serviceability with the exact marker proves complete dual-modalias assembly,
  successful return, and cleanup safe, isolating the reset to netlink message
  construction or delivery.
- A reset after the marker implicates the successful completion/cleanup side of
  the split without any broadcast.
- A missing marker is a validation failure, not hardware evidence for either
  branch, and must not be promoted to a PASS.

## Safety

The patch adds no driver, provider, transfer, register access, or storage path.
It suppresses only the exact target add-event before netlink broadcast. The
DA921x driver remains module-only and absent from the initramfs, CPUs 8 and 9
remain offline, and runtime acceptance requires an unbound real OF client,
zero I2C/oracle counters, and the complete serviceability baseline.

The experiment patch has actual author metadata but no DCO sign-off. It is
experiment-only and not submission-ready.

## Selected candidate

The validated `7.1.3-gemini-da921x-dualpre` package was assembled twice from
the exact Gate 3 real-compatible DT and module-free initramfs. Both assemblies
were byte-identical. The retained Android-v0 container passed all 32 LK gates.

| Item | SHA-256 |
| --- | --- |
| Kernel `Image.gz` | `f43e65ebdf7be3e94f006235f1230f996dbfb6ef55db3cd3471455f3c103c21e` |
| Kernel configuration | `96bb06d56eb4034ff59909fa205675d834241a7eec9bbdd6a86b5719fc39a23f` |
| Real-compatible DT | `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806` |
| Module-free initramfs | `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f` |
| Boot container | `8be48f4356d1b4fd5a28a914b146da5394bff32ef4dace28a99d01fd1774db75` |
| Exact 16 MiB boot2 image | `ddb7fadf7cd41f7ef805e2120f299b8034b7fc5ccedea2b6da7fb9976794e072` |
| Candidate manifest | `81cdca19d56faba451804d358d631c9fe3b50624522768d9bb19fa0e0b1da648` |

The installer resolves `boot2` from the live GPT, requires the preceding
fail-closed pre-dispatch candidate, performs a full post-write readback,
creates no new partition backup, and powers the device off after verified
success.

## Deployment

Attempt 1 stopped safely before upload or partition write because the host and
remote temporary-path allowlists disagreed. The corrected installer was
reviewed and published before retrying. No temporary upload remained.

Attempt 2 resolved logical `boot2` to `/dev/mmcblk0p30` while the known-good
Gemian root was `/dev/mmcblk0p29`. The expected predecessor matched, power was
stable at 100% with good battery health, and the write, flush, target checksum,
and independent full readback all matched the exact candidate. No new backup
was created. The device shut down cleanly after verification and awaits the
first selected boot.

## Runtime result

On the first selected boot, the display turned white and the device rebooted
automatically before console or USB/netcat serviceability was established.
Returned Gemian had a changed boot ID and reported the watchdog-class reason
`wdt_by_pass_pwk`. The live GPT still resolved `boot2` to `/dev/mmcblk0p30`,
whose full-partition checksum matched the exact candidate; Gemian remained on
`/dev/mmcblk0p29`. Pstore contained no regular files.

No runtime marker survived, so the exact validation checkpoint is not proven
to have executed. This is a failed serviceability result, not proof that
ten-entry assembly or successful cleanup alone caused the reset. The exact
artifact must not be repeated unchanged. Source inspection also confirms that
`device_add()` ignores the uevent return value, leaving the validation work and
its immediate `pr_info()` checkpoint as the only effective differences from
the earlier serviceable fail-closed path. The next discriminator therefore
needs to remove that printk and expose validation state through an independent
read-only observation path if serviceability survives.
