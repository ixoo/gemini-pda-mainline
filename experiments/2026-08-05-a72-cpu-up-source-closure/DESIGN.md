# A72 CPU-up source-closure design

## Scope and relationship to the membership contract

This design is the current design authority for implementation review of
late-A72 capability admission and the P30/P32 failure branches. The earlier
[`A72 membership and admission contract`](../2026-08-05-a72-membership-admission-contract/README.md)
remains the authority for transaction phases, membership/provider ownership,
admission, and one-shot semantics. Its original P30/P32 descriptions are
preserved as chronology but are superseded where this source audit adds branch
ownership, publication races, `.cpu_disable`, and A41.

P30 and P32 remain the only phase transitions. Branch labels P30K/C/P/E/U and
P32A/D/F/X/R are closure cases, not new transaction phases.

## A41: pre-finalization late-A72 capability accounting

### Boundary and owner

A41 runs during arm64 capability finalization for the exact MT6797 profile in
which the early boot set is CPU0-7 Cortex-A53 and CPU8-9 Cortex-A72 are expected
to appear later. Its owners are arm64 capability-finalization code and the
reviewed MT6797 profile owner.

The owner must derive, from the exact source and resolved configuration, every
compiled local capability that is false on the early A53 set and true on an A72
target. It must pre-account and fully enable that set before:

```text
setup_system_capabilities()
  -> update_cpu_capabilities(SCOPE_SYSTEM)
  -> enable_cpu_capabilities(...)
  -> apply_alternatives_all()

setup_user_features()
  -> setup_elf_hwcaps(...)
  -> elf_hwcap_fixup()
```

The current deterministic minimum is:

```text
ARM64_SPECTRE_BHB                with Cortex-A72 loop k=8
ARM64_WORKAROUND_1742098         with COMPAT_HWCAP2_AES removed
ARM64_WORKAROUND_SPECULATIVE_AT  selected by ERRATUM_1319367
```

Spectre-v2 and Spectre-v4 remain conditional on exact SMCCC results and are
treated conservatively until those results are pinned. Mismatched cache type,
ASID width, active VA mode, and page granule remain explicit proof rows rather
than implicit assumptions.

### Required implementation shape

A41 is not a late runtime override and not an untyped bit mask. A reviewed
implementation must provide:

1. an MT6797 profile predicate that is true only for the exact early-A53 plus
   late-A72 topology and resolved configuration;
2. a pre-finalization enumerator using the canonical arm64 capability entries,
   not duplicated numeric capability values;
3. each capability's normal enable/fixup behavior, including BHB loop/vector
   parameters and erratum-1742098 compat-HWCAP suppression;
4. assertions before and after system capability, alternative, and user-HWCAP
   finalization;
5. the same frozen set included in A36 and attested immediately before P17/P18;
6. a fail-closed result on any source, configuration, firmware, topology, or
   capability-set drift.

Raw post-finalization `set_bit()`, marking an erratum permitted for late CPUs,
disabling a mitigation, or changing Kconfig merely to avoid the verifier is
rejected. Disabling COMPAT and KVM would remove some side effects but would not
close BHB, Spectre-v2/v4, cache-type, ASID, VA-mode, or granule proof.

### Acceptance

A41 passes only when K01-K12 are closed, boot-time assertions establish the
complete frozen set before finalization, A36/P17/P18 carry its exact identity,
and late target verification contains no known conflict. Failure leaves A26's
boot veto in place and authorizes no build.

## P14/P15 publication point

The controller must publish the successful `__cpu_up()` handoff immediately
after `__cpu_up(cpu, idle)` returns zero in `bringup_cpu()`, before
`cpuhp_bp_sync_alive()`, `bringup_wait_for_ap_online()`, or later ONLINE
callbacks can fail. This is the point that proves the target published
SUCCESS, online, and completion for the exact generation. P32's source phase
cannot be guaranteed if P14/P15 is deferred until all later CPUHP work.

P30U's publication-winning branch drains and validates the exact completion,
then joins this P14/P15 point. It does not manufacture P30.

## P30: early-secondary failure closure

P30 is the membership contract's existing `ON_ISSUED -> FAULT` transition. It
accepts only an exact owner, operation, target, and generation. Membership
stays at entry. Provider state stays conservatively retained or becomes
`FAULT_UNKNOWN`. No branch permits an inverse, query, retry, provider release,
or membership commit.

### Shared arbitration state

The cancellation-versus-publication contract starts because the existing
global `secondary_data.task`, `secondary_data.status`,
`__early_cpu_boot_status`, and `cpu_running` completion cannot distinguish
attempts. The early-status cell is not reset before CPU_ON and is cleared only
after MMU enable; a target can also take the too-slow park path without a
unique shared reason. Status zero is therefore ambiguous. The closure requires
a generation-scoped startup object with atomically ordered states equivalent
to:

```text
PREPARED
  -> ABORTED       controller proved the boot method returned before CPU_ON
  -> ARMED         controller crossed the exact P24 CPU_ON-issue boundary
  -> FAULTED       controller lacks the proof required for a no-effect abort
ARMED
  -> PUBLISHING    target won one CAS before any SUCCESS/online/completion write
  -> CANCELLED     controller won timeout cancellation while still ARMED
  -> FAILING       target won an early K/C/P/E or STARTING-failure CAS
  -> FAULTED       controller received synchronous CPU_ON error or uncertainty
PUBLISHING
  -> PUBLISHED     target emitted the booted log, published SUCCESS and online,
                   then release-published this state and signalled the exact
                   completion
CANCELLED
  -> PARKED        target release-published the exact-generation final reason,
                   park commitment, and possible prepublication effect prefix
FAILING
  -> PARKED        target release-published the same terminal record
  -> PANICKED      controller published P30 and the stuck/kexec interlock,
                   then entered the unconditional panic branch
FAULTED
  -> PARKED        any late target acknowledged the terminal fault before
                   parking; controller recovery was already fail-stop
```

`PREPARED -> ABORTED` is controller-only startup-object cleanup and requires
proof that no CPU_ON was issued; it never uses timeout cancellation or PARKED
and creates no membership phase edge. The transaction owner still applies the
existing A26/P05/P16/P21 result as applicable. The selected patch-0092
`-EAGAIN` veto permits only this object cleanup while the A26 boot veto remains
closed. Missing no-effect proof uses `PREPARED -> FAULTED` and P16.
`PREPARED -> ARMED` occurs immediately before the first CPU_ON SMC, after which
no ordinary disarm is allowed. On a returned CPU_ON error or uncertainty, the
controller attempts `ARMED -> FAULTED`. A winning FAULTED transition globally
quarantines CPU-up and enters immediate P16 fail-stop; any late target must
observe FAULTED and publish PARKED without success. If PUBLISHING, FAILING, or
another terminal owner already won, the controller drains that exact owner to
PUBLISHED-plus-completion, PARKED, or PANICKED and still fails stop because the
synchronous return conflicts with target activity. It never overwrites the
winning state, claims the target absent, returns to runtime, or reuses state.

The target checks CANCELLED or FAULTED at the earliest safe C entry and parks
with the exact terminal record. Every K/C/P/E failure path must instead win
`ARMED -> FAILING` before its first reason, status, present-mask, or other
failure publication; P30E uses that same authoritative atomic state through
its MMU-off-visible representation. The no-fail STARTING range must likewise
latch any unexpected nonzero result and win FAILING after the range returns
but before publication; otherwise the upstream warning would be swallowed.
The success path uses the single `ARMED->PUBLISHING` CAS immediately before
the booted `pr_info()` and first success-status write, `CPU_BOOT_SUCCESS`; the
owned sequence is booted log, SUCCESS, online, PUBLISHED, and exact completion.
All earlier MM, RCU, GIC, cpuinfo, topology, STARTING, IPI, and NUMA effects
remain the prepublication prefix. Any failed target CAS must consume the
winning exact-generation state and may not continue its proposed failure or
success publication. A CANCELLED or
FAULTED winner therefore routes even the MMU-off path directly to the terminal
PARKED record. It performs no cancellable check between SUCCESS, online,
PUBLISHED, and the exact completion. The controller may cancel only ARMED. On
PUBLISHING or PUBLISHED, it boundedly waits for both acquire-observed PUBLISHED
and the exact completion, validates target identity and online state even if
`cpu_online(cpu)` was already true,
and joins P14/P15. A stalled publisher is global fail-stop. On CANCELLED,
FAILING, or FAULTED it boundedly waits for the applicable PARKED or PANICKED
terminal when runtime observation remains possible. Task, status,
early-status, and completion state cannot be cleared, reinitialized, or reused
until exact PUBLISHED-plus-completion consumption or PARKED.

### P30K: CPU_KILL_ME

Before `cpu_die_early()` clears the target present bit or publishes
`CPU_KILL_ME`, the target-side guard must win `ARMED -> FAILING`. A timeout
controller may instead have won CANCELLED first, in which case the target
records the failure reason and parks without publishing KILL_ME. After FAILING,
target and controller can race through `.cpu_die`; the raw KILL status is
provisional because a missing or returning callback refines the final branch
to P30C:

- the target guard release-publishes a park acknowledgment carrying the final
  branch, reason, and retained callback prefix, then parks without CPU_OFF;
- the controller `.cpu_kill` waits boundedly for that acknowledgment without
  an SMC, performs no affinity call, and returns nonzero;
- present-clear and any RCU-dead effects are retained in P30's exact terminal
  record for the later A39 reconciliation owner;
- the controller returns `-EIO` and recovery is P13/A34 reset only.

A zero kill return would falsely report clean death and is rejected.

### P30C: post-C bare STUCK

If `.cpu_die` is absent or unexpectedly returns, `cpu_die_early()` overwrites
`CPU_KILL_ME` with bare `CPU_STUCK_IN_KERNEL` after present was cleared, then
release-publishes the exact-generation PARKED record immediately before
parking. Bare STUCK alone is not an acknowledgment. The controller waits
boundedly for PARKED and retains every callback effect. A direct P30C performs
no kill or query; a K-to-C refinement records the bounded, non-SMC P30K guard
that may already be waiting. Missing or mismatched PARKED globally quarantines
CPU-up and fails stop. Present is never optimistically restored.

### P30P: CPU_PANIC_KERNEL

The controller publishes P30 and an exact-once stuck/kexec interlock before
preserving the kernel's unconditional `panic()`. Panic is not an excuse to
lose terminal attribution. This branch has no normal return and attributes no
present clear, CPU_OFF, or affinity.

### P30E: pre-C reasoned STUCK

The early assembly 52-bit-VA and unsupported-granule branches cannot access the
C ledger. P30E therefore uses the same authoritative arbitration object as the
controller: its `{target, generation, cookie, reason, atomic state}`
representation is MMU-off-visible, not a second ledger. Before CPU_ON the
controller writes the per-attempt sentinel and cookie with the required
point-of-coherency, cache, and barrier ordering. Assembly CASes the same state
from ARMED to FAILING, then release-publishes reason and PARKED with matching
ordering. If that CAS loses to controller CANCELLED or FAULTED, assembly
acquire-observes the winner, writes no reason or status, and release-publishes
exact-generation PARKED. A C-only generation label paired with the unchanged
scalar reason is insufficient. The controller acquire-validates the exact
tuple and authoritative state, publishes P30, retains stuck accounting,
performs no kill/query, and returns `-EIO`. An untagged, zero, stale, inherited,
or independently arbitrated cell routes to P30U uncertainty. The generation
remains quarantined through P13/A34.

### P30U: default/unknown timeout

Timeout does not prove that the target parked. The controller must win the
generation arbitration before it may publish P30:

- if PUBLISHING or PUBLISHED wins, it boundedly waits for acquire-observed
  PUBLISHED and the exact completion, verifies target identity and online
  state, and joins P14/P15 without contaminating stuck accounting;
- if CANCELLED or FAILING wins, the target release-publishes PARKED without
  SUCCESS, online, or completion, carrying the exact or conservative possible
  prefix of MM, RCU, GIC, cpuinfo, topology, STARTING, IPI, NUMA, and other
  prepublication effects already performed;
- without bounded PUBLISHED-plus-completion or PARKED, every later CPU-up is
  globally quarantined and the system fails stop through panic or platform
  reset.

Returning ordinary `-EIO`, clearing `secondary_data.task`, logging a raw
status, or incrementing `cpus_stuck_in_kernel` is insufficient without that
arbitration. Status logging and stuck/kexec accounting happen only after
CANCELLED plus PARKED wins; a publication winner never receives stuck effects.

## Selected post-CPU_ON callback inventory

STARTING callbacks execute before online publication with no-fail semantics;
the selected callbacks return zero. An unexpected nonzero is warned and
swallowed by the upstream range, so A25 must latch it into P30U's target-owned
FAILING-to-PARKED path before success publication. P32 is about the later ONLINE range.
The exact fixed groups, mandatory dynamic relative order, and conditional
insertion points are frozen in
[`results/post-cpu-on-callbacks.tsv`](results/post-cpu-on-callbacks.tsv).
Absolute `DYN+N` identities are deliberately not claimed: A25 still requires
a same-boot hotplug-state, module/probe, firmware, and boot-parameter capture
immediately before the first A72 attempt.

The set cannot be claimed non-failing:

- timer migration can return `-EINVAL` on a violated preparation invariant;
- kthreads can return `-ENOMEM` or `-EINVAL`;
- cacheinfo can return `-ENOENT`, `-ENOMEM`, OF, hierarchy, device, or sysfs
  errors;
- padata can return `-ENOMEM` on up or down and is multi-instance;
- io-wq always reserves a dynamic state and invokes zero-return callbacks for
  each live instance;
- CPU capacity and cpuinfo can fail on missing devices or sysfs operations;
- scheduler, block-MQ, workqueue, and other rollback callbacks contain failure
  or invariant paths;
- conditional arm pvtime and SDEI add more errors when firmware makes them
  register;
- an EFI/ITS state would be fallible and self-removing before pvtime, while a
  command-line mismatched-32-bit state can insert before cpuinfo.

Configuration or firmware drift therefore reopens the entire inventory.

## P32: automatic CPUHP rollback closure

P32 is the existing `VERIFYING -> FAULT` phase edge. It is published by the
controller at the `cpuhp_up_callbacks()` error point before
`cpuhp_reset_state()` and the outer reverse callback range. Guards must be
installed and attested at publication; they have not necessarily executed.

### P32A: rollback arm

The controller first records any nested `cpuhp_kick_ap()` rollback already
performed to `CPUHP_AP_ONLINE_IDLE`, publishes P32, and freezes the exact
completed/unwound callback prefix and CPUHP state. Outer rollback may then
continue only under the fail-stop guard contract.

### P32D: primary `.cpu_disable` guard

The first target CPU-ops boundary in normal teardown is `op_cpu_disable()`.
It first requires a valid `.cpu_die`, then calls optional `.cpu_disable`.
The exact P32 guard in `.cpu_disable` must acknowledge the token and return an
error before arm64 can:

```text
remove_cpu_topology()
numa_remove_cpu()
set_cpu_online(false)
ipi_teardown()
irq_migrate_all_off_this_cpu()
```

The guard is bounded and atomic because it runs on the target in stop-machine
context. It cannot acquire the transition mutex or sleep.

This may leave the CPU online after higher ONLINE callbacks were removed and
after CPUHP state was predecremented. Normal operation is prohibited. The only
accepted result is fail-stop panic/reset unless a separate reviewed core
interface prevents automatic rollback or proves a complete quarantine.

### P32F: `.cpu_die` and `.cpu_kill` defense

Early `cpu_die_early()` bypasses `.cpu_disable`, and ordinary rollback can
reach deeper paths if the primary guard is skipped or defeated. Therefore:

- target `.cpu_die` recognizes P32 after arm64 has published `DEAD`, publishes
  the exact park acknowledgment, and parks without CPU_OFF;
- controller `.cpu_kill` waits boundedly for that acknowledgment without SMC,
  performs no affinity call, and returns nonzero;
- `DEAD` alone is not a guard acknowledgment or physical-off proof.

### P32X: partial or skipped cleanup

Rollback callbacks can fail before `.cpu_disable`; missing `.cpu_die` can
reject teardown; DEAD synchronization can time out; and guards can be skipped.
P32 must retain the exact executed prefix, including as applicable:

- nested AP rollback and every fixed/dynamic or multi-instance callback;
- CPUHP state predecrements and rollback warnings;
- topology and NUMA removal;
- online/present masks;
- IPI teardown and IRQ migration;
- DYING callbacks, RCU, lockdep, and DEAD publication;
- target park and controller kill observations.

No generic return alone can prove cleanup success, and no branch may infer a
clean rollback from that return value.

### P32R: outer result and side channel

CPU-up returns its original startup callback error. Cleanup failures are warned
and swallowed. In the separate off path a swallowed kill failure can even
coexist with generic success. The transaction owner must consume an
exact-generation P32 side channel before any P10, HPS success accounting,
provider release, reconciliation, or retry.

P32 is reset-only through P13/A34. It is never retained-up success.

## A25 completion requirement

A25 must prove the exact same-boot selected and conditional numeric
registration order plus all nested rollback behavior. Its implementation
review must cover no-fail warning paths, partial multi-instance effects,
conditional insertion and self-removal, teardown callback failure,
`.cpu_disable` rejection, DEAD synchronization timeout, kill warning, and
generic continuation. The callback table in this experiment is the current
source inventory; it is not a claim that future configurations share it.

## Rejected alternatives

- Repeating a boot2 cycle cannot close a source race or capability-finalization
  gap.
- Removing only the three deterministic Kconfig options does not close the
  conditional or architectural inventory and can remove required mitigations.
- Setting capability bits after finalization misses alternatives, parameters,
  mitigation state, and user-HWCAP fixups.
- Marking the errata permitted for late CPUs reverses arm64's safety rule.
- Treating timeout as parked allows late online/completion and stale reuse.
- A target-only CPU_KILL_ME owner loses the controller race.
- Die/kill-only P32 guards act after topology and online state may already have
  changed; `.cpu_disable` is the primary boundary.
- A `.cpu_disable` rejection alone does not restore higher callbacks and cannot
  return to normal runtime.
- Generic CPU-up failure does not describe cleanup success.
- `DEAD`, kill return zero, or an affinity result is not independent proof of a
  safe retained A72 state.

## Authorization boundary

```text
implementation_authorized=no
cpu_on_authorized=no
cpu_off_authorized=no
build_authorized=no
device_action_authorized=no
device_action=none
current_cpu_boot_veto=REQUIRED
```

Only a later reviewed source implementation that passes A41, P30, P32, A25,
and every other applicable A26 row can change this boundary.
