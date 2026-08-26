# A72 platform movement attribution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-a72-platform-movement-attribution` |
| Status | decision-bearing runtime captured; over-broad CPU-status comparison proven; candidate retired |
| Subsystem | MT6797 A72 platform-state source and composed observer |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-26 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, platform inter-sample movement attribution |

## Question

Which existing platform-state comparison moved between the two samples that
caused exact candidate `8b6bedfd` to return `-EAGAIN` at the platform stage?

The predecessor's first attributed boot was otherwise serviceable. Its
`-EAGAIN` excludes the source's distinct CCI change-pending `-EBUSY` branch,
proves inter-sample movement, and also proves the provider, retained, clock,
publication, owner, and CPU paths were never reached.

## Discriminator

Keep the exact two-sample transaction and add an out-of-band failure detail.
On `-EAGAIN`, it carries the completed first and second samples plus a compact
nine-bit mask for the existing comparisons:

1. SPM CPU power status;
2. SPM CPU power status second word;
3. MP2 cpusys power control;
4. MP2 CPU0 power control;
5. MP2 CPU1 power control;
6. external CPU-buck isolation;
7. masked MP2 synchronous DCM;
8. masked CCI MP2 port request; and
9. PWRAP reset state.

The public stable snapshot remains all-zero on every failure. First- and
second-read errors leave the failure detail zero. CCI busy remains `-EBUSY` and
may expose the already completed pair without changing precedence. A stable
pair still publishes only the second sample.

The composed observer logs one exact movement line only when the platform stage
returns `-EAGAIN` with a complete pair. The line includes the mask and both
values for all nine comparisons, so one device boot can distinguish the field,
direction, and any simultaneous movement without another hardware access.

## Safety boundary

This derivative adds no register read or write, loop, retry, delay, provider
call, retained write, protected-clock call, gate pair, BigiDVFS read, secure
call, ownership change, publication, or CPU request. It keeps `maxcpus=8` and
the predecessor DT. Hardware-free injected tests must prove exactly two reads
on stable, busy, and moved pairs; one read on first-read failure; no third read;
all nine independent bits; masked-noise exclusion; CCI-busy precedence; zero
failure outputs where required; and unchanged composed-observer terminal
behavior.

## Validation and next action

The two canonical patches, their scope, and every manifest-selected series pass
their prebuild audits. The isolated KUnit profile compiles on Buildbox and
passes its exact no-network QEMU contract. The distinct same-DT device candidate
also compiles on Buildbox, passes its offline container gates, and is installed
on live-GPT-resolved `boot2` with a matching full-partition readback. The device
is shut down. The next action is one owner-selected `boot2` start with the
no-reboot USB collector already armed.

The ordered continuation is owned only by
[`docs/ROADMAP.md`](../../docs/ROADMAP.md#7-bring-up-cpu8).

## Current result

Deterministic generation emits canonical patches `0380` and `0381`. The
production patch adds the separate completed-pair detail, exact nine-bit mask,
unchanged legacy API, and one bounded movement log. The test patch adds a pure
in-memory platform transaction seam plus five platform cases while preserving
the eight composed-observer cases. Both patches pass strict Checkpatch with
zero errors, warnings, or checks.

Two independent generations are byte-identical. Eight source-contract
mutations and six KUnit-classifier mutations fail closed. Both isolated
fragments validate, and all 140 manifest profiles preserve canonical series
order.

Buildbox compiled exact clean commit `d2caf9df` as release
`7.1.3-gemini-a72-movement-kunit`; the fetched package passed its checksum and
provenance gates. QEMU then ran the two focused suites and all 13 cases passed
with zero failures or skips. The first classifier invocation rejected the raw
log because the tool incorrectly expected one combined 13-test totals line;
Linux emitted the actual per-suite totals of five and eight. The corrected
classifier requires exactly those two totals, continues to reject all six
negative mutations, and classifies the unchanged raw log as a pass. This was a
tooling correction, not a kernel-test retry or kernel-source change.

The separate device profile also compiled on Buildbox from exact clean commit
`1ad025c4` as release `7.1.3-gemini-a72-movement`. Its kernel is assembled with
the byte-identical retired failure-stage DT and the unchanged serviceability
ramdisk. Two raw assemblies and two independent 16 MiB padding paths are
byte-identical; all 32 LK gates pass; six container corruptions are rejected;
and the exact movement-detail marker is present once. Raw candidate
`fd070a56` pads to selected boot2 image `9ac8e004`.

The source-pinned installer requires full predecessor `8b6bedfd`, resolves
inactive and unmounted `boot2` from the live GPT, makes no fresh backup, requires
a full post-flush readback, and shuts the device down without rebooting. The
no-reboot USB collector accepts four completed clock outcomes, the exact
movement-detail platform failure, and the two later pre-clock failure stages;
23 unsafe runtime mutations fail closed.

From changed-ID Gemian boot `5047f3a3`, the read-only preflight resolved
inactive and unmounted `boot2` as `/dev/mmcblk0p30`, matched exact predecessor
`8b6bedfd`, stable external power, both TEE identities, and two logically empty
retained headers. The guarded installer wrote exact full candidate `9ac8e004`,
synced and flushed it, obtained the same full-partition checksum on independent
readback, removed temporary readback data, and confirmed shutdown. It made no
fresh partition backup, retained-RAM write, or reboot. An independent bounded
SSH probe also timed out after shutdown.

The single selected boot reached a serviceable exact mainline session as release
`7.1.3-gemini-a72-movement` with changed boot ID `6f87ca7c`. The initial
collector saw the exact USB interface and live shell banners but its one-line
probe transport did not emit the required markers. A tiny read-only command
passed over the same session. Sending the source-equivalent probe as bounded
script lines then produced a complete transcript; mechanically removing only
leading interactive prompt prefixes made the unchanged strict validator pass.

The sole failure at 46.168459 seconds is `stage=platform ret=-11
movement=003`. The first CPU-status word changed only at bit 11 and the second
only at bits 11 and 13. Both words' source-backed CPU8/CPU9 identity bits 7:6
were stable, their on-state intersection remained zero, and all MP2 cluster,
CPU0, CPU1, external-isolation, DCM, CCI-port, and PWRAP comparisons were
identical. The original platform-state design explicitly limits CPU8/CPU9
identity to bits 7:6 and forbids unrelated full-word equality from invalidating
A72 state. This proves the implementation's full-word CPU-status comparison is
over-broad; it does not prove platform instability relevant to CPU8.

The probe made no write or reboot request. After capture, the validated USB
shell returned the device to changed-ID Gemian. Candidate `9ac8e004` is retired
without an unchanged retry. No native VM build occurred. The selected next
implementation masks both CPU-status stability comparisons to `GENMASK(7, 6)`,
preserves the full raw words, proves unrelated-bit acceptance and A72-bit
rejection in hardware-free tests, and only then builds one distinct same-DT
candidate. It still makes no retry, additional read, provider action, retained
write, protected-clock call, publication, owner mutation, or CPU request.
