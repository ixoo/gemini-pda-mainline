# CPU8/CPU9 scheduler-context execution design

## Parent boundary

The exact parent is the repeatable pair-v6 candidate from
`2026-08-03-a72-cpu9-parallel-disjoint-load`. Two attributable watchdog cycles
completed every inherited startup, HPS, scalar, multiline, and parallel-load
predicate with identical deterministic results. The parallel phase executed in
synchronous IPI callback context; it did not test ordinary scheduler dispatch.

This experiment adds one observation only after the complete pair-v6 state is
a pass. No parent result is reopened or weakened.

## Hypothesis

The standard scheduler can concurrently dispatch one normal-priority kernel
thread bound to CPU8 and one bound to CPU9. Both threads can rendezvous in task
context, execute exactly 262,144 deterministic integer iterations, remain on
their assigned CPUs, publish exact results, and exit through the standard
`kthread_stop()` lifecycle before the retained watchdog recovery.

This is a bounded task-context diagnostic. It is not userspace scheduling,
migration, capacity/energy-model validation, long-duration load, or production
scheduler qualification.

## Exact execution contract

### Parent gate and owner

1. Keep CPU startup, pair sampling, HPS veto, scalar, multiline, parallel-load,
   sample timing, watchdog, power, and recovery sources identical.
2. The existing CPU0-pinned worker completes every pair-v6 phase first.
3. Only if the exact pair-v6 positive predicate passes, create the two scheduler
   tasks once. No task exists before the parent gate.
4. CPU0 remains the sole creator, waker, waiter, stopper, and publisher.

### Thread creation and affinity

- Create exactly two threads with `kthread_create_on_cpu()`.
- Thread 0 is bound to CPU8 and thread 1 to CPU9 before either first wake.
- Use fixed names `gemini-a72-sc/8` and `gemini-a72-sc/9` through the API's
  restricted CPU-number format.
- Do not change scheduling class, priority, nice value, cpuset, affinity after
  creation, or any global scheduler policy. Upstream `kthread()` resets each
  new thread to `SCHED_NORMAL`; this experiment leaves that default intact.
- If either creation fails, stop the other never-woken thread through the
  documented `kthread_stop()` path and publish a fault. There is no retry.

### Task-context and placement oracle

Each thread must prove all of the following before workload execution:

- `current->flags & PF_KTHREAD` is set;
- `in_interrupt()` is false;
- `get_cpu()` reports its exact assigned CPU, followed immediately by
  `put_cpu()`;
- its callback data identifies the same expected CPU.

Each thread repeats the `get_cpu()`/`put_cpu()` placement check after its
workload. Any wrong CPU or interrupt context returns `-EXDEV` or `-EINVAL` and
preserves the first error. The workload itself runs preemptible; placement is
not manufactured by disabling preemption across the phase.

### Concurrent entry and bounded workload

State is static and initialized before creation. Each task:

1. increments one shared `ready` atomic and waits until it equals exactly 2;
2. consumes one task-local total spin budget of `1U << 25` while waiting;
3. executes exactly 262,144 iterations of a pure unsigned-64-bit recurrence
   seeded by its assigned CPU number;
4. invokes `cond_resched()` after every 4,096 iterations, exactly 64 call sites
   per task, without changing affinity or priority;
5. folds every deterministic value into a task-local 64-bit hash;
6. verifies its ending CPU and task context;
7. stores result, error, completed iterations, and hash, executes `smp_wmb()`,
   increments `finished`, and completes its task-specific completion object;
8. returns its exact error code normally from the thread function.

The recurrence uses fixed constants, XOR, shifts, and unsigned arithmetic. It
must not depend on time, addresses, randomness, scheduler counters, prior data,
or device state. A static validator independently computes both exact hashes.

The `ready == 2` rendezvous proves both bound tasks were dispatched before
either workload starts. It does not claim simultaneous instruction issue.

### CPU0 wait and cleanup

- Wake CPU8 then CPU9 exactly once with `wake_up_process()` and require each
  return value to be 1.
- Wait on each completion with an absolute phase deadline derived once from
  `jiffies + msecs_to_jiffies(2000)`. Do not grant two independent two-second
  windows.
- Internal waits remain finite, so a completion timeout does not create an
  unbounded thread. After the waits, call `kthread_stop()` exactly once for each
  successfully created task, even on fault.
- Require both stop returns to equal the corresponding task result and require
  both to be zero for a pass.
- Clear both task pointers after stop. Publication before both stop calls and
  any surviving task pointer are terminal faults.
- The retained hardware watchdog remains the outer recovery bound if scheduler
  dispatch or cleanup violates the expected finite behavior.

## Publication and terminal

The CPU0 worker resets scheduler-context state, completes pair-v6, runs the
task lifecycle, executes a write barrier, and publishes completion. Sample 3
takes one coherent snapshot after an acquire barrier.

The exact terminal version is pair-v7. Both pass and fault forms retain every
pair-v6 field and add:

- `sc_reported`;
- `sc_iterations=262144 sc_rescheds=64`;
- expected, starting, and ending CPU for each task;
- task-context flags for each task;
- creation errors, wake returns, task errors, and stop returns;
- per-task completion-wait success;
- completed iterations and final ready/finished counters;
- exact deterministic CPU8/CPU9 hashes.

The positive suffix is:

```text
sc_reported=1 sc_iterations=262144 sc_rescheds=64 sc_expected8=8 sc_start8=8 sc_end8=8 sc_expected9=9 sc_start9=9 sc_end9=9 sc_task8=1 sc_task9=1 sc_create8=0 sc_create9=0 sc_wake8=1 sc_wake9=1 sc_wait8=1 sc_wait9=1 sc_error8=0 sc_error9=0 sc_stop8=0 sc_stop9=0 sc_done8=262144 sc_done9=262144 sc_ready=2 sc_finished=2 sc_hash8=A sc_hash9=B
```

`A` is `f678147669874ecd` and `B` is `c2274327e9c8104c`, independently
precomputed from the fixed recurrence. Partial marker text, thread names,
online CPUs, or a watchdog restart are not a pass.

## Result classes

### Pass

Require the complete pair-v7 pass, every inherited pair-v6 predicate, both
exact scheduler hashes and lifecycle fields, changed-cycle watchdog recovery,
offline recovery CPUs 8/9, unchanged unmounted boot2, and no panic, BUG,
Internal error, Call trace, asynchronous SError, lockup, timeout, affinity
warning, or unexpected fault.

One pass earns one exact repeat. A second pass closes only bounded pinned
kernel-task dispatch. It does not authorize CPU_OFF, migration, userspace load,
OPP/cpufreq, thermal, suspend, or another power boundary.

### Parent regression

Any failed or incomplete pair-v6 field is a regression. Do not evaluate the
scheduler suffix or repeat unchanged; compare exact source and binary boundaries
against the parent.

### Creation, dispatch, placement, workload, or cleanup fault

Any create error, wake result other than 1, incomplete completion wait, wrong
task context/CPU, incomplete iteration count, wrong ready/finished count, hash
mismatch, nonzero task error, or stop/result mismatch rejects the candidate.
Record the first exact boundary and do not repeat unchanged.

### Restart without pair-v7

Use prearmed changed-cycle pstore plus the latest retained inherited terminal to
distinguish terminal-not-reached from evidence loss. Repeat only if a new
independent observation can distinguish those classes.

### Lost recovery

Missing automatic restart, wrong recovery identity, changed boot2, online
recovery CPU8/9, or any undeclared fault is a safety failure. Recover through
known-good Gemian and do not repeat unchanged.

## Source and binary invariants

Before container construction, exact parent-versus-child review must prove:

- only `arch/arm64/kernel/psci.c` changes;
- all startup, HPS, CPU_OFF, watchdog, power, regulator, clock, reset, SPM,
  SRAM-LDO, MMIO, and inherited test sources are identical;
- exactly two `kthread_create_on_cpu()` calls target CPUs 8 and 9;
- both binds occur by construction before exactly one wake per task;
- SCHED_NORMAL is inherited and no scheduler policy, priority, nice, cpuset, or
  post-create affinity operation is added;
- task-context and start/end CPU checks, exact workload/`cond_resched()` bounds,
  one shared deadline, internal spin bound, both completions, unconditional
  two-task cleanup, stop/result checks, and pointer clearing are present;
- representative mutations of parent gate, target CPU, task count, context
  check, recurrence, iteration/reschedule bound, rendezvous, deadline, wake,
  completion, stop, cleanup order, error propagation, hash, and terminal field
  are rejected;
- child and parent configs and diagnostics are identical; and
- measured stack remains within the parent boundary with no workload array or
  task payload placed on stack.

## Explicit non-goals

- CPU_OFF, hotplug-down, migration, affinity changes after creation, or another
  power transition;
- userspace tasks, scheduler capacity/energy policy, realtime policy, priority
  changes, load balancing, or long-duration stress;
- DVFS/OPP, cpufreq, idle, thermal, suspend/resume, or production integration;
- weakening the HPS veto, watchdog, startup, serviceability, or recovery path;
- claiming general scheduler or A72 production stability from this diagnostic.
