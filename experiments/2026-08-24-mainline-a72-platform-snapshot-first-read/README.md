# Experiment: A72 platform snapshot as the first physical read

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-a72-platform-snapshot-first-read` |
| Status | hardware-free Buildbox compile and focused KUnit runtime pass |
| Subsystem | MT6797 A72 platform-state read-only snapshot |
| Device variant | Gemini PDA, named project device |
| Date | 2026-08-24 |
| Boot path | retained LK, owner-selected non-primary `boot2` |

## Question or hypothesis

Can the exact runtime-passed Stage-27 reader DT complete one stable A72
platform-state snapshot while preserving serviceability and keeping every
later reader, owner, and CPU action closed?

The predecessor runtime proved that the platform-state, clock, and BigiDVFS
backends all bind cumulatively without invoking a reader. The old full physical
observer is not a valid first-read discriminator: it performs platform,
DA921x-provider, and protected-clock reads before its first retained checkpoint.

## Audited read boundary

`mt6797_a72_platform_state_snapshot()` has one mutex-protected, fixed two-sample
transaction and no loop or retry. Each sample performs exactly:

- eight SPM syscon reads;
- one spinlock-protected TOPRGU PWRAP-reset status read;
- one MCUCFG MP2 DCM read; and
- CCI status, MP2 port-control, and CCI status reads.

That is 13 read-only register observations per sample and 26 total. A busy CCI
returns `-EBUSY`; movement between samples returns `-EAGAIN`; transport errors
propagate. No path writes a register or retries.

The new candidate-only observer will retain record 1 immediately before the
snapshot call, make that call exactly once, require `valid=1`, and retain
record 2 only after success. It clears the result on every error and logs one
terminal value/count receipt only after record 2. It references no DA921x
provider, clock backend, BigiDVFS backend, compositor, publisher, owner, or CPU
operation.

## Provenance

- Canonical parent: `patches/v7.1.3/0362-pstore-add-Gemini-A72-early-initcall-ledger.patch`.
- Managed source state:
  `15cb40c8149a9c02be4e2143e733ff81b06d82c3112aaa6e96255187cd3cb6d2`.
- Managed source integrity:
  `a42dfd12969eaca5e22e88580ad8be5a5cb9b69674fd41236eafe9004bed1c74`.
- Planned canonical changes:
  `0363` retained platform-snapshot ledger, `0364` one-shot observer,
  `0365` binding, and `0366` focused injected tests.
- Build backend: Buildbox only. Native VM compilation is prohibited unless
  the owner explicitly requests it.

The Buildbox generator pins the managed source markers and every edited parent
file, produces normal `git format-patch` output with a clearly synthetic,
non-certifying author and no synthetic sign-off, replays all four patches, and
runs source and strict style validation. Patch generation performs no build,
device access, retained-memory write, or hardware operation.

Generation attempt 1 from signed commit `876a9522` stopped before producing a
patch because the intended layout insertion anchor also matched two raw-record
conditionals. The correction narrows that edit to the unique adjacent
first-dmesg layout lines; it does not change the generated source or admitted
runtime effects. No build, candidate, retained-RAM write, or device action
occurred in the failed attempt.

Generation attempt 2 from signed commit `2abfe96a` passed that layout edit and
then stopped before patch creation because the early-init mode begins both the
record table and its execution section. The second correction anchors the
insertion to the unique `gemini_prb_armed`/record-table adjacency. It likewise
changes only generator attribution, not the intended generated source or
runtime effects; no build, candidate, or device action occurred.

Generation attempt 3 from signed commit `c7232392` passed all four phased
source validators, the exact patch-shape validator, and byte-identical replay.
Strict checkpatch then rejected patch `0364` for one short Kconfig help
paragraph and six function/call layout checks. The correction changes only
line wrapping and local helper naming, applies the same layout to the not-yet-
checked KUnit patch, and preserves the validated call graph and effect counts.
No kernel build, candidate, or device action occurred.

Generation attempt 4 from signed commit `07f207fa` passed every semantic,
shape, and replay validator and eliminated all six C layout checks. The sole
remaining warning was a checkpatch parser ambiguity: a help-text continuation
began with Kconfig's reserved word `source`, so the parser ended the paragraph
after one line. Rewrapping the unchanged description resolves that false
boundary without changing code or effects. No build, candidate, or device
action occurred.

Generation attempt 5 from signed commit `b58864e8` passed every source, shape,
and replay validator and strict style for patches `0363`--`0365`. The final
KUnit patch `0366` stopped on one check requiring a blank line between the
suite declaration and registration macro. The correction adds only that blank
line. No kernel build, candidate, or device action occurred.

Generation attempt 6 from signed commit `f47ad7dc` passes all four phased
source validators, exact patch inventory and file-scope validation,
byte-identical replay, and strict checkpatch with zero errors, warnings, or
checks for every patch. The fetched package's relative checksum manifest and
an independent local patch validator pass. Canonical patches `0363`--`0366`
are byte-identical to the fetched bytes, and the manifest-series invariant
passes across all 129 profiles after adding isolated KUnit and candidate
profiles. The exact receipt is in
[`results/buildbox-generation-20260824.txt`](results/buildbox-generation-20260824.txt).
No kernel build, candidate, retained-RAM write, or device action has occurred.

The exact admitted commit `6d7af739caa324662799f4162f43a16ca93ef5dd`
then compiled successfully on Buildbox as the isolated
`a72-platform-snapshot-kunit` profile. The fetched package passes its relative
checksum manifest, contains exactly the one intended KUnit-test configuration,
links the platform snapshot boundary, and excludes the audited later writer
symbols. The compile receipt is
[`results/buildbox-kunit-compile-20260825.txt`](results/buildbox-kunit-compile-20260825.txt).

QEMU executed exactly the `mt6797-a72-platform-snapshot` suite: all four
success, before-checkpoint failure, snapshot/validity failure, and
after-checkpoint failure cases passed with zero failures or skips. The runner
uses no network, device tree, retained RAM, MMIO, physical I2C, or device
access; the expected no-root-filesystem panic occurred only after the passing
KTAP result. The classifier also rejects eight changed-release, exit, suite,
case, plan, failure, summary, or terminal-boundary fixtures. The exact
sanitized runtime receipt is
[`results/kunit-qemu-pass-6d7af739-20260825.txt`](results/kunit-qemu-pass-6d7af739-20260825.txt).
This closes the injected software boundary only; it is not physical-read or
hardware-support evidence and is not a boot candidate.

## Safety assessment

CPU8 and CPU9 remain closed by exact `maxcpus=8`. The observer performs only
the audited 26 reads plus at most two short retained-RAM records. It has no
storage access, register-data write, reset action, clock operation, protected
clock read, secure call, DA921x transaction, regulator action, publication,
owner mutation, CPU request, reboot, or power action.

The eventual candidate must preserve the exact passed Stage-27 DT and all three
bound backends, add only one observer node plus the necessary previously absent
platform-state phandle reference, reproduce byte-identically, pass
LK/container mutations, and use the guarded live-GPT `boot2`
write/readback/shutdown workflow. The exact passed predecessor DTB is
`d439ed8f4c226eda49f5bf652f16761ba3400bd0b80685bfc8f8da371d6ed9db`;
the independently reproduced observer DTB is
`3c6c54ff07dde1ee3ea234feb39a0ceef72101414f16679e3881a5461570f284`.
Removing the observer and its sole phandle property recovers a byte-identical
sorted semantic tree to the predecessor. Two independent assemblies and the
artifact checksum manifest pass; the sanitized receipt is
[`results/offline-dtb-validation-20260825.txt`](results/offline-dtb-validation-20260825.txt).

## Pre-boot decision map

| Unique result | Interpretation | Decision |
| --- | --- | --- |
| Exact live identity, Stage-27 serviceability, observer bound, complete value/count receipt | One stable platform snapshot completed | Qualify the values and isolate the next reader |
| Exact live identity with observer device unbound | The call returned a bounded error or the observer contract failed | Use the exact error/retained prefix; repair only that boundary |
| Changed-ID Gemian with only `before-platform` retained | Failure occurred inside the one snapshot or before its completion checkpoint | Split the fixed platform read sequence; do not retry unchanged |
| Changed-ID Gemian with both exact records | Snapshot returned and the later failure is outside the admitted read boundary | Repair only post-checkpoint serviceability/observation |
| Changed-ID Gemian with neither record | No snapshot is attributable | Add an earlier independent observer-entry boundary |
| Neither exact live mainline nor changed-ID Gemian | Observation incomplete | Diagnose transport/selection without assigning a kernel result |

Only one owner-selected attempt is allowed after every offline, Buildbox,
container, deployment, and pre-armed runtime gate passes.

## Next

Build the isolated `a72-platform-snapshot-candidate` profile on Buildbox,
combine it only with the exact validated observer DT, and run the offline
candidate gates. Do not change or reboot the currently healthy control boot
until the new candidate is fully validated and ready for guarded deployment.
