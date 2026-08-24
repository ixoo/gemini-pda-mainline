# Experiment: mainline A72 A34 publication contract audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-a72-a34-publication-contract-audit` |
| Status | completed offline audit; current production publication rejected |
| Subsystem | MT6797 A72 A34 eligibility and lifecycle publication |
| Device variant | Gemini PDA contract; canonical-source audit only |
| Date(s) | 2026-08-23 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, A34 publication |

## Question or hypothesis

Can canonical mainline through the passing direct-state compositor safely use
the present A34 and direct-state ABIs to publish the A72 owner atomically from
`CLOSED / UNINITIALIZED` to `AVAILABLE / IDLE`, while retaining both CPU
vetoes?

The positive hypothesis requires more than a stable record shape. The input
must prove the exact recovered physical state, current-boot secure replay
applicability, pristine P30 state, target identity, and pristine membership
owner under one serializable publication contract.

## Provenance and environment

- Repository input: signed and pushed commit `5176ebf418c331a2e8aefba7aaafcabfc3234f8c`.
- Canonical prepared source state: `c020a36a674ca8ac6516f022649f143cd1d1d8834f17e5de758bc3fe0268c72e`.
- Prepared-source integrity: `54165d2bf54ca5b795d85314061fdfe0930e0b78e50927269b0746d1646625c3`.
- Canonical series ends at patch `0341`.
- The exact prepared tree was inspected read-only on Buildbox. No source tree
  was copied to or from it.

Exact file hashes and call-graph facts are in
[`results/source-audit-20260824.txt`](results/source-audit-20260824.txt).
The decision is decomposed in
[`results/decision-matrix.tsv`](results/decision-matrix.tsv).

## Safety assessment

This audit performed no build, source edit, device contact, MMIO, SMC, I2C
transfer, CPU request, boot image construction, partition access, or boot2
write. It does not authorize lifecycle publication or a device attempt.

The current CPU-up and CPU-disable vetoes remain unchanged: A72 admission
returns while the owner is closed, `mt6797_psci_cpu_boot()` still rejects, and
`mt6797_psci_cpu_can_disable()` still returns false.

## Observations

The compositor now provides a useful owner-held record. It takes the CPU
hotplug read lock and the A72 transition lock, requires CPU8 and CPU9 possible,
present, and offline, samples one registered source, verifies a pristine owner
before and after that callback, and clears its workspace on exit.

That record is not yet A34 authority:

- `mt6797_a72_direct_source_valid()` checks ABIs, validity bits, reserved
  fields, byte widths, and nonzero sample generations. It does not compare the
  provider, SPM, PWRAP, DCM, CCI, protected-clock, or BigiDVFS values with a
  recovered-state predicate.
- The direct-state ABI carries CPU8/CPU9 possible, present, and online bits,
  the raw source, and the public owner snapshot. It does not carry the CPU
  method/MPIDR identity, the private `next_generation`/`next_cookie` state, or
  P30 state. The compositor checks the two private counters for zero but does
  not publish them in its result.
- A34 ABI 1 duplicates caller-supplied topology, CPUHP, MPIDR, owner, private
  counter, and P30 fields instead of consuming the compositor record. Its
  reset-provenance positive still depends on evidence that the previous
  classifier audits proved unavailable to Linux.
- The BL31 audit proves that primary entry clears the private replay ledger,
  but only for an applicable secure-platform epoch. Canonical Linux has no
  positive current-boot owner for that applicability. Ordinary Linux reboot,
  raw TOPRGU zero, retained status zero, and software zero remain rejected.
- P30 has an internal raw spinlock and exact pristine zero state, but it has
  no bootstrap claim/interlock. The canonical call graph currently has no
  production P30 caller, which keeps the present system closed; it is not a
  durable synchronization contract for a future publisher.
- The A34 evaluator, direct-state snapshot, and P30 prepare entry points have
  no production callers in the canonical tree.

## Analysis

Publishing now would make one of two invalid substitutions. Accepting only
the direct source's structural `valid=1` would treat arbitrary stable raw
hardware values as recovered state. Retaining A34 ABI 1 would instead continue
to trust caller-populated duplicate fields and a reset-provenance positive
that canonical Linux cannot honestly produce.

The publication store itself can be made atomic under `a72_state_lock`, with
all destination fields prepared first and `health = AVAILABLE` written last.
That mechanical fact does not repair the missing input authority or protect a
pristine P30 record across the commit.

The smallest safe next slice is therefore hardware-free and remains
lifecycle-closed:

1. define a versioned A34-v2 input that embeds exactly one compositor-owned
   direct-state record plus a separately typed secure-replay applicability
   record, with no reset-cause fallback or duplicate owner/topology fields;
2. define exact field-level recovered-state predicates, including every raw
   hardware member, and reject structural validity as sufficient authority;
3. add an owner-scoped P30 pristine bootstrap claim that blocks the only
   pristine-to-active P30 edge while a future A34 commit is in progress; and
4. exercise the evaluator and interlock with injected KUnit data while adding
   no publication call, physical reader binding, or CPU operation.

Only after that slice passes may a separate review add the single membership
publication commit point. A production positive replay source and physical
source binding remain separate requirements for a decision-bearing CPU8
candidate.

## Conclusion

`rejected-current-input`: canonical A34 ABI 1 plus direct-state ABI 1 cannot
safely authorize production lifecycle publication. The compositor closes the
record-shape and lock-owned sampling boundary, but not recovered-value
eligibility, current-boot replay applicability, or P30 exclusion.

`selected-next`: implement and prove the default-off A34-v2 evaluator and P30
bootstrap interlock with injected, hardware-free tests. Keep the membership
owner closed and both CPU vetoes unchanged.

## Follow-up

[`DESIGN.md`](DESIGN.md) freezes the exact rejected substitutions, input
ownership, lock order, interlock, and fail-closed rules. The authoritative
execution order remains in [Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8).
