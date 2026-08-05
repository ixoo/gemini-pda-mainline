# Experiment: A72 membership and admission contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-membership-admission-contract` |
| Status | `completed-blocking-contract`: the source-only contract is frozen; implementation remains blocked |
| Subsystem | MT6797 Cortex-A72 membership, provider reference, CPU-hotplug admission, notifier, and terminal-failure ownership |
| Device variant | Named Gemini PDA development unit; no live-device action |
| Date(s) | 2026-08-05 UTC (2026-08-04 America/New_York) |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4 |

> **Current mechanism notice:** The detailed A37/A39/P30/P32 mechanics below
> are retained as historical chronology. The later
> [A72 CPU-up source closure](../2026-08-05-a72-cpu-up-source-closure/README.md)
> is the current design authority for implementation review of A41 and the
> P30/P32 mechanism;
> use its P30K/C/P/E/U, P32A/D/F/X/R, primary `.cpu_disable`, and moved P14/P15
> contracts before implementation review.

## Question or hypothesis

Can Linux-side A72 membership, provider-reference ownership, admission, and
failure handling be specified precisely enough to constrain a later
implementation without treating firmware-private `big_on` as Linux state or
authorizing CPU_OFF?

The contract must freeze the exact `members=0x0 -> 0x1 -> 0x3 -> 0x1 -> 0x0`
commit points, bind that ledger to exact CPU8/CPU9 CPUHP/online state at every
transaction entry, dominate public and internal CPU-up and CPU-down paths,
deny unowned frozen-task bypasses in both directions, preserve the
source-lane-specific HPS/cpufreq/hotplug lock orders, permit only one active
`AFFINITY_INFO` call for the exact off target, and require same-generation
callback, register, provider, and per-core teardown evidence before any
membership commit.

## Provenance and environment

This contract pins the following committed source-attribution and safe-off
records:

- Secure callgraph SHA-256:
  `0007ba7868cbd68bb2a4ef6ad66240c7e00715e08934ca5d05ca482dfd464354`.
- Secure effect inventory SHA-256:
  `deaa6686582e6e3f2e3453ff626f14b2ec555d9be468ac2f67fb350e6eead8bc`.
- Secure validation transcript SHA-256:
  `6da8ad1883362b32fe7b8e2332f262ec8ebf195db09c91872a0ce59eda429af6`.
- Safe-off contract SHA-256:
  `8451fbc2910a0d4776efe2d51b84f0bcb3e95ac77310ff425c506bbb59d6af26`.
- Safe-off reconciliation SHA-256:
  `6ee968f2f1286393d9552c23caf3ed0e9aef2647d07029b1651eebffdea5b046`.
- Safe-off validation transcript SHA-256:
  `19a2674623722e54b0bb0599a2acd6504c0eca0e88b0fcc5dfe570352d34eb48`.
- Public CPU-down source-order audit SHA-256:
  `ce530fb74fe520d1899f94f64a2c4e2a0029699cb6dd91f7eaccb6d5f5e01a34`.
- Pinned manifest SHA-256:
  `ea55ec7dd39ef96ed0d69f008405a8f5776bd3afe599ab4da9ea688d4c83687a`.
  It selects Linux 7.1.3 from
  `https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.1.3.tar.xz` with source
  SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Canonical patch 0092 SHA-256:
  `cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5`.
- Canonical patch 0091 SHA-256:
  `ed46e44a7ba42a7084ab5fba59168f3d51fcfed40f50dee363e1d8f43e619e98`.
- Canonical/source-lane order audit SHA-256:
  `2344676ee4fc5b889eba4d40aad1a00e1c5266935ee9a887ad8624b763f1077d`.
- CPU8 one-way predecessor design SHA-256:
  `257217f6ea0d513162e2888259ee8a4a6b76a614ee8d3b2bb43f5b841a67321a`.
- CPU9 cluster-reuse predecessor design SHA-256:
  `9c75776937c4045dd4774546ec1985068eaf6c672f88f740757a146aeec45717`.
- Selected `configs/gemini.fragment` SHA-256:
  `aa2a138abe1449bc5204099af349d271c5eb5337d2d932a8d02ea02f0a0ee8b8`.
- Selected `configs/gemini-handoff.fragment` SHA-256:
  `cb786eb244637af11858cb0ca31c138be32bf0104582ec589fc0eb2d50933f5e`.

Two source lanes remain explicit. The implementation target is canonical Linux
7.1.3, including its `cpu_up`/`_cpu_up`, `cpu_down`/`remove_cpu`, direct frozen
up/down callers, startup and teardown CPUHP callbacks, arm64 hotplug, and PSCI
source. The public-equivalent source-order audit is pinned separately to Gemian
3.18 commit
`59e00a9144d782e148332009a835b99c43382467`; its HPS, CPUHVFS, and priority-zero
PM notifier are compatibility/evidence constraints, not code to import into
mainline. The exact active Gemian source revision remains unresolved. No kernel
was built. Neither Buildbox nor the native VM build backend was invoked.

## Safety assessment

This experiment is offline and read-only. It reads committed text only. It
does not contact the device, invoke an SMC, change a CPU mask, request CPU
hotplug, read or write a partition, build a kernel, package an image, deploy,
reboot, or shut down hardware.

These markers are normative:

```text
implementation_authorized=no
cpu_off_authorized=no
build_authorized=no
device_action_authorized=no
device_action=none
```

The validator rejects any attempt to merge Linux `members` with private
`big_on`, begin from a mismatched Linux CPU state, admit an unattested public or
internal up/down caller, admit a frozen-task bypass, move admission after
CPUHP work, query a retained or non-target CPU, repeat the target query,
conflate operation tokens, use `regulator_is_enabled()` as a reference oracle,
reuse stale-generation proof, commit CPU9 removal without a per-core/private
entry discriminator, issue an affinity query without the secure concurrency
gate, retry a consumed synchronous call, or clear terminal state without a
known-good platform or external reset.

## Associated code

- [`DESIGN.md`](DESIGN.md): ownership, state, admission, and lock design.
- [`results/phase-contract.tsv`](results/phase-contract.tsv): canonical
  transaction phase transitions.
- [`results/membership-contract.tsv`](results/membership-contract.tsv):
  canonical Linux membership commit points.
- [`results/provider-contract.tsv`](results/provider-contract.tsv): canonical
  provider-reference states and transitions.
- [`results/admission-lock-contract.tsv`](results/admission-lock-contract.tsv):
  public/internal admission, suspend, HPS, notifier, query, and lock rules.
- [`results/source-order-audit-20260805.txt`](results/source-order-audit-20260805.txt):
  pinned Linux 7.1.3 and separate public-equivalent Gemian source audit.
- [`scripts/validate_contract.py`](scripts/validate_contract.py): schema,
  row-identity, evidence, ordering, ownership, prose-safety, authorization, and
  exact-transcript validator.
- [`scripts/test_contract.py`](scripts/test_contract.py): adversarial mutation
  suite.
- [`results/contract-validation-20260805.txt`](results/contract-validation-20260805.txt):
  frozen validation transcript.

Run from the repository root:

```sh
python3 experiments/2026-08-05-a72-membership-admission-contract/scripts/validate_contract.py
python3 experiments/2026-08-05-a72-membership-admission-contract/scripts/test_contract.py
```

## Procedure

1. Pin the exact secure callgraph/effect inventory, reconciled safe-off
   contract, and public CPU-down source-order evidence.
2. Define four boot-local operation-attempt bits. P31 consumes the requested
   bit before A28's generic state/mapping checks. Only a passing A28 allocates
   the P01-P04 transaction token; an up token then carries the same generation
   into A36's operation-specific predecessor checks before P17/P18.
3. Define all phase edges, including `ON_ISSUED`, target-published
   `OFF_COMMITTED`, pre-call `QUERY_INFLIGHT`, single freeze release,
   post-mutation fault, consumed call budgets, and platform/external-reset-only
   recovery.
4. Define the four Linux membership commits and the independent proof required
   before each commit.
5. Define provider reference acquisition/release as explicit consumer-vote
   states, independent from rail-enabled observation.
6. Require symmetric admission at public `cpu_up()`/`cpu_down()` and early
   `_cpu_up()`/`_cpu_down()`, deny unowned internal callers, and deny both
   frozen-task paths when `tasks_frozen=1`.
7. Freeze complete startup and teardown callback inventories, HPS,
   CPUHVFS/cpufreq notifier, PM notifier, target/query handoff, and lock
   ordering rules.
8. Validate the README and design safety claims, then require the frozen
   transcript to equal the live validation report plus the fixed mutation
   summary exactly.
9. Run the validator and negative-mutation tests. PASS freezes a source-only
   blocking contract; it does not authorize implementation or hardware work.

## Observations

- The Linux membership ledger and firmware-private `big_on` have different
  owners and different observation boundaries. Static firmware expectations
  cannot update Linux membership.
- P31 consumes the exact operation's boot-local attempt before A28 checks any
  generic state. A mismatch remains `IDLE`, allocates no token, and leaves that
  operation consumed. A28 then binds a passing entry to exact membership,
  provider, CPU8/CPU9 CPUHP/online state, target present/possible state, and
  owner-validated non-aliased MPIDR before P01-P04 allocates the token and
  freezes admission. For up, A36 then checks the remaining same-generation
  operation-specific predecessor state before P17/P18; failure uses P05/P06
  and does not rearm. CPU8-up has one asymmetric prerequisite: its owner-safe
  observer capture window must already be open before P31 consumption. No
  other CPU8 predecessor state, and no CPU9 parent state, is checked first.
  `0x2` is forbidden.
- The only allowed membership sequence is `0x0 -> 0x1 -> 0x3 -> 0x1 -> 0x0`.
  Each edge waits for same-generation callbacks, readbacks, provider identity,
  the final requested CPUHP state, `cpu_online_mask`, and the complete rollback
  window. A generic hotplug return is never enough.
- CPU-up admission is fail-closed at public `cpu_up()` before
  `cpu_possible()`/`try_online_node()`/map locking and again at early
  `_cpu_up()` before locks, state changes, or startup callbacks. It requires an
  exact `CPUHP_ONLINE` token and public preflight. Direct thaw, SMT, frozen, and
  unattested internal paths are denied.
- CPU-down admission requires the same-generation safe-off C02/L02 entry
  snapshot and private branch attestation before public `cpu_down()`, then
  repeats exact `CPUHP_OFFLINE` admission at early `_cpu_down()`. Direct
  suspend, shutdown, frozen, and unattested internal paths are denied.
- The `add_cpu()` and `remove_cpu()` device wrappers reach the same public
  online/offline gates. External probe/release or device-topology mutation is
  absent in the selected arm64/ACPI-disabled profile and fails closed if a
  future configuration adds it. This does not claim the present mask is
  immutable: the selected internal `cpu_die_early()` failure path clears the
  target's present bit and is owned separately by P30/A39.
- The suspend interlock remains closed not only for a live token but also while
  membership is nonzero, provider state is not `NONE`, or phase is `FAULT`.
- The natural HPS caller already holds `hps_ctxt.lock`; reacquiring it would be
  invalid in the public-equivalent Gemian lane. Its success accounting must
  follow the membership commit, never the return of generic CPU-down alone.
- CPUHVFS transaction recognition must happen before `cpufreq_mutex`, and all
  admitted A72 actions, including `CPU_DOWN_FAILED`, must skip CPUHVFS hardware
  writes in that compatibility lane. Neither rule authorizes vendoring
  HPS/CPUHVFS.
- P17 publishes CPU8 `ON_ISSUED` while provider state is exactly `NONE`; only
  then may R01 publish `ACQUIRE_INFLIGHT` and consume one provider attempt.
  R03/P21 is the sole no-effect clean refusal. A durable provider-reference
  identity created by M01 persists across M02/M03 transaction generations and
  is consumed exactly by M04.
- CPU8/CPU9 CPU_ON is one-shot and bound to exact two-argument
  `psci_ops.cpu_on()` values: validated MPIDR `0x200`/`0x201` and the exact
  physical `secondary_entry`. The exact 2026-08-02 CPU8 ownership/prestate
  gates and 2026-08-03 CPU9 cluster-reuse/empty-shared-write gates remain
  normative; the predecessor up-path affinity observation is superseded.
- M02 first requires P15's CPU_ON return and same-MPIDR secondary completion,
  then full accepted generic callbacks, both CPUs online, and inherited
  cluster/DCM publication. Only then may it schedule static delayed evidence:
  initial schedule, sample 1 at about 1 second, reschedule 1, sample 2 at about
  6 seconds, reschedule 2, then sample 3 at about 10 seconds. Every sample must
  preserve exact callback/IPI identities, online accounting, and equal
  cumulative hit counts. P10 is forbidden before sample 3 and all remaining
  M02 proofs. Any post-full-bringup callback/IPI, identity, accounting, hit,
  shared-resource, provider, A33-final, schedule, or reschedule failure enters
  P19 `FAULT`, retains `members=0x1` and the durable provider reference, and is
  reset-only with no inverse or retry.
- Linux 7.1.3 startup failure can automatically roll back through teardown,
  CPU_OFF, and `cpu_kill` under an up token without down admission. A37 keeps
  the CPU-up veto closed until that path is proven non-failing, a reviewed
  core/A72 no-auto-teardown propagation interface exists, or reviewed target
  `cpu_die` and controller `cpu_kill` up-token guards suppress CPU_OFF and
  affinity. The last alternative deliberately takes P32 to A30 `FAULT` with a
  possibly cleared online mask, conservative ledgers, and reset-only recovery.
- An earlier path bypasses A37. `secondary_start_kernel()` checks local CPU
  capabilities; `cpu_die_early()` bypasses `cpu_can_disable` and optional
  `cpu_disable`, clears the target present bit, publishes `CPU_KILL_ME`, and
  directly reaches the method's `cpu_die`, after which the controller reaches
  `cpu_kill`. P30/A39 require separate up-token guards at target `cpu_die` and
  controller `cpu_kill` so neither CPU_OFF nor affinity can run. The
  `CPU_PANIC_KERNEL`, pre-C `CPU_STUCK_IN_KERNEL` for 52-bit VA or unsupported
  page granule, and unknown/default-timeout branches are distinct terminal
  blockers and each needs impossibility proof or a reviewed core interception.
- Linux 7.1.3 arm64 reports `DEAD` inside `cpu_die()` immediately before
  `cpu_operations::cpu_die` enters PSCI CPU_OFF; the controller later calls
  `cpu_kill`. Generic PSCI
  `cpu_kill` uses a 100-ms jiffies deadline around repeated active affinity
  calls with 100-to-1000-us sleeps. That outer deadline cannot bound the first
  secure call and the repeats violate this contract's one-query budget.
- arm64 selects `HOTPLUG_CORE_SYNC_DEAD` with CPU hotplug; disabling it is not
  a solution because cleanup would skip `ops->cpu_kill` and leave the target
  parked in WFI without physical teardown. The controller cleanup callback is
  void, warns on kill failure, and does not propagate that failure to
  `_cpu_down()`, so generic takedown can continue without an A72 proof.
- Its earlier void `cpuhp_bp_sync_dead()` wait is also warn-only: a 10-second
  failure to report `DEAD` skips arch cleanup/kill yet generic teardown
  continues. Neither `DEAD` nor that timeout is physical-off proof.
- Canonical patch 0092 supplies neither `cpu_die` nor `cpu_kill`. Enabling the
  generic `cpu_psci_ops` A72 off path as-is is therefore prohibited. A future
  method must audit `cpu_can_disable`, optional `cpu_disable`/resident-TOS
  policy, `cpu_die`, and `cpu_kill`; die/kill alone is insufficient.
- A27 closes the `DEAD` race: target `.cpu_die` publishes `OFF_COMMITTED`
  immediately before CPU_OFF, and the controller waits without SMC for that
  exact handoff. `OFF_COMMITTED` does not claim the target entered the SMC.
- Querying could still race target CPU_OFF entry. The secure audit proves a WFI
  poll but not concurrent SMC lock/deadlock safety, so A29 requires exact
  firmware concurrency proof or an owner-safe entry/WFI discriminator before
  any query.
- P20 atomically consumes one level-0 query for the owner-validated target
  MPIDR and enters `QUERY_INFLIGHT` before the call. CPU9-off additionally
  requires private `big_on=0x3`; last-CPU8-off requires `big_on=0x1`. Aliased,
  other-level, retained, already-off, non-target, and repeated queries are
  prohibited.
- A31's private branch proof may not merely be carried forward to P20. A40
  blocks the query until a complete private-ledger writer/caller inventory
  excludes every other CPU_ON, CPU_OFF, affinity, and private writer under the
  transition/policy freeze for the whole interval, or an owner-safe serialized
  exact-branch revalidation occurs immediately before P20 through a non-SMC
  reader or with independent A29-equivalent secure-concurrency proof. C02/L02
  writer drain alone is insufficient.
- M03 separately requires an independent CPU9 `PWR_CON` and power-ack OFF
  readback plus exact C07 invariance. M04 requires exact L06-L13 proofs,
  including distinct iDVFS, DCM, SRAM, sentinel, and provider owners. These
  post-query proofs cannot substitute for the pre-query private branch gate.
- A nonreturning synchronous call cannot execute a fault edge: provider
  acquire/release remains in its inflight provider state, CPU_ON remains
  `ON_ISSUED` with its attempt consumed, and affinity remains
  `QUERY_INFLIGHT`. Every such state is retry-forbidden until a known-good
  platform or external reset.
- A38 makes each of CPU8-up, CPU9-up, CPU9-off, and last-CPU8-off one-shot per
  boot. P05/P06/P11 and a failed post-P31 A28 check never rearm an operation;
  only a known-good platform/external reset plus A34 reinitializes all four
  bits, including from `IDLE` with no token and a consumed attempt.
- Generic CPUHP may clear `cpu_online_mask` and return success after a swallowed
  kill failure while the A72 ledger/provider remains conservative. A30 treats
  this as terminal divergence with no rollback and requires a core propagation
  change or reviewed outer completion sidechannel. P32 is the exact
  `VERIFYING -> FAULT` edge for guarded A37 up rollback: target `cpu_die` skips
  CPU_OFF, controller `cpu_kill` skips affinity, and no inverse/query/retry is
  allowed.
- P13 is not an ordinary reboot path. Platform/external reset may return any
  phase, including `IDLE` with a consumed P31 attempt, to reset `IDLE` only
  after A34 proves the exact zero tuple: both A72 CPUs offline, `members=0x0`,
  provider `NONE`, owner-safe private replay zero, both targets restored
  present/possible, and non-aliased mappings exactly `0x200`/`0x201`. Any
  topology or mapping mismatch remains terminal. The terminal reset/bootstrap
  owner remains unresolved.

## Analysis

### Source-closure correction (2026-08-05)

The later
[`A72 CPU-up source closure`](../2026-08-05-a72-cpu-up-source-closure/README.md)
is the current design authority for implementation review of A41 and the
P30/P32 mechanism.
This frozen experiment remains authoritative for phase, membership, provider,
admission, and one-shot ownership, but its original P30/P32 descriptions are
chronological inputs rather than a sufficient implementation design.

The correction is substantive:

- A41 must pre-account every false-on-A53/true-on-A72 local capability and all
  mitigation, parameter, alternative, and HWCAP side effects before arm64
  finalization. The deterministic minimum includes BHB with A72 `k=8`,
  erratum 1742098 with compat AES suppression, and speculative-AT.
- P30 is split into P30K/C/P/E/U. Default timeout is not proof that the target
  parked; exact-generation cancellation must arbitrate against late
  SUCCESS/online/completion, and a missing park acknowledgment is fail-stop.
- P32 is split into P32A/D/F/X/R and must be controller-published before outer
  rollback. Exact `.cpu_disable` is the primary target guard before topology,
  online, IPI, and IRQ effects. The earlier paired die/kill proposal remains a
  mandatory defense for `cpu_die_early()` and deeper rollback, not the primary
  A37 boundary.
- P14/P15 must be published immediately after successful `__cpu_up()` and
  before later CPUHP synchronization. Generic CPU-up return never proves that
  rollback cleanup succeeded.

The existing frozen TSVs and transcript are intentionally unchanged. Apply the
linked correction before any implementation review; neither document
authorizes a build or device action.

The hypothesis is confirmed only as a source-level constraint. The phase and
ledger model prevents optimistic software state from outrunning physical
evidence. It closes the structural admission requirement for public/internal
up and down, frozen bypasses, HPS, and notifier paths, but it does not close the
implementation owners needed to relax either current veto.

The contract is not implementable yet. There is no CPU9-off runtime evidence.
The owner-safe private `big_on` entry/branch proof, a real writable regulator
consumer and durable identity owner, separate DCM/SRAM/iDVFS/sentinel and
per-core power observers, exact active-kernel source reconciliation, complete
startup/rollback/teardown and PM inventories, a no-auto-rollback CPU-up
interface, branch-specific early-secondary status interception, a complete
private-ledger writer/caller inventory and freshness owner, an A72-owned full
CPU-ops completion/propagation sequence, secure concurrency proof, and a
reviewed terminal reset/bootstrap mechanism remain unresolved. The exact
predecessor gates remain in the pinned safe-off C/L rows and the named CPU8/CPU9
startup designs; this experiment does not re-prove them.

## Conclusion

`confirmed` as a source-only blocking contract. All four membership commit
points, durable provider ownership, symmetric admission layers, query and call
budgets, predecessor proof gates, lock order, and platform/external-reset-only
terminal semantics are frozen.

No implementation, CPU_ON/CPU_OFF candidate, build, deployment, or device
action is authorized.

## Follow-up

Use this contract as an input to the ordered Gate 4 source work in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). Preserve the existing CPU8/CPU9
CPU boot and disable vetoes until every implementation blocker has separately
reviewed evidence and the contract is revalidated.
