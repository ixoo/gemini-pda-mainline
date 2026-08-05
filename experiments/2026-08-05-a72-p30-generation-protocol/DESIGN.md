# P30 generation protocol model

## Claim boundary

This directory is an independent, source-only specification oracle labeled
`PARTIAL_P30_PROTOCOL_MODEL`. It deliberately does not import or inspect Linux
source. It has no P24 production owner, production hook, build/runtime claim,
or P30E MMU-off proof.

The model is bounded to two exact operation tokens:

| Operation | CPU | MPIDR | Generation | Cookie |
| --- | ---: | ---: | ---: | ---: |
| CPU8 | 8 | `0x200` | 42 | `0x8a720042` |
| CPU9 | 9 | `0x201` | 7 | `0x9a720007` |

The full target tuple is `(cpu, mpidr, generation, cookie)`. Generation values
are opaque and scoped by operation: they are tested only for exact identity,
never ordered globally. Retirement is one-shot for the complete operation
token. Thus CPU8/gen42 retirement must not reject the later CPU9/gen7 token,
while an exact replay of either retired token must fail.

## State and winner contract

The controller phases are `FREE`, `PREPARED`, `ABORTED`, `ARMED`,
`PUBLISHING`, `PUBLISHED`, `CANCELLED`, `FAILING`, `FAULTED`, `PARKED`, and
`PANICKED`.

- `PREPARED` may become `ABORTED` only with exact proof that no CPU_ON was
  issued. An ambiguous dispatch result becomes `FAULTED` and latches the first
  quarantine record.
- An exact target-side claim observed in `PREPARED` or `ABORTED` is an
  `ILLEGAL_EDGE`: it latches quarantine and enters `FAULTED`, so the operation
  can neither remain armable nor be released.
- `ARMED` admits exactly one winner: publish, cancel, fault, or failure.
- A publish claim enters `PUBLISHING`. Quarantine may latch there, but cancel,
  failure, and a second winner cannot overtake it. The owner must finish the
  exact publication and expose its completion.
- `PUBLISHED` completion is drained using the controller's internal online
  observation. A caller-provided success assertion is not authoritative.
- A latched quarantine is first-cause, sticky, and reset-only. It blocks
  successful P14/P15 retirement, while publication completion and online
  draining remain available so no owner is stranded.
- Successful P14/P15 retirement requires exact publication completion,
  completion consumption, a positive internal online sample, and no
  quarantine. It records the operation token before returning to `FREE`.
- `PARKED` and `PANICKED` are immutable reset-only terminal states.

Target-local publication, parking, and panic actions must carry the exact
active target tuple. A mismatch cannot publish or create a terminal record; it
latches quarantine instead.

## K/C/P/E/U closure

The modeled terminal branches have these frozen meanings:

| Branch | Legal closure |
| --- | --- |
| K | A claimed K failure parks as K after the clean bounded return effects. |
| C | A claimed C failure parks as C; a claimed K failure may also refine to C when the post-C return path parks. |
| P | A claimed P failure records panic first, then publishes `PANICKED` only with the panic interlock set; generic parking is forbidden. |
| E | A claimed E exception records the exception effects and parks as E. |
| U | A claimed U failure, cancellation, or protocol fault parks as U. |

Every terminal record is bound to the active exact tuple. Once `PARKED` or
`PANICKED` is published, the terminal state and record are immutable. Sticky
quarantine never clears or replaces its first cause, and the panic interlock
must be set before `PANICKED` is published.

## Reviewed dormant C mapping

Patch `0158` implements this state algebra as a raw-spinlock-serialized C-only
control object. Every metadata writer and snapshot uses the same lock. State
publication remains release-ordered, target calls carry the exact tuple, and
the success consumer samples `cpu_online(exact_cpu)` only after it observes
`PUBLISHED` and drains the exact completion. Per-operation retirement records
the CPU8 and CPU9 one-shot histories independently; it never compares their
opaque generation numbers.

The default-off KUnit suite has 17 cases covering the success witness, both
race winners, PREPARED/ABORTED/ARMED faulting, publisher draining under
quarantine, exact tuple mismatches before and after a winner, online mismatch,
premature retirement, direct K/C/E/U, K-to-C refinement, P-only panic closure,
and terminal immutability. It was statically reviewed but not built or run.

This C object is not an assembly ABI and is not visible to the MMU-off path.
Its effect mask stores a conservative caller-supplied prefix; branch-specific
effect enforcement is intentionally deferred to the future production hooks.
It also supplies no P24 token owner, bounded controller wait, actual target
park site, P14/P15 hook, global panic/reset action, or replacement for the
current shared secondary startup state. Those are required before production
P30 can be claimed.

## Oracle method

`scripts/oracle.py` uses frozen dataclasses and enumerates every state reachable
from `FREE` under the bounded action alphabet. It checks state invariants,
transition invariants, liveness witnesses needed by the contract, the
CPU8/gen42 to CPU9/gen7 success trace, and exact replay rejection.

`scripts/test_mutations.py` changes one rule at a time and requires the oracle
to report the intended violation. The mutations cover global generation
ordering, replay, PREPARED/ARMED fault handling, winner uniqueness, pre-armed
target claims, `PUBLISHING` interruption, quarantine retirement and drain
polarity, missing drain, caller-owned online state, target-tuple mismatch,
forbidden C-to-K cross-closure, P parking/interlock, quarantine replacement,
and terminal mutation.
