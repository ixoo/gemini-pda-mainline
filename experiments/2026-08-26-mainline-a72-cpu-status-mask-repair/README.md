# A72 CPU-status stability mask repair

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-a72-cpu-status-mask-repair` |
| Status | prebuild admission passed; Buildbox KUnit submission next |
| Subsystem | MT6797 A72 platform-state source and runtime transport |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-26 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, A72 platform-state acceptance |

## Question or hypothesis

Does limiting the two CPU-status stability comparisons to their source-backed
CPU8/CPU9 identity bits 7:6 remove the observed false `-EAGAIN` without hiding
an A72-relevant transition or changing the two-sample hardware ceiling?

Exact predecessor `9ac8e004` reached a serviceable mainline session. Its two
completed samples differed only in CPU-status bits 11 and 13. CPU8/CPU9 bits
7:6, their on-state intersection, and all seven other platform comparisons
were stable. The earlier owner audit explicitly states that only bits 7:6
identify CPU8/CPU9 and that unrelated full-word changes must not invalidate A72
state.

## Selected repair

Keep both full raw CPU-status words in every sample and failure detail, but
compute movement for each word from `GENMASK(7, 6)` only. Preserve the other
seven comparison rules, CCI-busy precedence, exactly two completed reads, zero
retry, and second-sample publication on success.

Hardware-free tests must prove:

1. each of bits 6 and 7 in each CPU-status word still produces the matching
   movement bit and `-EAGAIN`;
2. the exact observed bit-11/bit-13 pair succeeds and publishes the complete
   second raw sample;
3. CCI busy still wins over simultaneous A72-bit movement;
4. read-error, failure-zeroing, every other movement field, and masked-noise
   behavior remain unchanged; and
5. no third read, retry, delay, or hardware action is introduced.

The runtime transport also changes from one unbounded base64 shell line to
bounded in-memory chunks. It creates no device file, storage write, or reboot
request, and reconstructs the exact source-pinned probe before execution.

## Safety assessment

The kernel repair only narrows a read-only comparison to the already documented
A72 identity mask. It adds no register access, MMIO write, I2C transfer, clock
operation, retained-RAM write, secure call, provider transaction, owner
mutation, publication, or CPU request. CPU8 and CPU9 remain offline through
`maxcpus=8`. The collector transport operates only in the initramfs shell's
memory and remains read-only.

No device build or action is allowed until deterministic patches, mutation
tests, canonical-series audits, strict Checkpatch, Buildbox KUnit compilation,
and focused no-network QEMU KUnit all pass. The ordered continuation is owned
only by [`docs/ROADMAP.md`](../../docs/ROADMAP.md#7-bring-up-cpu8).

## Current result

Canonical patches `0382`--`0383` implement the mask and its focused KUnit
coverage. Two generations are byte-identical, eight source mutations fail
closed, all 142 manifest profiles preserve canonical order, and both patches
pass strict Checkpatch with zero diagnostics. The bounded transport reproduces
an exact payload larger than 20 KiB with 768-character chunks and an
820-character maximum command line, without a remote file or storage write.

The frozen prebuild definition passes. Its selected continuation is a signed,
pushed, clean-tree Buildbox KUnit build followed by focused no-network QEMU
validation. No native VM build, hardware write, or CPU request has occurred.
