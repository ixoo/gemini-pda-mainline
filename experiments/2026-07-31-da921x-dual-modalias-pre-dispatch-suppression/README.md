# DA921x dual-modalias event pre-dispatch suppression

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-pre-dispatch-suppression` |
| Status | `ready for deployment` |
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
