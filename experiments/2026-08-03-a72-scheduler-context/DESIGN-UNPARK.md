# CPU8/CPU9 kthread-unpark source contract

## Boundary and hypothesis

This is a source-only successor contract. Its immediate parent is the rejected
phase-attribution patchset with SHA-256
`b2c971d4a1860ec09616a61dbd8a29fde488f7d99deb8bd6bfbf2c517b2c3493`.
The historical `0001` and `0002` patches, their source editors, and their
validators remain evidence and are not rewritten.

The retained runtime trace reached both successful creates but no task phase:
[`results/runtime-phase-attribution-attempt-1-incomplete-trace-20260804.txt`](results/runtime-phase-attribution-attempt-1-incomplete-trace-20260804.txt).
The exact source/binary audit explains that observation: this vendor kernel's
`kthread_create_on_cpu()` returns a parked per-CPU task, while
`wake_up_process()` neither clears its park state nor wakes `TASK_PARKED`:
[`results/source-binary-kthread-park-contract-20260804.txt`](results/source-binary-kthread-park-contract-20260804.txt).

The single hypothesis is that replacing the two intended activation calls with
`kthread_unpark()` lets the otherwise unchanged CPU8 and CPU9 tasks reach their
existing ready/start/work/done lifecycle. This contract does not build a
kernel, construct a boot container, authorize a device write, or reinterpret
the rejected runtime result. Ordered successor work remains owned by
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).

## Finite transformation

[`scripts/unpark_edits.py`](scripts/unpark_edits.py) accepts only six unique
parent anchors in `arch/arm64/kernel/psci.c` and applies exactly these changes:

1. Rename the result member `wake_result` to `unpark_issued`.
2. Replace the marker-wrapped CPU8 assignment and `wake_up_process(task8)`
   with `unpark8-before`, `kthread_unpark(task8)`, publication of
   `unpark_issued = 1`, and `unpark8-after`, in that order.
3. Make the equivalent replacement for CPU9.
4. Replace the accepted wake-return ranges in the PASS predicate with exact
   `unpark_issued == 1` requirements for both tasks.
5. Rename terminal fields `sc_wake8`/`sc_wake9` to
   `sc_unpark8`/`sc_unpark9`.
6. Publish the two `unpark_issued` members in those terminal positions.

`kthread_unpark()` returns `void`. Therefore `unpark_issued` is an honest
parent-owned observation: static zero initialization means not issued, and the
parent writes one only after the call returns. It is not a kernel success code.

No other scheduler source changes. In particular, creation and CPU binding,
ready/start/done completions, shared deadlines and release, deterministic
workload and hashes, placement checks, stop cleanup, pair-v6 ownership, HPS
veto, CPU_OFF prohibition, power, and watchdog boundaries remain byte-identical
to the immediate parent. The source still has 31 phase strings and a complete
success still emits 39 records; only the four parent wake phase names become
unpark phase names.

## Acceptance proof

[`scripts/test_unpark_child.py`](scripts/test_unpark_child.py) requires the
parent and child sources together. It reverse-applies all six replacements and
requires byte-for-byte equality with the supplied parent. This makes the
finite edit, rather than a hand-maintained list of allowed paths, the complete
child delta.

The validator also extracts exact function definitions from the pinned vendor
sources and requires the decision-relevant lifecycle:

- `kthread_create_on_cpu()` records per-CPU state and CPU, then parks before
  returning;
- `__kthread_parkme()` waits in `TASK_PARKED` and clears the parked state on
  exit;
- `__kthread_unpark()` clears `KTHREAD_SHOULD_PARK`, test-clears
  `KTHREAD_IS_PARKED`, restores the per-CPU binding with `TASK_PARKED`, and
  wakes `TASK_PARKED`;
- public `kthread_unpark()` reaches that internal helper;
- `kthread_stop()` retains its cleanup-unpark, normal wake, and completion
  wait sequence; and
- `wake_up_process()` remains restricted to `TASK_NORMAL`, while the exact
  declaration and `TASK_PARKED`/`TASK_NORMAL` definitions remain pinned.

The child scheduler section must contain exactly two creates, two unparks, and
two stops, with no `wake_up_process()`. Both creates precede activation; each
before marker precedes its matching unpark call, publication, and after marker;
both activations precede the shared ready deadline. PASS requires both exact
issuance fields.

The self-test builds a finite in-memory parent fixture, transforms it with the
real editor, accepts the exact child, and then requires rejection of all 20
decision-relevant mutations:

- missing CPU9 unpark; wrong CPU9 target; restored wake API; missing CPU9
  publication; publication before the call;
- missing CPU9 PASS gate; legacy terminal schema; legacy phase schema;
- missing create-time park; missing parked-state update; missing
  `KTHREAD_SHOULD_PARK` clear; degraded `KTHREAD_IS_PARKED` test-clear;
- changed unpark bind state; changed unpark wake state; missing public-unpark
  call; missing stop cleanup-unpark;
- changed `wake_up_process()` mask; missing unpark declaration; changed
  `TASK_PARKED` value; and `TASK_NORMAL` improperly including `TASK_PARKED`.

Passing this source contract establishes only that a future generated child is
the intended lifecycle correction against the pinned parent and pinned vendor
semantics. Compile, accepted-binary, deployment, and runtime evidence remain
separate gates.
