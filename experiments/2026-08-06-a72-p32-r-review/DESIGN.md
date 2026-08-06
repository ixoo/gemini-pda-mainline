# P32A/P32X/P32R integration design

## Purpose

This document turns the three open findings in the P32R review into an
implementable, fail-closed contract. It is a source design only: it does not
open CPU_ON, CPU_OFF, a provider call, or any device action.

The design is deliberately separate from the existing P32 scalar record. The
scalar record remains the exact-generation identity and branch owner; the new
prefix records describe what the generic CPUHP path actually did before that
identity was consumed.

## One transaction, one owner

The controller owns one `p32_trace` inside the exact active transaction. It is
published once, while the transition owner is still `VERIFYING`, and is
consumed once after the generic reverse range. Every writer validates the
same `{operation, target_cpu, target_mpidr, generation, cookie}` tuple under
the existing state lock. A stale writer is ignored or returns an error; it
cannot create a new generation.

The trace has three immutable sections:

| Section | Required contents | Writer boundary |
| --- | --- | --- |
| `callback_prefix` | nested AP rollback state, outer failing state, reset/reverse boundaries, and each callback event including direction, state, instance ordinal, return value, and warning status | `cpuhp_kick_ap()` and the two callback-range paths |
| `effect_prefix` | ordered bits for topology, NUMA, online/present masks, IPI, IRQ, RCU, lockdep, DEAD, park, and controller-kill observations | arm64 teardown and target/controller CPU-ops hooks |
| `ledger_handoff` | original error, final P32 branch, callback/effect completeness, membership snapshot, provider identity/state, and A30 terminal disposition | the owner-side P32R consume call |

Each section carries `valid`, `complete`, `overflow`, and `unknown` flags.
`overflow` or `unknown` is a terminal P32X condition, never a successful
rollback. No source path may silently truncate a callback or effect event.

## P32A callback-prefix contract

The core must publish these ordered events:

1. Any nested `cpuhp_kick_ap()` rollback records its pre-reset state, the
   state passed to `cpuhp_reset_state()`, the resulting state, and its return
   value.
2. The controller records the outer failing callback and the state at which
   it failed before publishing the P32 scalar identity.
3. The controller records the outer reset boundary.
4. Every reverse callback is appended in execution order, including dynamic
   and multi-instance callbacks. A callback that warns or returns an error is
   still an event.
5. The controller records the end of the reverse range and the final CPUHP
   state before P32R consumption.

The event vector is fixed-size and its capacity is checked against the
selected source/configuration registration inventory before it can be armed.
If a runtime registration exceeds that capacity, the writer records
`overflow=1`, marks branch X, and refuses completion. A digest may accompany
the vector for independent comparison, but a digest is not a replacement for
the events.

## P32X architecture-effect contract

The architecture path sets an effect bit immediately before each operation,
and records a completion bit only after that operation returns. The required
bits are:

```text
TOPOLOGY_REMOVE  NUMA_REMOVE  ONLINE_CLEAR  PRESENT_CLEAR
IPI_TEARDOWN     IRQ_MIGRATE  RCU            LOCKDEP
DEAD_PUBLISH     TARGET_PARK  KILL_OBSERVED  NO_AFFINITY
CPU_OFF_ATTEMPT  AFFINITY_INFO_ATTEMPT      UNKNOWN
```

`CPU_OFF_ATTEMPT` and `AFFINITY_INFO_ATTEMPT` are forbidden-effect evidence;
their presence forces branch X and global fail-stop handling. The normal
P32D guard must therefore publish before the first architecture bit. If any
architecture operation is not instrumented, `UNKNOWN` is set before returning
from that path, so the trace cannot be mistaken for a clean rollback.

## P32R ledger handoff

After the generic reverse callback range returns, `arch_cpu_up_rollback_complete`
must call an owner API with the original startup error and the complete trace.
The owner API is the only writer allowed to set `ledger_handoff.valid`.

The API accepts only when:

- the exact active transaction still matches the trace identity;
- the scalar P32 state is PARKED, or the trace is explicitly terminal X;
- callback and effect sections are complete and have no unknown/overflow bits;
- the original callback error still matches the public return value; and
- no completion, HPS success accounting, provider release, retry, or
  membership commit has happened.

On acceptance it copies the membership and provider snapshots into the
terminal record, sets the A30 disposition to `FAULT_ROLLBACK_RECORDED`, and
retires the generation. A held provider is marked `FAULT_UNKNOWN` for later
owner-specific recovery; the handoff does not call a provider or guess that a
release succeeded. A mismatched or incomplete trace sets `FAULT_ROLLBACK_LOST`
and remains fail-stop.

## Validation obligations

The independent model in `scripts/integration_oracle.py` must cover:

- nested-before-outer event ordering;
- fixed and dynamic callback events, including multi-instance ordinals;
- event-vector overflow and unknown-event rejection;
- every architecture-effect bit and forbidden CPU_OFF/affinity bits;
- exact identity and original-error mutations;
- ledger handoff only after reverse completion;
- one-shot generation retirement and rejection of duplicate completion;
- exact trace identity, including operation, target CPU, MPIDR, generation, and
  cookie;
- copying the pre-fault membership/provider snapshot into the terminal record,
  changing a held provider to `FAULT_UNKNOWN`, and preserving `NONE` when no
  provider reference existed;
- rejection after any HPS-success, provider-release, retry, or membership-commit
  side effect, with no terminal snapshot or generation retirement.

Until a source patch implements this contract and passes a clean Buildbox
build plus the model, the P32R review remains open and all device gates stay
closed.
