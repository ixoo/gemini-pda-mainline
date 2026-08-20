# Experiment: positive DA921x provider transaction

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-20-mainline-da921x-positive-provider-transaction` |
| Status | `completed` hardware-free implementation proof; canonical patches compile and focused KUnit passes 6/6 |
| Subsystem | legacy DA921x regulator, private MT6797 A72 provider seam |
| Device variant | Planet Gemini PDA named unit |
| Date | 2026-08-20 America/New_York |
| Tracking | Roadmap Gate 7 |

## Question

Can current Linux 7.1 represent the historically proven Buck-B enable and
owned inverse as one default-off, generation-bound provider state machine,
with exhaustive hardware-free failure coverage and without making CPU8 or a
physical write reachable in this phase?

## Parent and discovered prerequisite

The exact parent is repository commit
`feb1767011da40e28679e0f9293ddcb195646c7a` and managed Buildbox source state
`c9e5f2fbef9f2a25a7b6772ad122ca0f000d57f0c23789040f70f669e022c698`.

Review of the cumulative source found that the release-refusal function from
canonical patch 0173 is present, but the final provider-ops initializer lacks
its `.release` member. The registry therefore rejects that ops table at runtime.
The first logical patch restores the already intended registration. It is kept
separate from the positive transaction.

## Frozen boundary

[`contract.json`](contract.json) and [`DESIGN.md`](DESIGN.md) define the exact
prestate, two eleven-transfer operations, lock and retry rules, handle binding,
terminal failure states, and forbidden effects. The important distinction is
that the root-adapter lock covers each complete acquire or release; it is not
held across the handle lifetime.

## Validation procedure

1. Apply three deterministic source phases to checksum-pinned copies of the
   managed Buildbox source.
2. Validate the complete edited source and three normal patches.
3. Replay the patches onto the exact parent and run strict checkpatch.
4. Import the generated patches into canonical order and add isolated source
   and KUnit profiles.
5. Commit and push the exact reviewable source.
6. Compile only through Buildbox, then run the fake-adapter KUnit suite in the
   existing bounded, network-free arm64 QEMU lane.

No native VM build, device access, boot image, partition write, physical I2C
operation, CPU request, or authorization for a later physical transition is
part of this phase.

## Patch-generation result

Exact pushed repository revision
`2d621af80ecb1090bb4f2201a8d8e46157189978` generated three ordinary patches
on Buildbox. Contract, edited-source, patch, replay, and strict checkpatch
validation all passed; checkpatch reported zero errors, warnings, or checks.
The fetched package checksum manifest verified before import. The exact patch
hashes and Buildbox job are recorded in
[`results/buildbox-patch-generation-20260820.txt`](results/buildbox-patch-generation-20260820.txt).

Canonical patches 0293--0295 now preserve the prerequisite registration
repair, positive transaction, and hardware-free KUnit coverage as separate
logical changes. The isolated `da921x-positive-provider` and
`da921x-positive-provider-kunit` profiles select the stopped-firmware window
and owner seam without connecting a CPU caller.

The exact KUnit profile then compiled and linked on Buildbox at signed revision
`bfca1a05066a1619e074ea73ad01e736cb72aace`. Both the production regulator
object and focused provider-test object built, and the fetched package passed
its full checksum manifest. Exact identities are in
[`results/buildbox-compile-20260820.txt`](results/buildbox-compile-20260820.txt).

The same Image and resolved configuration reproduced after the QEMU harness
was committed at exact revision
`43099ac1dcfa5da1fa0bb3bd4a8b9de71f033f50`. The Gemini DTB differs only in
its two repository-commit provenance fields, as designed. The exact comparison
is recorded in
[`results/buildbox-reproduction-20260820.txt`](results/buildbox-reproduction-20260820.txt).

## KUnit result and conclusion

One bounded, network-free arm64 QEMU run of the exact fetched Buildbox Image
passed the sole `da9213-legacy-positive-provider` suite: all six declared cases
passed with zero failures or skips. The cases cover successful lifecycle,
one-shot admission, every negative and short acquire/release transfer ordinal,
and every owned-state mismatch ordinal. The later root-filesystem panic is the
declared end boundary for this kernel-without-rootfs lane; QEMU was terminated
by the expected 45-second timeout only after complete KTAP success.

The sanitized receipt is
[`results/kunit-qemu-20260820.txt`](results/kunit-qemu-20260820.txt). The raw
log remains ignored below `artifacts/qemu/` and is identified by checksum in
that receipt.

This completes the hardware-free positive-provider implementation proof. It
does not prove a physical `BUCKB_CONT` transition, connect P24/P28/P30, lift
either CPU veto, create a boot candidate, or authorize device execution. The
authoritative next boundary remains in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8).
