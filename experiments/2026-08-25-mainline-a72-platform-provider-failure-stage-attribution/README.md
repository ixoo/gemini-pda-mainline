# A72 platform/provider failure-stage attribution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-25-mainline-a72-platform-provider-failure-stage-attribution` |
| Status | exact deployment/runtime tooling passes; candidate selected; device deployment pending |
| Subsystem | MT6797 A72 platform/provider/protected-clock observer |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-25 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, pre-clock failure attribution |

## Question

Did third-reader attempt 1 return `-EAGAIN` from the platform snapshot or the
provider snapshot?

The exact prior image is retired. It reached a healthy mainline USB console,
but the composed observer logged only `capture failed: -11`; exact source order
proves the protected-clock call and retained checkpoints were not reached. The
existing return code cannot identify which of the first two readers failed.

## Discriminator

Add one out-of-band failure-stage result to the internal capture function. It
is initialized to `none`, becomes `dependency`, `platform`, `provider`, or
`before-clock` only on the corresponding pre-clock return, and is logged by the
probe with the unchanged errno. The snapshot remains byte-for-byte zero on
every pre-clock failure.

This changes no supplier lookup, sample, register access, retained checkpoint,
protected-clock call, retry, owner, publication, or CPU behavior. The distinct
candidate retains `maxcpus=8`, the exact one-call clock ceiling, and the same DT.

## Validation and next action

Two format-patches are generated deterministically from the exact canonical
post-`0377` source templates: production stage attribution and its injected
KUnit assertions. After source, patch, series, configuration, Buildbox compile,
and no-network KUnit gates pass, a separately named candidate may replace the
retired image. Its only new decision path is the explicit pre-clock stage.

The ordered continuation remains in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md#7-bring-up-cpu8).

## Current result

The deterministic generator pins all three post-`0377` source templates and
emits patches `0378` and `0379`. Source validation, exact patch inventory and
scope, six tooling mutations, byte-for-byte admission, both isolated profile
fragments, and all 138 manifest-series invariants pass.

Exact clean commit `2e507bcb` compiled on Buildbox as
`7.1.3-gemini-a72-clock-stage-kunit`; its fetched package and checksum manifest
pass. The sole no-network QEMU suite passes all eight cases with zero failures
or skips. In particular, the injected platform, provider, and before-clock
failures preserve the zero snapshot and report their exact out-of-band stage.
The test performed no physical I2C, clock-backend, MMIO, retained-RAM, secure,
provider-transaction, owner, publication, or CPU operation. No native build or
device action occurred.

Exact evidence commit `53398b8a` then compiled the separate device profile on
Buildbox as `7.1.3-gemini-a72-clock-stage`; its fetched package and checksum
manifest pass. Two raw assemblies and two exact-padding paths are byte-for-byte
identical. The decision-bearing DT is byte-identical to the retired third-reader
DT, all 32 LK gates pass, and six corrupt-container mutations fail closed. Raw
candidate `8ca14ec2` pads to exact 16 MiB `8b6bedfd`. The image retains
`maxcpus=8`, one-call/no-retry ceilings, and zero CPU requests. No device access
or hardware write occurred.

The next action is to publish these exact identities with a guarded installer
and no-reboot runtime collector. Only then may live-GPT `boot2` replace exact
predecessor `1f7bd960`, pass a full-partition readback, and shut down for one
owner-selected boot. That boot will distinguish `platform`, `provider`, or
`before-clock` without repeating the retired ambiguous image.

That tooling now passes. The source-pinned guarded installer accepts only exact
predecessor `1f7bd960`, exact candidate manifest `1a733736`, and exact padded
candidate `8b6bedfd`; it preserves the live-GPT, inactive/unmounted target,
stable-power, full-partition checksum/readback, no-fresh-backup, cleanup,
clean-shutdown, and no-reboot gates. The first read-only USB capture now records
both the snapshot lines and the exact stage-bearing failure line. Four returned
clock outcomes and exact `platform`, `provider`, and `before-clock` failures
pass; 24 stale, malformed, duplicated, or unsafe mutations fail closed.

While these tools were still unpublished and the old image remained installed,
the owner selected `boot2`. The host saw neither its expected USB interface nor
Gemian SSH during a bounded 50-second window. No kernel identity was available,
so that observation is inconclusive and is not attributed to this candidate.

Candidate `8b6bedfd` is now selected for deployment. The next action is to wait
for known-good Gemian, replace only exact live-GPT `boot2` predecessor
`1f7bd960`, verify the full readback, and shut down. One subsequent selected
boot is the sole hardware attempt for this discriminator.
