# A72 membership and admission design

> **Current mechanism notice:** Detailed A37/A39/P30/P32 mechanics retained in
> this file are historical. The later
> [A72 CPU-up source closure](../2026-08-05-a72-cpu-up-source-closure/DESIGN.md)
> supersedes those implementation details while preserving this design's
> phase, membership/provider, admission, one-shot, and reset-only ownership.

## Separate ledgers and identities

`members` is a Linux-owned two-bit A72 ledger:

- bit 0 represents logical CPU8;
- bit 1 represents logical CPU9.

Firmware-private `big_on` is not an alias, mirror, cache, or readback for
`members`. The retained payload uses `big_on` to choose and replay-gate secure
hardware teardown. Linux has no owner-safe reader for it. Source attribution
may state the private transition expected for a named branch, but only the
Linux state machine can commit `members` after independent Linux-owned proof.

The provider ledger is separate again. `HELD` carries one durable consumer
reference identity and the exact M01 acquire generation that created it. M02
and M03 use fresh transaction generations, so they sample that persistent
identity in their own generation rather than claiming to reacquire it. M04
must release that exact identity. A physical rail-enabled observation or an
unrelated stale vote cannot satisfy the provider proof.

## Transaction entry, token, and locks

One sleepable `a72_transition_lock` serializes A72 transactions. A short
`a72_state_lock` protects only scalar phase, `members`, provider state and
identity, and the exact boot-local token. The token contains owner, operation,
logical target, validated `cpu_logical_map()` MPIDR, requested CPUHP target,
generation, public preflight attestations, and operation-specific one-shot
budgets. CPU8-up and last-CPU8-off share a logical target but may never satisfy
each other's gate.

Before any P01-P04 token allocation, P31 atomically consumes the exact
operation's A38 boot-local attempt under the transition owner and short state
lock. CPU8-up has one minimal preconsume requirement: its owner-safe observer
capture window must already be open. That read-only attestation precedes P31;
all other CPU8 predecessor state and all CPU9 parent state follow P31. A28 then
checks only the generic membership, provider, CPUHP/online, present/possible,
and non-aliased mapping invariant. A failed A28 remains `IDLE`, allocates no
generation or token, and leaves that operation consumed until A34. If A28
passes, P01-P04 allocates the matching token and enters `FROZEN`. For an up
operation, A36 then checks remaining same-generation operation-specific
predecessor state before P17/P18; failure follows P05/P06 and cannot rearm.
The transition owner serializes the generic CPUHP snapshot as follows:

```text
a72_transition_lock
  -> temporary cpu_add_remove_lock / canonical CPUHP read serialization
    -> short a72_state_lock
```

Under the same transition ownership, P31 releases the leaf after attempt
consumption. A28 obtains temporary CPUHP read serialization, takes only a short
leaf snapshot of scalar ledger/token and generic CPUHP state, validates the
generic tuple, and allocates the token on success. It releases the leaf and
temporary read serialization but retains `a72_transition_lock`; the temporary
generic lock is not held when public `cpu_up()` or `cpu_down()` reacquires it.
A36 operation-specific register observations happen after token allocation and
without the leaf held. The leaf lock is never held across a notifier, PSCI/SMC,
callback, regulator call, register readback, delay, wait, or sleepable lock
acquisition.

The only entry tuples are `0x0` with both A72 CPUs offline, `0x1` with CPU8
online and CPU9 offline, and `0x3` with both online. `0x2` is forbidden. Up
transactions use exact `CPUHP_ONLINE`; down transactions use exact
`CPUHP_OFFLINE`. Every intermediate CPUHP target is denied.

P01-P04 require the immediately preceding same-request P31 attestation and do
not consume the A38 bit again. They initialize all call budgets, including
explicit `none` values. CPU8-up has one preparation attempt, one
provider-acquire attempt, and one CPU_ON attempt. CPU9-up has one CPU_ON
attempt. Each off transaction has one level-0 affinity attempt;
last-CPU8-off also has one provider-release attempt. A budget is consumed
atomically before its synchronous call and is never restored. P05/P06/P11 do
not rearm the operation; only A34 after a known-good platform or external reset
reinitializes the four A38 bits.

## Phases and terminal semantics

The phases are:

- `IDLE`: no live token;
- `FROZEN`: exact admission and policy state is frozen;
- `ON_ISSUED`: an up transaction is published before provider or CPU_ON work;
- `OFF_COMMITTED`: target `.cpu_die` committed to CPU_OFF and published that
  commitment immediately before entering the CPU_OFF SMC;
- `QUERY_INFLIGHT`: the one affinity budget was consumed before entering the
  synchronous query;
- `OFF_PROVEN`: that exact query returned OFF;
- `VERIFYING`: independent same-generation proofs are being collected;
- `REJECTED`: a strictly no-effect condition failed;
- `FAULT`: returned failure or owned uncertainty is terminal at runtime;
- `CONSUMED`: the generation committed or recorded a clean rejection and
  cannot be reused.

P05 is strictly a no-effect edge. It is allowed only when no CPUHP, provider,
or hardware effect occurred. A down-path failure after any executed or
uncertain teardown effect takes P23 to `FAULT`, even if a rollback appears to
have completed. The rejection and success consume edges release the
transaction-owned freeze exactly once; `CONSUMED -> IDLE` is scalar cleanup
only.

P17 publishes CPU8 `ON_ISSUED` while provider state is exactly `NONE` and
before the first mutation. P27 consumes the one preparation attempt, releases
SPM reset, performs the B-PLL ordering read, and asserts PWRAP before R01. R01
then publishes `ACQUIRE_INFLIGHT` and consumes the one acquire attempt before
the synchronous regulator call. After R02, P28 performs the ordered isolation,
PWRAP, SRAM-LDO, selector, and calibration preparation before P24. The only
narrow `ON_ISSUED -> REJECTED` exception is P21 after R03 proves no vote or rail
mutation and P29 proves exact restoration of all attempt-owned P27 effects with
no residual state. Every missing or ambiguous proof uses P16 `FAULT`.

P18 publishes CPU9 `ON_ISSUED` with the durable M01 reference unchanged. P24
consumes the one CPU_ON attempt before calling the two-argument kernel API
`psci_ops.cpu_on(exact_mpidr, __pa_symbol(secondary_entry))`. CPU8's validated
MPIDR is `0x200`; CPU9's is `0x201`. P14/P15 require the same
logical-CPU/MPIDR/generation at secondary completion.

A synchronous call cannot execute a failure edge if it never returns. A
nonreturning provider acquire remains `ACQUIRE_INFLIGHT`; a nonreturning
provider release remains `RELEASE_INFLIGHT`; a nonreturning CPU_ON remains
`ON_ISSUED` with its attempt consumed; and a nonreturning affinity call remains
`QUERY_INFLIGHT`. Those exact inflight states prohibit retry and every runtime
action until a known-good platform or external reset. Returned uncertainty
uses P16/P12 and provider `FAULT_UNKNOWN` as applicable.

P32 owns the guarded A37 rollback terminal edge. Once generic rollback has
begun from `VERIFYING`, a reviewed target `.cpu_die` up-token guard prevents
CPU_OFF and a separate controller `.cpu_kill` up-token-fault guard prevents
affinity. P32 enters `FAULT`, retains membership/provider conservatively,
allows `cpu_online_mask` to diverge under A30, and permits no inverse, query,
retry, or commit before platform/external reset.

P13 may discard any live or terminal generation, or recover `IDLE` with no
token and a consumed P31 attempt, only after a known-good platform or external
reset and A34 bootstrap. Ordinary Linux reboot is not assumed reachable:
unowned shutdown CPU-down is denied and may hit generic multi-CPU shutdown
assertions. A34 currently permits only the exact zero tuple: CPU8/CPU9 offline
with matching CPUHP/online masks, both targets restored present and possible,
owner-validated non-aliased mappings exactly `0x200`/`0x201`, `members=0x0`,
provider `NONE` with no durable identity, and owner-safe private replay state
zero. It then atomically restores all four operation attempts. Any topology or
mapping mismatch remains terminal. Bootstrap to `0x1` or `0x3` requires a
separate reviewed provider-origin model and is not authorized. `0x2` always
remains terminal. The reset and bootstrap owners are unresolved blockers.

## Membership commits

The only permitted sequence is:

```text
0x0 --CPU8 up--> 0x1 --CPU9 up--> 0x3
0x3 --CPU9 off--> 0x1 --CPU8 last off--> 0x0
```

Every callback, readback, MPIDR, provider observation, and CPUHP result must be
bound to the exact live transaction generation. A33 waits through every
relevant callback, generic result, and rollback window, then attests the exact
requested CPUHP state and `cpu_online_mask` before P10. Generic zero return or
a stale/cached result cannot commit membership.

1. M01 (`0x0 -> 0x1`) requires the exact 2026-08-02 one-way CPU8 prestate and
   ownership gates and executed P27/P28 order for SPM `0x218`/`0x290`, BUCKB
   page/VSEL, PWRAP, isolation, SRAM selector/calibration, and post-completion
   DCM; MPIDR `0x200`; the exact
   physical `secondary_entry`; returned CPU_ON and same-MPIDR secondary/callback
   completion; same-generation resource readbacks; a new durable provider
   identity; and final CPU8-online/CPU9-offline CPUHP state. The predecessor's
   old up-path affinity reconciliation is superseded and is not carried
   forward: M01 permits no affinity call.
2. M02 (`0x1 -> 0x3`) requires the exact 2026-08-03 CPU9 cluster-reuse prestate,
   CPU8 cluster/DCM publication, empty shared-write set, MPIDR `0x201`, exact
   physical `secondary_entry`, same-MPIDR secondary/callback completion, and
   P15's CPU_ON return and same-MPIDR secondary completion, then full accepted
   generic callbacks, both CPUs online, and inherited cluster/DCM publication.
   Only afterward may the static work follow this exact order: initial schedule,
   sample 1 at approximately 1 second, reschedule 1, sample 2 at approximately
   6 seconds, reschedule 2, then sample 3 at approximately 10 seconds. In every
   sample both CPUs are online, the exact CPU8 and CPU9 callback/IPI identities
   are unchanged, and their cumulative callback hit counts are equal. P10
   cannot run before sample 3 and every remaining M02 proof. Any post-full-
   bringup callback/IPI, identity, online-accounting, hit-count,
   shared-resource, provider, A33-final, scheduling, or rescheduling failure
   takes P19 to `FAULT`, retaining `members=0x1` and the durable provider
   reference with no inverse/retry and reset-only recovery. M02 also requires
   independent CPU8 shared-resource proof, an unchanged M01 provider identity
   sampled in this generation, final both-online CPUHP state, and no affinity
   call.
3. M03 (`0x3 -> 0x1`) requires same-generation safe-off C02 entry snapshot,
   owner-safe private `big_on=0x3` before public CPU-down or any callback, one
   level-0 query to the validated CPU9 MPIDR, returned OFF, an independent CPU9
   `PWR_CON` and power-ack OFF readback, CPU8 callback, exact safe-off C07
   resource/provider invariance, unchanged durable provider identity, and final
   CPU8-online/CPU9-offline CPUHP state. Post-query per-core proof cannot
   substitute for the pre-query private branch gate.
4. M04 (`0x1 -> 0x0`) requires same-generation safe-off L02 entry snapshot,
   owner-safe private `big_on=0x1` before public CPU-down or any callback, one
   level-0 query to the validated CPU8 MPIDR, returned OFF, exact L06-L12
   per-core/cluster/CCI/SPM/iDVFS/DCM/SRAM/sentinel proofs, L13 release of the
   exact durable provider identity, and final both-offline CPUHP state.

The exact safe-off C/L rows are normative gates, not summaries. There is still
no CPU9-off runtime evidence. The owner-safe private entry reader, CPU9
per-core power acknowledgment, and separate DCM, SRAM, iDVFS, sentinel, and
provider readback owners remain unresolved.

## Provider reference state

The provider states are exactly `NONE`, `ACQUIRE_INFLIGHT`, `HELD`,
`RELEASE_INFLIGHT`, and `FAULT_UNKNOWN`. They model a real regulator consumer
vote, not physical rail level.

CPU8-up is the only acquire path. R01 can begin only after P17 publication;
R02 establishes the durable reference identity. R03/P21 is the narrow clean
refusal path. CPU9-up and CPU9-off prove that same durable identity remains
held across their distinct transaction generations.

Last-CPU8-off may enter R05 `RELEASE_INFLIGHT` only after same-generation
safe-off L06-L12 all pass, including iDVFS, DCM, SRAM, and sentinel proofs. R05
publishes the inflight state and consumes its one release attempt before the
synchronous call. R06 must prove release of the exact durable identity before
M04. Nonreturn remains inflight and reset-only; a returned ambiguous result
enters `FAULT_UNKNOWN` and transaction `FAULT`.

`regulator_is_enabled()` may describe hardware output but cannot identify
which consumer owns a vote. It is never provider-reference evidence.

## Admission, callbacks, and topology

Canonical Linux 7.1.3 admission is symmetric and fail-closed:

1. Public `cpu_up()` checks exact `CPUHP_ONLINE`, operation, logical target,
   MPIDR, generation, A36 up prestate/call shape, and provider state at function
   entry before `cpu_possible()`, `try_online_node()`, or
   `cpu_maps_update_begin()`. It publishes a short public preflight for A23.
   The `add_cpu()` device-online wrapper reaches this same gate.
2. Early `_cpu_up()` repeats the exact check and public attestation before
   `cpus_write_lock()`, `cpuhp_set_state()`, and every startup callback.
3. Before public `cpu_down()`, P26 must attest the exact same-generation
   C02/L02 entry snapshot and private branch gate. Public admission then checks
   exact `CPUHP_OFFLINE`, operation, target, generation, and P26 before
   `cpu_maps_update_begin()`. The `remove_cpu()` device-offline wrapper reaches
   this same gate and does not mutate topology.
4. Early `_cpu_down()` repeats exact `CPUHP_OFFLINE`, token, and P26 checks
   before `cpus_write_lock()`, state changes, or callbacks.

Both internal gates require `tasks_frozen=0`. Direct thaw `_cpu_up(..., 1)`,
SMT/internal unattested up, direct suspend `_cpu_down(..., 1)`, shutdown, and
every unowned internal path are denied with a leaf snapshot and never acquire
the transition mutex while a generic outer lock may be held.

A25 inventories every startup callback and rollback branch; A08 inventories
teardown callbacks on both sides of `CPUHP_TEARDOWN_CPU`. Auxiliary callbacks
are non-reentrant validators under A21. They cannot acquire the transition
mutex, allocate/reuse a token, call CPU hotplug, invoke affinity, or modify a
ledger.

Before generic startup rollback, `secondary_start_kernel()` calls
`check_local_cpu_capabilities()`. A selected mismatch can call
`cpu_die_early()`, which bypasses `cpu_can_disable` and optional `cpu_disable`,
clears the target present bit, reports RCU death, publishes `CPU_KILL_ME`, and
directly invokes the target method's `cpu_die`; controller `__cpu_up()` then
calls `cpu_kill`. P30/A39 require two distinct guards: target custom `.cpu_die`
must detect the live up token, CAS terminal P30, and park without CPU_OFF, and
controller custom `.cpu_kill` must detect that up-token fault and return
without affinity. `CPU_PANIC_KERNEL` parks the target before the controller
panics; pre-C `CPU_STUCK_IN_KERNEL` covers 52-bit-VA or unsupported-page-granule
cases; unknown/default timeout is separate again. Each status needs proof that
it is impossible for the exact profile or a reviewed branch-specific core
change. None is generic A37 rollback, and the present-mask divergence is owned
by P30 rather than A30.

Linux 7.1.3 with `HOTPLUG_CPU` also permits later startup rollback. A
post-CPU_ON `cpuhp_up_callbacks()` failure can run teardown through
`takedown_cpu`, `cpu_die`, CPU_OFF, and `cpu_kill` under an up token without
A01/A02 admission. A37 therefore blocks implementation until every selected
post-CPU_ON failure path is proven non-failing with fallible validation after
full bringup, a reviewed core/A72 interface prevents automatic teardown and
propagates the failure, or reviewed MT6797 target `cpu_die` and controller
`cpu_kill` up-token guards suppress CPU_OFF and affinity. That third closure is
intentionally not success: generic rollback may still clear
`cpu_online_mask`, so P32/A30 records terminal divergence with conservative
membership/provider state and platform/external-reset-only recovery. P16/P19
may not pretend that an already-started generic auto-rollback retained the
up-path hardware state.

External physical topology mutation has no operation in this model. In the
selected profile, arm64 does not select `CONFIG_ARCH_CPU_PROBE_RELEASE`, ACPI
is disabled in both project fragments, and arm64 ACPI rejects external present
state changes. A35 fails closed if a future configuration enables external
probe/release or present/possible mutation; a distinct reviewed topology state
machine would be required. This external rule does not claim that internal
present state is immutable: P30/A39 own the selected `cpu_die_early()` clear.

The suspend interlock vetoes suspend whenever a token is live, `members != 0`,
provider state is not `NONE`, phase is terminal/inflight, or suspend is already
active. In the separate Gemian compatibility lane the veto priority is
strictly above the vendor priority-zero notifier. Complete notifier inventory
and exact active Gemian revision remain blockers.

Patch 0092's CPU-up `cpu_boot=-EAGAIN` veto and CPU-disable veto both remain.
A22-A25 alone cannot relax boot: every applicable phase, membership, provider,
admission, and lock row in this frozen contract must be implemented and proven,
including P31/A38 one-shot, budgets, provider, predecessor prestate,
call-shape, P30/A39 early status, A37/P32 rollback, proof, final-state, and
reset. The off method has the same all-applicable-row requirement, including
P31/A38, A18 suspend, A28 entry, A34 reset, A40 freshness, and the full
`cpu_can_disable`, optional `cpu_disable`/resident-TOS, `cpu_die`, and
`cpu_kill` inventory. No enumerated subset and no die/kill-only implementation
relaxes either veto.

## HPS, CPUHVFS, and lock compatibility

Canonical Linux 7.1.3 is the implementation target; vendor HPS and CPUHVFS are
not imported. The separate public-equivalent Gemian compatibility order is:

```text
hps_ctxt.lock
  -> a72_transition_lock
    -> cpu_add_remove_lock
      -> cpu_hotplug.lock
        -> cpufreq_mutex
          -> dvfs_lock
```

`hps_ctxt.para_lock` is a short sibling below the first two locks and is
released before public hotplug. Canonical up and down paths instead use:

```text
a72_transition_lock
  -> cpu_add_remove_lock
    -> cpu_hotplug_lock (through cpus_write_lock)
```

The Gemian HPS path already holds `hps_ctxt.lock` and must not reacquire it.
HPS accounting changes only after the same-generation M01-M04 commit, never
from generic return alone. CPUHVFS recognition occurs before `cpufreq_mutex`;
every A72 action including `CPU_DOWN_FAILED` is a no-op for cluster, B/CCI,
ARMPLL, PBM, frequency/index, and power writes. These are compatibility
constraints, not vendor-import authorization.

## OFF handoff and active affinity

Arm64 reports `DEAD` immediately before entering `cpu_operations::cpu_die`.
The controller can reach `cpu_kill` before target `.cpu_die` publishes its next
state. `DEAD` is not CPU_OFF, WFI, or physical-off proof.

A27 defines the missing target/controller handoff. Target `.cpu_die` must CAS
P07 `FROZEN -> OFF_COMMITTED` immediately before the CPU_OFF SMC. The
controller performs a bounded non-SMC wait for that exact publication; timeout
CASes P23 `FAULT`, and a target that loses its P07 CAS must not call CPU_OFF.
`OFF_COMMITTED` is an honest commitment, not proof that the target entered or
completed the SMC.

The controller could still query after `OFF_COMMITTED` but before target SMC
entry. The secure audit proves a WFI poll, not concurrent secure-call lock or
deadlock safety. A29 therefore blocks P20 until either exact firmware
concurrency/lock safety is reviewed or an owner-safe CPU_OFF-entry/WFI
discriminator exists.

After A29 and the exact private branch proof pass, A40 must prove that the
branch value remains fresh. One acceptable path inventories every private
`big_on` writer and caller and excludes every other CPU_ON, CPU_OFF,
`AFFINITY_INFO`, and private-ledger writer under the transition/policy freeze
continuously from A31/P26 through P20. The alternative is an owner-safe,
writer-serialized exact-branch revalidation immediately before P20 through a
non-SMC reader or after an independent A29-equivalent concurrent-SMC
lock/deadlock proof. C02/L02 policy-writer drain alone is insufficient. P20
then atomically consumes the one query budget and publishes `QUERY_INFLIGHT`
before releasing the leaf lock and entering `AFFINITY_INFO`. The call is
exactly level 0 and uses the same-transaction owner-validated
`cpu_logical_map(target)` MPIDR. Aliased, different-MPIDR, other-level,
retained, already-off, and non-target queries are forbidden. CPU9-off requires
fresh private `big_on=0x3`; last-CPU8-off requires fresh `big_on=0x1`. No
post-query observation can replace that branch-selection proof.

A returned OFF advances P08 to `OFF_PROVEN` without issuing another query. A
returned non-OFF/error enters P12 `FAULT`. A nonreturn stays
`QUERY_INFLIGHT`, consumes the sole budget, and requires platform/external
reset. An unexpected target CPU_OFF return races through P25 to `FAULT` and
cannot be overridden by P08.

Generic PSCI `cpu_kill` is unusable: its nominal 100-ms jiffies interval does
not bound the first synchronous secure call and it repeats active affinity
after returned non-OFF values. Disabling `HOTPLUG_CORE_SYNC_DEAD` is also not a
fix because it skips deferred cleanup/kill.

The enabled generic path can swallow both `cpuhp_bp_sync_dead()` and
`cpu_kill()` failures. Void arch cleanup may let generic CPUHP clear
`cpu_online_mask` and return success while `members` and provider state stay
conservative/FAULT. A30 classifies that as terminal divergence with no
rollback. A custom `cpu_kill` alone cannot stop generic publication; a core
interface/propagation change or reviewed outer completion sidechannel consumed
before transaction/HPS success is required.

## Source-closure correction (2026-08-05)

The later
[`A72 CPU-up source closure`](../2026-08-05-a72-cpu-up-source-closure/DESIGN.md)
supersedes this design's detailed A37/A39 implementation mechanism while
preserving P30 and P32 as the only phase edges.

Its A41 prerequisite requires complete late-A72 capability pre-accounting
before arm64 alternatives and user-HWCAP finalization. P30K/C/P/E/U add exact
generation cancellation/publication arbitration, shared-completion protection,
target park acknowledgment, and the post-C bare-STUCK branch. P32A/D/F/X/R
requires controller publication before rollback and makes target
`.cpu_disable` the first guard before topology/NUMA, online, IPI, or IRQ
teardown. Target `.cpu_die` and controller `.cpu_kill` remain mandatory defense
for `cpu_die_early()` and deeper rollback. P14/P15 publication moves to the
controller point immediately after `__cpu_up()==0`.

Use the linked source-closure design for implementation and mutation review.
The phase, membership/provider, admission, and reset-only ownership frozen here
remain normative.

## Authorization boundary

This design defines invariants for later review. It contains no kernel patch,
does not weaken the current CPU boot or disable vetoes, and grants no build or
device authorization. A future implementation must satisfy the validator,
close the exact unresolved source, provider, private-ledger, startup rollback,
secure concurrency, CPUHP propagation, observer, and reset/bootstrap owners,
and receive a new experiment decision before any CPU_ON/CPU_OFF candidate.

These markers are normative:

```text
implementation_authorized=no
cpu_off_authorized=no
build_authorized=no
device_action_authorized=no
device_action=none
```
