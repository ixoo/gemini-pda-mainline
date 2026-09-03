# CPU9 physical executor contract

## Purpose

This contract is the implementation boundary between the hardware-free CPU9
down/restore owner and any callback that can invoke PSCI or observe live MT6797
state. It does not bind a callback, expose CPU hotplug, select a candidate, or
authorize a device action.

The executor is split across the generic controller, target CPU9, and retained
CPU8. No synchronous wrapper may pretend that target `CPU_OFF` and the later
controller-side `AFFINITY_INFO` call are one bounded function.

## Watchdog correction

The established CPU8 transition takes irreversible ownership of the TOPRGU
watchdog before its first physical mutation. The owner has no cancellation or
refresh API. The CPU9 physical executor must therefore inherit and validate
that exact already-armed watchdog identity. It must not take over the watchdog
again, reload it, cancel it, or claim that the secure call is intrinsically
bounded.

This supersedes the earlier design sentence that allowed cancellation after a
successful restore. A successful physical result must be durably committed
before the original 15-second deadline, after which the expected reset returns
the device to the known-good OS. The reset is recovery and experiment
termination; it is not evidence that CPU9-off or restore succeeded.

## Split lifecycle

1. Controller preflight mints exactly one down identity, validates the already
   armed watchdog identity, and captures one stable baseline while CPU8 and
   CPU9 are online.
2. Generic validation binds the transaction after the CPU map lock and before
   the CPU hotplug write lock.
3. Target CPU9 disable validates the standard PSCI CPU-off guard before Linux
   removes topology, NUMA, online, IPI, and IRQ state.
4. Target CPU9 die consumes the owner CPU_OFF budget, durably checkpoints the
   immutable commit, and invokes exactly one PSCI `CPU_OFF`. A returned call is
   a post-commit fault and may only wait for reset.
5. The controller consumes exactly one level-0 `AFFINITY_INFO` budget after
   target-dead publication. The call is the active physical teardown and may
   remain inside secure firmware until the watchdog resets the unit.
6. If the call returns OFF, the controller captures one stable post-state,
   runs one bounded callback on retained CPU8, classifies per-core and shared
   state, and publishes the exact owner proof.
7. Generic completion may commit membership from `0x3` to `0x1` only after the
   proof has been accepted.
8. A separate parent-linked restore identity consumes exactly one CPU_ON.
   Success needs secondary completion, full generic CPUHP completion, restored
   4+4+2 topology, retained serviceability, and independent CPU8/CPU9 progress
   before its durable terminal is published.

## Independent readback predicate

The post-affinity sample is accepted only when:

- CPU8 bit 7 is set in both SPM CPU power-status words;
- CPU9 bit 6 is clear in both SPM CPU power-status words;
- MP2 cluster control and CPU8 core control are byte-for-byte unchanged;
- external-isolation bit 1, MP2 DCM bits 6:0, and CCI request bits 1:0 are
  unchanged, with both CCI change-pending samples clear;
- the complete five-byte provider tuple is unchanged;
- protected clock and Big iDVFS values are unchanged, excluding only their
  monotonically changing sample-generation fields; and
- CPU9's raw core-control word is retained as evidence but is not promoted to
  an acceptance mask because the audited public sources do not yet define a
  trustworthy off-value mask for that word.

The general SPM power-status words remain correlation context. A change in an
unrelated general power domain cannot decide the A72 transaction.

## Failure boundary

Before the CPU_OFF commit, a failure rejects the down request and releases only
attempt-owned software state. At or after the commit, any return, timeout,
readback mismatch, callback failure, proof failure, generic-completion failure,
or restore failure latches a terminal fault. There is no retry, second affinity
call, guessed inverse, last-A72 transition, watchdog mutation, or success from
a park-only result.

[`physical-executor-contract.json`](physical-executor-contract.json) is the
machine-readable form of this document. Its validator and rejecting mutation
suite must pass before source generation begins.
