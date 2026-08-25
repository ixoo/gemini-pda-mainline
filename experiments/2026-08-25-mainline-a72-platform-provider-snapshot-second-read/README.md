# Experiment: A72 platform plus DA921x provider snapshot as the second read

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-25-mainline-a72-platform-provider-snapshot-second-read` |
| Status | complete; provider-not-ready boundary localized; artifact retired |
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

Generation attempt 4 from signed commit `170f3732` passes every source phase,
exact patch inventory and scope, byte-identical replay, injected-test structure,
and strict checkpatch with zero errors, warnings, or checks for all four
patches. The fetched package's full checksum manifest passes. Canonical patches
`0367`--`0370` match the fetched files byte-for-byte, and the canonical-series
invariant passes across all 131 profiles after adding isolated KUnit and device
profiles. See
[`results/buildbox-generation-20260825.txt`](results/buildbox-generation-20260825.txt).
No kernel build, boot candidate, retained-RAM write, or device action occurred.

The isolated `a72-platform-provider-snapshot-kunit` Buildbox profile then
compiled exact published commit `2c224492`. Package checksums pass; the required
platform snapshot, provider snapshot, composition, and suite symbols are linked,
while the Buck-B writer, positive provider transaction helpers, same-value
writer, A34 evaluator, and atomic publisher symbols are absent. No-network arm64
QEMU executed exactly the intended suite: all six cases passed with zero
failures or skips. The VM performed no physical I2C, MMIO, retained-RAM, SMC,
provider transaction, owner mutation, publication, CPU request, or device
action. See the
[`compile receipt`](results/buildbox-kunit-compile-20260825.txt) and
[`QEMU receipt`](results/kunit-qemu-pass-20260825.txt).

The isolated device profile then compiled exact published commit `2a936080`
on Buildbox. The fetched package checksum manifest passes and pins release
`7.1.3-gemini-a72-provider-read`, patchset `80b97d1e`, configuration
`2838806a`, Image `661c6221`, and System.map `5071bd36`. No native VM build or
device action occurred. See
[`results/buildbox-candidate-compile-20260825.txt`](results/buildbox-candidate-compile-20260825.txt).

The candidate DT starts from exact runtime-passed predecessor `3c6c54ff`. It
removes the platform-only observer, retains its already assigned platform-state
phandle, and adds only the composed observer and its one reference. Two
derivations are byte-identical; replacing the composed observer with the old
observer recovers the byte-identical sorted predecessor tree. DA921x, all three
passed backends, and every Stage-27 serviceability node remain exact. The
derived DT is `ee8baf00`. See
[`results/offline-dtb-validation-20260825.txt`](results/offline-dtb-validation-20260825.txt).

Two raw assemblies and two padding constructions are byte-identical. The exact
raw candidate is `32059676`; the exact 16 MiB `boot2` identity is
`ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f`.
All 32 LK gates pass, six container corruptions fail closed, the live
classifier accepts only its complete result and rejects 21 mutations, and the
changed-ID recovery classifier accepts the three predeclared retained branches
while rejecting 15 malformed or conflicting mutations. The guarded installer
retains live-GPT resolution, inactive/unmounted target, power, sync, flush,
full readback, and clean-shutdown gates and makes no fresh backup. See
[`results/offline-candidate-validation-20260825.txt`](results/offline-candidate-validation-20260825.txt).

The first guarded deployment invocation failed closed before any device write:
the initially derived installer still accepted only the older Stage-27 control
pair, while the running predecessor had produced the completed platform
snapshot this experiment intentionally supersedes. Read-only Gemian recovery
proved exact `GAPS-20260824-A` before/after records with slot hashes `11623055`
and `7f79d34e`. The experiment-local wrapper now accepts only an exact empty
pair or those two independently reconstructed full-slot identities; every
other byte still fails closed, and it never clears or writes retained RAM.

The corrected preflight and deployment then passed. Live GPT resolved inactive,
unmounted logical `boot2` as `/dev/mmcblk0p30` while the active root was
`/dev/mmcblk0p29`. The exact predecessor was `39f801f7`; TEE, stable-power,
size, write, sync, flush, temporary-cleanup, and full 16 MiB readback gates all
passed. The readback is exact candidate `ff902d12`, no fresh backup or retained-
RAM write occurred, and the device shut down cleanly without reboot. See
[`results/deployment-20260825.txt`](results/deployment-20260825.txt).

The original pre-armed watcher expired after its bounded 1,800-second wait
without observing a boot and therefore consumed no attempt. When the owner
later selected `boot2`, a replacement collector attached during the same
physical start and proved exact live release
`7.1.3-gemini-a72-provider-read`, installed image `ff902d12`, boot ID
`ef73506c-274f-4a1b-96fc-a0199ad9efac`, CPUs 0--7 online and 8--9 closed, and
the complete Stage-27 USB/T-PHY/I2C5/keyboard serviceability set. All three
backends and the DA921x I2C provider were bound by the 49.09-second capture,
but the one composed observer device remained unbound with no terminal
snapshot receipt.

Live initcall timing localizes the dependency race. The observer first deferred
at 0.788627 seconds while the platform source was unavailable. The platform
source bound at 1.143926 seconds; the retried observer then reported
`-ENODEV: platform/provider snapshot failed` at 1.146260 seconds and returned
without another retry. The DA921x `1-0068` device did not bind until 46.149957
seconds. Source audit independently proves that an empty A72 provider registry
makes `mt6797_a72_provider_snapshot()` return `-ENODEV` before invoking the
DA921x callback, so this attempt performed zero provider I2C reads.

The validated USB shell then requested the normal return to Gemian. Changed-ID
recovery verified that `boot2` remained exact `ff902d12`, record 1 was the
exact `before-provider` record (`047e5c5c`), and record 2 was exact empty
(`d58e2f4e`). No memory or partition write occurred during recovery. This
independently proves that the qualified platform snapshot and first checkpoint
completed, while provider registration had not. See
[`results/runtime-attempt-1-provider-not-ready-20260825.txt`](results/runtime-attempt-1-provider-not-ready-20260825.txt).

## Safety assessment

CPU8 and CPU9 remain closed by exact `maxcpus=8`. This definition adds only ten
fixed read-only DA921x transactions after the already qualified platform read,
plus at most two short retained-RAM writes. It performs no storage access,
register-data write, clock operation, secure call, provider action, regulator
action, reset, reboot, power transition, publication, owner mutation, or CPU
request.

The hardware-free build, DT reversal, container, classifier, recovery, and
guarded deployment gates passed. The one runtime remained fully serviceable
but exposed a provider-readiness dependency before any provider I2C transfer.
The exact image is retired and must not be retried unchanged.

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

Create a separate deferred-bind repair on canonical parent `0370`. Add an
explicit DA921x provider phandle to the observer binding/DT and require that
endpoint to be present and bound before taking the platform snapshot or writing
the first checkpoint. Inject both provider-not-ready deferral and provider-ready
single-capture tests. Preserve the same 26 platform observations, ten provider
reads, two retained writes, `maxcpus=8`, and every later-action exclusion. Do
not spend a second unchanged attempt.
