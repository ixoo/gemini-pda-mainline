# A72 platform/provider failure-stage attribution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-25-mainline-a72-platform-provider-failure-stage-attribution` |
| Status | two patches admitted byte-for-byte; 138 profile-series checks pass; isolated Buildbox KUnit compile pending |
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
fragments, and all 138 manifest-series invariants pass. The next action is the
isolated KUnit profile on Buildbox, followed by its no-network QEMU suite. No
native build or device action has occurred for this derivative.
