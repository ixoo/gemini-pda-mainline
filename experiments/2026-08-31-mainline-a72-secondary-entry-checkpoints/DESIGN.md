# Design: monotonic P30E secondary-entry checkpoints

## Frozen checkpoint values

| Value | Meaning |
| ---: | --- |
| 0 | P30E claimed; no added checkpoint completed |
| 1 | `__cpu_setup` returned while the identity mapping is active |
| 2 | MMU/virtual switch, EL finalization, vector setup, and secondary-task setup completed |
| 3 | the first explicit statement in `secondary_start_kernel()` ran |
| 4 | the identity mapping was uninstalled |
| 5 | local CPU capabilities were accepted |
| 6 | late target expectation and topology setup completed |
| 7 | CPU-starting notification, IPI setup, and NUMA addition completed |

The target state remains CLAIMED and target sequence remains zero for values
1--7. Existing terminal publication changes state to PUBLISHED, changes target
sequence to one, and replaces the reason with its terminal reason.

## Write contract

The MMU-off writer accepts only value 1. It requires the exact A72 static slot,
ARMED controller, CLAIMED target, sequence zero, and reason zero. It preserves
the caller link, boot mode, `__cpu_setup` SCTLR value, stack, and all
callee-saved registers, then uses the existing full-slot clean plus `dsb sy`.

The normal-text writer accepts only values 2--7. It selects the current A72 by
MPIDR, takes the existing raw spinlock, invalidates the full slot, requires
ARMED/CLAIMED/sequence-zero, requires a strictly increasing reason, writes only
the reason word, and cleans the full slot. A53 CPUs return `-ENODEV`; an
unarmed A72 returns without a write. Callers intentionally ignore observation
errors so instrumentation cannot create a new admission action.

## Decision map

- reason 0: fault during `__cpu_setup`, or the MMU-off writer refused;
- reason 1: fault in MMU enablement, virtual switch, EL/vector/task setup, or
  the next writer refused;
- reason 2: task stack exists; fault before the first C checkpoint;
- reason 3: early C entry executed; fault before identity-map removal completed;
- reason 4: fault before capability validation completed;
- reason 5: fault before target validation/topology completed;
- reason 6: fault before CPU-starting/IPI/NUMA setup completed;
- reason 7: fault between IRQ/IPI/NUMA readiness and existing publication;
- PUBLISHED/sequence 1: the existing late boundary completed;
- CPU8 online: continue with bounded architecture/accounting validation.

Any malformed, decreasing, out-of-range, contradictory, CPU9-bearing,
CPU_OFF-bearing, retry-bearing, or repeated transcript is rejected.
