# A72 CPU-status stability mask repair

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-a72-cpu-status-mask-repair` |
| Status | candidate and deployment tooling pass; boot2 install next |
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

The device build was held until deterministic patches, mutation tests,
canonical-series audits, strict Checkpatch, Buildbox KUnit compilation, and
focused no-network QEMU KUnit all passed. A hardware action remains gated on
an exact same-DT candidate, independent LK validation, the exact predecessor,
live GPT resolution, stable power, full readback, and shutdown. The ordered
continuation is owned only by
[`docs/ROADMAP.md`](../../docs/ROADMAP.md#7-bring-up-cpu8).

## Current result

Canonical patches `0382`--`0383` implement the mask and its focused KUnit
coverage. Two generations are byte-identical, eight source mutations fail
closed, all 142 manifest profiles preserve canonical order, and both patches
pass strict Checkpatch with zero diagnostics. The bounded transport reproduces
an exact payload larger than 20 KiB with 768-character chunks and an
820-character maximum command line, without a remote file or storage write.

Signed commit `7fb8f50d` is published and compiles on Buildbox as exact release
`7.1.3-gemini-a72-cpumask-kunit`; its fetched package passes checksum and
provenance validation. Focused no-network QEMU then passes both suites: six
platform-state cases plus eight preserved composed-observer cases, 14 total,
with zero failures and zero skips. The classifier rejects all six transcript
mutations and observes the expected post-test rootfs panic only after both
suites complete.

The hardware-free gate is therefore closed. Exact clean commit `8b087b98`
builds the same-DT `maxcpus=8` device profile on Buildbox as
`7.1.3-gemini-a72-cpumask`; the fetched package passes provenance and checksum
validation. Two independent assemblies and two independent padding paths are
byte-identical. Raw image `ebaddc69` pads to exact 16 MiB candidate
`6219357a`; all 32 LK gates pass, the DT remains exact `90cfc29b`, and six
container mutations are rejected.

The source-pinned installer requires exact full-partition predecessor
`9ac8e004`, resolves inactive `boot2` from the live GPT, makes no fresh backup,
requires a full readback, and shuts down without reboot after success. The
runtime collector converts the inherited one-line payload to 40 bounded
in-memory commands with an observed maximum of 812 characters; it creates no
remote file. Seven serviceable result branches pass and the inherited 23
runtime mutations plus two retargeted identity mutations remain rejected. No
native VM build or CPU request has occurred.

The first real deployment exposed a shutdown-confirmation defect in the
inherited installer: Gemian stopped accepting SSH sessions while its TCP/22
listener remained open, so session failure alone falsely reported shutdown.
The corrected wrapper now also requires TCP/22 to close and fails otherwise;
it never sends a reboot or an additional poweroff request.

The exact deployment itself passed every live-GPT, predecessor, power, TEE,
retained-header, write, flush, full-partition, and independent-readback gate.
Inactive `boot2` now contains exact `6219357a`. The clean Gemian poweroff
request left the device half-responsive: SSH authentication still completed
and TCP/22 still served a banner, but a session could not open. Therefore
shutdown is explicitly unconfirmed and no physical `boot2` selection is
allowed yet. The next action is to confirm actual power-off; only then may the
bounded collector be armed and this candidate booted once.
