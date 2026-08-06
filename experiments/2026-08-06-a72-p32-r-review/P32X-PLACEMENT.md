# P32X effect-prefix placement review

## Scope

This is a source-placement review for the P32X architecture-effect prefix. It
does not add hooks, enable CPU_ON/OFF, or authorize a device action. The
upstream source reference is [Linux v7.1 `kernel/cpu.c`](https://github.com/torvalds/linux/blob/v7.1/kernel/cpu.c)
and [arm64 `smp.c`](https://github.com/torvalds/linux/blob/v7.1/arch/arm64/kernel/smp.c);
the v7.1.3 build must still validate the eventual patch.

## Exact operation order

The arm64 `__cpu_disable()` path is the decisive boundary:

1. `op_cpu_disable()` calls the platform `.cpu_disable` callback.
2. Only after it returns success does arm64 call `remove_cpu_topology()`.
3. It then calls `numa_remove_cpu()`.
4. It clears the online mask with `set_cpu_online(cpu, false)`.
5. It tears down IPIs with `ipi_teardown(cpu)`.
6. It migrates interrupts with `irq_migrate_all_off_this_cpu()`.

The existing MT6797 P32 `.cpu_disable` guard therefore has to publish the
P32X boundary before returning its refusal. The refusal path must be recorded
as “blocked before architecture effects”; it must not pretend that
topology, NUMA, masks, IPI, or IRQ operations completed.

The remaining architecture/CPUHP boundaries are separate:

| Effect | Upstream boundary | Required P32X observation |
| --- | --- | --- |
| `CPU_OFF_ATTEMPT` | entry to `__cpu_disable()` / `op_cpu_disable()` | forbidden attempt marker before the platform guard |
| topology | `remove_cpu_topology()` | begin/end around the call |
| NUMA | `numa_remove_cpu()` | begin/end around the call |
| online mask | `set_cpu_online(cpu, false)` | begin/end around the call |
| IPI | `ipi_teardown(cpu)` | begin/end around the call |
| IRQ | `irq_migrate_all_off_this_cpu()` | begin/end around the call |
| DEAD/RCU | `cpuhp_report_idle_dead()` and `rcutree_report_cpu_dead()` | ordered event before/after the report |
| park | `take_cpu_down()` and `stop_machine_park()` | event after park returns or explicit no-return classification |
| lockdep | `lockdep_cleanup_dead_cpu()` | begin/end around cleanup |
| controller kill | arm64 `op_cpu_kill()` / `arch_cpuhp_cleanup_dead_cpu()` | observation without affinity information |
| affinity | any `AFFINITY_INFO` path | forbidden marker; no call is permitted |

`kernel/cpu.c::cpuhp_down_callbacks()` is a callback-range rollback and state
reset boundary, not a substitute for the arm64 architecture-effect prefix.
Its callback events belong to P32A; the P32X effect events must remain
ordered relative to the architecture calls above.

## Implementation constraints

- The effect record is bounded and carries `valid`, `complete`, `overflow`,
  and `unknown` state. An uninstrumented operation is `unknown`, never an
  implicit success.
- The P32 `.cpu_disable` refusal is a no-effect terminal prefix: it records
  the forbidden attempt and the guard boundary, then classifies all later
  architecture operations as not reached. It does not set their completion
  bits.
- If a future path returns success from `.cpu_disable`, every operation above
  must have an explicit begin/end event before P32R can accept it.
- `CPU_OFF_ATTEMPT` and any affinity-information attempt force branch X. No
  marker may call CPU_OFF, alter affinity, or issue provider/device I/O.
- Generic CPUHP callbacks and architecture code must use a no-op path when
  `CONFIG_ARM64_MT6797_A72_P32_ROLLBACK` is disabled; the default profile must
  retain its existing behavior and layout.

This review narrows the next source patch: implement the trace API and the
arm64 `__cpu_disable()` boundary first, then add the DEAD/RCU/park/lockdep and
controller-kill observations only after their exact callback ownership is
verified. It is not a support claim or a Buildbox result.
