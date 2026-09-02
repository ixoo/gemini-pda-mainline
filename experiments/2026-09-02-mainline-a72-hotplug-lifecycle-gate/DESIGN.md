# CPU9 physical-off and same-boot restore design

## End state

This gate is complete only when the exact current-mainline path physically
offlines CPU9, keeps CPU8 and CPUs 0--7 usable, and restores CPU9 in the same
boot. A logical park, scheduler isolation, or writable sysfs file is not a
substitute for PSCI `CPU_OFF` plus a later distinct `CPU_ON`.

The first transition is deliberately CPU9-only. The exact secure-source audit
shows that CPU9-off with CPU8 retained takes the per-core branch and leaves the
A72 cluster, CCI, clocks, SPM shared state, and Buck-B provider untouched. The
last-A72 CPU8-off branch has a much larger unresolved effect set and remains
forbidden.

## Why current Linux cannot perform the experiment

The exact prepared source has all of these properties:

- `mt6797_psci_cpu_can_disable()` always returns `false`;
- `struct cpu_operations` has owner handoffs for CPU-up but none for
  controller-side CPU-down admission or completion;
- the MT6797 membership owner implements initial CPU8-up and CPU9-up, while
  the enum-only CPU9-off and last-CPU8-off slots have no production state
  transitions;
- P32 `.cpu_disable`, `.cpu_die`, and `.cpu_kill` guards match only a failed
  CPU-up rollback transaction; and
- both initial CPU-up attempt bits are consumed after the accepted 4+4+2
  bring-up, so a restored CPU9 cannot truthfully reuse the initial CPU9-up
  identity.

Changing the `cpu_can_disable` return alone would therefore expose a generic
path with no down owner, no distinct restore token, and repeated active PSCI
affinity queries.

## Generic lifecycle handoffs

The first kernel change adds four optional, no-op-by-default architecture
handoffs. They do not make any CPU hotpluggable.

1. `cpu_down_preflight` runs before `cpu_maps_update_begin()`. A later exact
   controller may mint one request identity without reversing the established
   transition-lock then CPU-map-lock ordering.
2. `cpu_down_validate` runs after the CPU map lock is held and before
   `cpus_write_lock()`. It binds that identity to the final target and rejects
   internal/bypass callers that did not pass preflight.
3. `cpu_down_complete` runs after the requested down callbacks succeed and
   before `cpus_write_unlock()`. It may finalize only an already-proven
   physical-off transaction.
4. `cpu_down_failed` runs after the CPU map lock is released for every
   nonzero result following a successful preflight. Before the CPU_OFF commit,
   it releases only attempt-owned software state; after the commit, it records
   a terminal retained fault and cannot retry or invent a rollback.

All unset methods return zero. The MT6797 operation table remains unset in the
first patch, and its `cpu_can_disable=false` veto remains byte-for-byte intact.
Focused KUnit uses only injected state and cannot issue PSCI, CPU, MMIO,
watchdog, retained-RAM, or device operations.

## CPU9 down owner

The second hardware-free phase adds a boot-local, non-rearmable CPU9-down
transaction. Its entry state is exact: members `0x3`, CPUs 8 and 9 online,
CPU8/CPU9 up parents retired successfully, provider held, no active owner, and
no suspend or policy transition. It consumes a new CPU9-off attempt; it never
recycles an initial-up attempt.

The target `.cpu_disable` handoff freezes the transaction before Linux removes
topology, NUMA, online, IPI, and IRQ state. Immediately before target-side
PSCI `CPU_OFF`, the owner publishes an immutable commit record. Once committed,
no software rollback, retry, or guessed inverse is allowed.

The controller-side `.cpu_kill` handoff owns exactly one level-0 affinity call.
That call is active: secure firmware uses it to perform CPU9 per-core MTCMOS
teardown. It is not a passive observer, and a second query is forbidden.
Success additionally requires an independent CPU9 per-core power readback, a
bounded callback on retained CPU8, and invariant cluster/provider/clock/CCI
state before Linux membership may commit from `0x3` to `0x1`.

## Bounded recovery despite an unbounded secure call

The secure audit found two reachable CPU9 per-core polling loops without an
inner timeout. Linux cannot make the SMC intrinsically bounded. Before any
target mutation, the experiment therefore arms the existing independent
15-second recovery watchdog. It is never refreshed after the CPU_OFF commit.

If target CPU_OFF returns, affinity blocks, a readback fails, or the down
completion cannot be proved, the owner retains conservative state and permits
only reset recovery. There is no retry. Changed-boot-ID Gemian recovery,
retained attribution, and unchanged boot2 are required to classify the result.

## Distinct CPU9 restore

A successful offline commit creates a new, separate CPU9-restore attempt.
Existing generic CPU-up lifecycle handoffs remain authoritative, but the
membership owner must distinguish restore from initial CPU9-up. Restore entry
requires members `0x1`, CPU8 online, CPU9 offline, the exact retired off
transaction, unchanged provider/reference/shared state, and the still-armed
watchdog.

Exactly one CPU_ON is permitted. Success requires arm64 secondary completion,
full generic CPUHP completion, membership `0x3`, the accepted 4+4+2 topology,
USB/netcat serviceability, and independent CPU8/CPU9 scheduler accounting.
Only then may the owner retire the restore and cancel the watchdog.

## Phase boundaries

The ordered implementation is:

1. add and hardware-free-test generic down handoffs, including failure
   publication after CPU-map unlock;
2. add and hardware-free-test the CPU9 down/restore owner and all failure
   states;
3. compile the isolated profile and focused KUnit on Buildbox;
4. construct and independently validate one exact boot2 candidate, its
   retained attribution, trigger, recovery, and forbidden-action oracle; and
5. spend one fresh physical boot on CPU9 off then same-boot restore.

No phase adds CPU8-last-off, CPU0--7 off, cpufreq, OPP, thermal, idle, suspend,
device-storage writes, or a native VM build.
