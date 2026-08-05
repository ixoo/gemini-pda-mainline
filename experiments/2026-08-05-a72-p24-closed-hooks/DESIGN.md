# P24 closed generic admission-hook model

## Claim boundary

This directory contains an independent source-only specification oracle
labeled `PARTIAL_P24_CLOSED_ADMISSION_HOOKS`. It models a negative hook seam,
not a P17/P18/P24 transaction.

The oracle does not import or inspect Linux source. It proves no C source
order, build, runtime behavior, device result, P30E ordering, or production
CPU admission. A separate static validator must later compare exact C source
with this model.

## Three-layer dispatch contract

The modeled hook layers are:

1. Generic weak defaults return `PASS_THROUGH`, preserving existing handling.
2. Arm64 dispatch invokes an optional CPU-method callback. An absent callback
   or out-of-range CPU returns `PASS_THROUGH` and leaves existing generic
   validation responsible for the input.
3. The MT6797 callback returns `PASS_THROUGH` for logical CPU0 through CPU7.
   CPU8 and CPU9 alone reach the closed-owner validator.

Pass-through is not A72 authorization. It means only that this optional hook
does not change behavior for an unrelated architecture, method, CPU, or
out-of-range input. The model never executes the delegated generic path.

## Source-order contract

The public source order is exactly:

```text
PUBLIC_HOOK
  -> CPU_POSSIBLE
  -> NODE_ONLINE_WORK
  -> CPU_MAPS_LOCK
```

The internal source order is exactly:

```text
INTERNAL_HOOK
  -> PER_CPU_STATE
  -> CPUS_WRITE_LOCK
  -> CPUHP_STATE
  -> CPUHP_CALLBACK
  -> CPU_BOOT_METHOD
```

The hook error returns directly. Public denial therefore precedes every named
public operation. Internal denial precedes per-CPU lookup, locks, stack
preparation, CPUHP mutation, callbacks, architecture boot, and the later
`arch_smt_update()` cleanup path. Both direct thaw (`tasks_frozen != 0`) and
direct SMT (`tasks_frozen == 0`) calls must enter the internal hook.

## Exact decisions

| Platform/method/input | Public result | Internal result |
| --- | --- | --- |
| Other architecture | `PASS_THROUGH` | `PASS_THROUGH` |
| Arm64 method without callback | `PASS_THROUGH` | `PASS_THROUGH` |
| CPU outside arm64 dispatch bound | `PASS_THROUGH` | `PASS_THROUGH` |
| MT6797 CPU0 through CPU7 | `PASS_THROUGH` | `PASS_THROUGH` |
| MT6797 CPU8/9, `CPUHP_ONLINE`, not frozen | `-EAGAIN` | `-EAGAIN` |
| MT6797 CPU8/9, `CPUHP_ONLINE`, frozen | not applicable | `-EPERM` |
| MT6797 CPU8/9, intermediate target | `-EINVAL` | `-EINVAL` |

Identity/target validation precedes frozen-context validation. The owner is
`CLOSED`; an unreachable `AVAILABLE` state would still return
`-EOPNOTSUPP`, not success.

## Transaction and lock boundary

The hook API is result-only. It allocates, returns, copies, and persists no
transaction or output. In particular, it does not call the transaction-begin
API. That distinction prevents a public stack result from being discarded or
an internal caller from repeating transaction entry.

The internal validation path may perform only a bounded leaf read. It cannot
sleep or take the owner transition mutex because `_cpu_up()` can already be
under the CPU map/add-remove lock. There is no owner opener or positive result
in this slice.

## Reviewed C mapping

Patch 0160 maps the model to two weak generic declarations in
`include/linux/cpu.h` and `kernel/cpu.c`. The public `cpu_up()` path calls
`arch_cpu_up_preflight()` before `cpu_possible`, node-online work, or the CPU
maps lock. The internal `_cpu_up()` path calls
`arch_cpu_up_validate()` before the per-CPU state lookup, CPU maps write lock,
CPUHP state changes, callbacks, or the architecture boot method. The weak
implementations return zero, so an architecture that does not override them
keeps its existing behavior.

Arm64 dispatch in `arch/arm64/kernel/smp.c` bounds-checks the CPU and invokes
an optional callback only when the selected `struct cpu_operations` provides
one. The MT6797 PSCI adapter supplies callbacks only in the named
`CONFIG_ARM64_MT6797_A72_P24_ADMISSION_HOOKS` profile and routes CPU8/CPU9 to
the membership leaf check. CPU0 through CPU7, methods without callbacks, and
out-of-range dispatch remain pass-through cases.

The membership implementation performs identity and target checks, frozen
context rejection, a `READ_ONCE()` fast rejection, and a raw-spinlock-protected
owner-health read. It returns only the model's negative results, allocates no
transaction, takes no transition mutex, and has no production caller or
opener. The existing MT6797 CPU-boot `-EAGAIN` and CPU-disable `false`
backstops are unchanged. Ten default-off KUnit cases include two callback
routing/no-mutation cases, but they were not built or run.

This source mapping is exact for the frozen patch and profile identities in
the experiment record. It remains a source-only denial seam: it does not
implement P17/P18/P24 transaction lifecycle, P30E, CPU_ON, or hardware
support.

## Immutable state and backstops

Every correct probe preserves one complete frozen value:

- owner `CLOSED`, membership `UNINITIALIZED`, and no opener;
- no transaction begin, allocation, or persisted output;
- no P31, A38, consumed attempt, or token;
- no P17, P18, or P30 publication;
- no provider, membership, or hardware effect;
- no CPU_ON request and no CPU-boot-method call; and
- the existing CPU-boot `-EAGAIN` and CPU-disable false backstops retained.

Pass-through probes also leave this hook-owned state unchanged. Delegated
generic behavior is deliberately outside the model.

## Oracle method

`scripts/oracle.py` uses frozen standard-library dataclasses. It evaluates 32
probes covering both hook stages, both A72 CPUs, every CPU0-through-CPU7
pass-through case, weak-default and optional-callback absence, bounds
behavior, both direct internal caller classes, exact online admission, frozen
admission, and an intermediate target.

It checks the two frozen source-order sequences independently from the result
matrix. This is a specification ordering proof, not source inspection.

`scripts/test_mutations.py` changes one rule at a time. Its 39 targeted
mutations cover:

- either hook omitted;
- every named public or internal ordering boundary;
- thaw or SMT bypass;
- global denial of another architecture or arm64 method;
- A53 denial and out-of-range policy capture;
- A72 admission and acceptance of intermediate or frozen inputs;
- transaction begin, transition-mutex acquisition, allocation, or persisted
  output;
- an owner opener, P31/A38/attempt/token, membership phase, P17/P18/P30,
  provider/member/hardware, CPU_ON, or CPU-boot effect; and
- removal of either boot or disable backstop.

## Exact nonclaims

- No Linux source inspection or C implementation validation by the oracle.
- No kernel configuration resolution, build, KUnit execution, or runtime test.
- No device, network, firmware, partition, package, candidate, or deployment.
- No owner opener, transaction begin, P17/P18/P24 transaction, token, or P30
  integration.
- No P30E MMU-off object, cache maintenance, PoC, barrier, or assembly proof.
- No positive CPU8/CPU9 admission and no hardware-support claim.
