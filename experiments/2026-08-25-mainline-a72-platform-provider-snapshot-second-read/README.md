# Experiment: A72 platform plus DA921x provider snapshot as the second read

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-25-mainline-a72-platform-provider-snapshot-second-read` |
| Status | definition frozen; patch generation pending |
| Subsystem | MT6797 A72 platform state and DA921x read-only provider snapshot |
| Device variant | Gemini PDA, named project device |
| Date | 2026-08-25 |
| Boot path | retained LK, owner-selected non-primary `boot2` |

## Question or hypothesis

Can the exact runtime-passed platform snapshot be followed by exactly one
stable DA921x provider snapshot while Stage-27 serviceability remains intact
and every later physical reader, publication path, owner mutation, and CPU
action stays closed?

The predecessor proved one stable two-sample platform snapshot on the named
device. The DA921x snapshot implementation separately passed its hardware-free
source/KUnit separation and earlier named-device read-only observations, but it
has not yet been composed immediately after this exact platform reader with an
independent retained boundary around only the provider call.

## Exact boundary

The candidate-only observer performs, in order:

1. one previously qualified A72 platform snapshot: two stable samples and 26
   read-only register observations;
2. retained record 1 immediately before the provider call;
3. one DA921x provider snapshot: two stable samples of the fixed register order
   `0x56,0x51,0x5e,0xd9,0xda`, ten pointer/read I2C transfers total, adapter
   retries temporarily forced to zero and restored; and
4. retained record 2 only after a valid provider result.

There is no loop or observer retry. Every failure clears the complete combined
result. The experiment compiles no positive provider transaction, Buck-B
writer, or firmware-writer transaction window and invokes no protected-clock
read, BigiDVFS read, secure call, publication, provider acquire/release, owner
mutation, or CPU request.

## Provenance

- Canonical parent: `patches/v7.1.3/0366-soc-mediatek-test-A72-platform-snapshot-observer.patch`.
- Prepared Buildbox source state:
  `214e7ca10cba99206c585a3c3f7a6aca707c244eeb7a535fea41f9eed7db994b`.
- Prepared-source integrity:
  `b28fccedcbd5e114b5c33d0a5c21deb9e892d35455a965182559c5a1026afc9c`.
- Planned canonical changes: `0367` provider-boundary retained ledger, `0368`
  one-shot platform/provider observer, `0369` binding, and `0370` focused
  injected tests.
- Build backend: Buildbox only. A native VM kernel build is prohibited unless
  the owner explicitly requests that specific build.

Exact source identities, effects, exclusions, and result fields are pinned in
[`contract.json`](contract.json). The implementation and decision boundary is
frozen in [`DESIGN.md`](DESIGN.md).

The local definition validator passes and rejects eight mutations spanning
parent identity, retained CRC, call order, CPU closure, later-reader admission,
patch inventory, injected-test coverage, and Buildbox dispatch. Bash syntax,
Python compilation, and ShellCheck pass. The sanitized receipt is
[`results/prebuild-definition-20260825.txt`](results/prebuild-definition-20260825.txt).

Buildbox generation attempt 1 from signed commit `3372cd01` passed every
source phase, exact patch scope, and byte-identical replay. Strict checkpatch
then rejected patch `0368` only for seven declaration/call line-layout checks,
with zero errors or warnings. No patch was admitted, no kernel was built, and
no device action occurred. The correction changes only those flagged line
breaks. See
[`results/generation-attempt-1-style-rejected.txt`](results/generation-attempt-1-style-rejected.txt).

Buildbox generation attempt 2 from signed commit `cfb1295e` again passed every
source phase, exact patch scope, and byte-identical replay. The first correction
removed all seven line-end checks; strict checkpatch stopped on four remaining
continuation-alignment checks in patch `0368`, again with zero errors or
warnings. No patch was admitted, no kernel was built, and no device action
occurred. The second correction only shortens two private helper names and
aligns their declarations and calls; the observer order and effects remain
unchanged. See
[`results/generation-attempt-2-alignment-rejected.txt`](results/generation-attempt-2-alignment-rejected.txt).

Buildbox generation attempt 3 from signed commit `d1e0f816` made patch `0368`
strict-style clean and reached patch `0370`. Every source phase, exact patch
scope, and byte-identical replay passed; strict checkpatch stopped only on two
test-helper continuation-alignment checks, with zero errors or warnings. No
patch was admitted, no kernel was built, and no device action occurred. The
third correction shortens only those two private KUnit helper names and aligns
their declarations. See
[`results/generation-attempt-3-test-alignment-rejected.txt`](results/generation-attempt-3-test-alignment-rejected.txt).

## Safety assessment

CPU8 and CPU9 remain closed by exact `maxcpus=8`. This definition adds only ten
fixed read-only DA921x transactions after the already qualified platform read,
plus at most two short retained-RAM writes. It performs no storage access,
register-data write, clock operation, secure call, provider action, regulator
action, reset, reboot, power transition, publication, owner mutation, or CPU
request.

This definition is not yet a patch, build, boot candidate, device action, or
hardware result. Patch generation must first reproduce the exact prepared
source, pass strict scope/replay/style gates, and preserve every manifest
series invariant. Buildbox KUnit must then prove the six success/failure
boundaries before any device-profile build is considered.

## Pre-boot decision map

| Unique result | Interpretation | Decision |
| --- | --- | --- |
| Exact live identity, Stage-27 serviceability, complete platform and provider value/count receipt | Both isolated readers completed in order | Qualify the provider tuple in this composition and isolate the protected-clock reader next |
| Exact live identity with observer unbound and a bounded error | Acquisition or one reader refused without a reset | Repair only the exact live error boundary |
| Changed-ID Gemian with no exact record | Platform did not complete or attribution was not reached | Use live/retained evidence to subdivide before-provider work; do not implicate DA921x |
| Changed-ID Gemian with only `before-provider` | Failure occurred inside the one DA921x provider snapshot | Split the ten fixed read operations; do not retry unchanged |
| Changed-ID Gemian with both exact records | Provider snapshot returned; failure is after the admitted read boundary | Repair only post-checkpoint serviceability or observation |
| Neither exact live mainline nor changed-ID Gemian | Observation incomplete | Diagnose transport or boot selection without assigning a kernel result |

Only one owner-selected attempt is allowed after every offline, Buildbox,
container, deployment, and pre-armed runtime gate passes.

## Next

Generate the four planned patches on Buildbox from one signed, pushed, clean
commit. Admit only byte-identical fetched patches after exact replay and strict
style validation, then add isolated KUnit and device profiles without changing
the default profile.
