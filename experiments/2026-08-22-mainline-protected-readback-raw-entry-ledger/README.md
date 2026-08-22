# Experiment: protected-readback raw-entry ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-22-mainline-protected-readback-raw-entry-ledger` |
| Status | defined; Buildbox build and device attempt pending |
| Subsystem | MT6797 protected clock read / retained ramoops checkpoint |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-22 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, protected-readback localization |

## Question or hypothesis

Does the first MT6797 protected-clock read return when bracketed by two
independently recoverable records, once the ledger accepts the runtime-proven
raw all-ones entry state instead of requiring a Gemian-initialized empty
header?

The exact hypothesis is:

1. records 171--174 enter mainline with header words all equal to `0xffffffff`;
2. checkpoint zero can commit owned record 173 by writing payload, start, and
   size before the valid signature, with a full local readback;
3. the existing protected-clock read is invoked exactly once; and
4. only if it returns can checkpoint one commit owned record 174 in the same
   way.

Changed-ID Gemian recovery is the independent oracle. Record 173 alone means
the protected-clock call was entered but did not return. Both records mean it
returned. Neither record rejects entry, mapping, or the first commit before
making an inference about the protected call.

## Provenance and environment

- Foundation runtime evidence: signed and pushed mapping-control evidence at
  commit `c9bcfdbb86b674b24ff3c1f3b6906df7d3156989`.
- Causal source correction: signed and pushed commit
  `5f81580f927425880ecb55245e6920f5d8d3e15d`.
- Parent build profile: `protected-readback-call-ledger`.
- New profile: `protected-readback-raw-entry-ledger`.
- Canonical patch: `0331-pstore-accept-Gemini-raw-entry-ledger.patch`.
- Expected release: `7.1.3-gemini-protected-raw`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The mode is default off and remains inside the existing exact Gemini DT and
reservation gates. Normal ramoops registration stays skipped. It requires the
all-ones header on every not-yet-owned record and never clears or overwrites a
valid or otherwise different header. It commits only records 173 and 174,
writes the signature last, fully reads back each record, and never retries.

The raw-mode observer acquires only the protected-clock backend. It performs at
most one read through that backend between the two records and makes no
BigiDVFS read. It adds no firmware write, regulator action, clock transition,
I2C transaction, transition owner, storage access, CPU request, timer,
watchdog, reset, or power operation. CPU8 and CPU9 admission remain closed.

## Associated code

- `patches/v7.1.3/0331-pstore-accept-Gemini-raw-entry-ledger.patch`
- `configs/gemini-protected-readback-raw-entry-ledger.fragment`
- `contract.json`
- `scripts/validate.py`

## Procedure

1. Validate the exact patch, profile, canonical-series placement, default-off
   mode, raw prefix, signature-last ordering, full readback, clock-only
   observer, and prohibited-action inventory.
2. Commit and push the definition with a clean worktree.
3. Build exact commit on Buildbox using
   `KERNEL_PROFILE=protected-readback-raw-entry-ledger ./scripts/build-kernel --backend buildbox`.
4. Fetch only the validated package, construct the serviceability DT and
   Android-v0 container twice independently, and require the complete LK,
   configuration, DT, padding, and mutation gates.
5. Install the exact admitted candidate to resolved inactive `boot2` under the
   standing guarded workflow, verify the full-partition readback, and shut down.
6. Arm the observer before one physical `boot2` selection. Recover only after
   a confirmed cycle into changed-ID Gemian and classify records 173 and 174
   before any repeat or successor.

## Analysis

This candidate does not infer that all ones are a valid ramoops record. They
are only the exact entry precondition observed by both mainline mapping models.
The valid signature is the last store that commits each new record, so a reset
during payload or metadata construction leaves an invalid header. Gemian's
ordinary ramoops initialization can then either recover a fully committed
record or normalize an invalid partial record; it cannot mistake an
all-ones/partial header for success.

The second record precedes every BigiDVFS action because raw mode removes that
action entirely. Its recovery therefore answers only whether the one
protected-clock read returned.

## Conclusion

Pending build and runtime evidence. This definition makes no hardware-support
claim and does not open CPU8 or CPU9 admission.

## Follow-up

If both records recover, proceed to the separately ordered read-free clock-node
population experiment. If only record 173 recovers, localize inside the
protected-clock transport without repeating this artifact. If neither
recovers, repair the exact raw-entry commit path before another protected call.
