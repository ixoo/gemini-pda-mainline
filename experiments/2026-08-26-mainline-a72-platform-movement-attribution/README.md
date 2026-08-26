# A72 platform movement attribution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-a72-platform-movement-attribution` |
| Status | canonical prebuild and static-review gates pass; Buildbox KUnit pending |
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

Generate two canonical patches: production failure detail and focused KUnit
coverage. Audit their scope and every manifest-selected series before building.
Compile and run the isolated no-network KUnit profile on Buildbox first. Only a
clean committed and pushed revision may then build a distinct same-DT device
candidate on Buildbox.

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
order. No native VM build or device action occurred.

The next action is a clean signed commit and push, followed by
`a72-platform-movement-kunit` on Buildbox. Only a passing package and exact
13-test no-network QEMU transcript can authorize building the separate device
profile.
