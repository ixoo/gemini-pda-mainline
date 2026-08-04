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

The current phase-attribution child derives from the exact rejected start-gate
revision. It changes observation only by adding durable pre/post markers around
the existing task and parent phases. It does not change the synchronization,
workload, timeouts, power boundary, or recovery path.

## Exact execution contract

### Parent gate and owner

1. Keep CPU startup, pair sampling, HPS veto, scalar, multiline, parallel-load,
   sample timing, watchdog, power, and recovery sources identical.
2. The existing CPU0-pinned coherency worker completes and publishes every
   pair-v6 phase without calling, resetting, or waiting for scheduler code.
3. Sample 3 snapshots and decides the complete pair-v6 terminal predicate.
   Only inside that predicate's pass branch, create the two scheduler tasks
   once. No task exists and no child reset occurs in the inherited worker.
4. The sample-3 CPU0 worker remains the sole scheduler-state resetter, creator,
   waker, waiter, stopper, and publisher.

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

1. increments one shared `ready` atomic and completes its CPU-specific ready
   completion;
2. blocks for at most 2,000 ms on one shared start completion;
3. after an acquire barrier, requires the parent's explicit `start_allowed`
   authorization; a release without authorization is a bounded cancellation;
4. executes exactly 262,144 iterations of a pure unsigned-64-bit recurrence
   seeded by its assigned CPU number;
5. invokes `cond_resched()` after every 4,096 iterations, exactly 64 call sites
   per task, without changing affinity or priority;
6. folds every deterministic value into a task-local 64-bit hash;
7. verifies its ending CPU and task context;
8. stores result, error, completed iterations, and hash, executes `smp_wmb()`,
   increments `finished`, and completes its task-specific completion object;
9. returns its exact error code normally from the thread function.

The recurrence uses fixed constants, XOR, shifts, and unsigned arithmetic. It
must not depend on time, addresses, randomness, scheduler counters, prior data,
or device state. A static validator independently computes both exact hashes.

The two ready completions plus the parent-authorized shared release prove both
bound tasks were dispatched and blocked before either workload starts. They do
not claim simultaneous instruction issue.

### CPU0 wait and cleanup

- Wake CPU8 then CPU9 exactly once with `wake_up_process()`. Zero and one are
  the only accepted return values, and either is meaningful only when the
  independent task-context, CPU, ready, start, done, and hash fields later
  prove execution.
- Derive one ready deadline from
  `jiffies + msecs_to_jiffies(2000)` and use its remaining time for both
  CPU-specific ready completions. Do not grant two independent windows.
- Set `start_allowed` only when both ready waits succeed, publish it with a
  barrier, and call `complete_all()` exactly once even on readiness failure so
  any created task exits through bounded cancellation.
- Derive one fresh 2,000 ms done deadline after release and use its remaining
  time for both CPU-specific done completions.
- Every explicit completion wait has a finite deadline. After those waits,
  call `kthread_stop()` exactly once for each successfully created task, even
  on fault. `kthread_stop()` has no independent software timeout; the retained
  hardware watchdog bounds a task that cannot complete cleanup.
- For PASS, require both stop returns to equal the corresponding task result
  and require both to be zero.
- Clear both task pointers after every required stop. Publication before every
  successfully created task has stopped, or any surviving task pointer, is a
  terminal fault.
- The retained hardware watchdog remains the outer recovery bound if scheduler
  dispatch or cleanup violates the expected finite behavior.

## Publication and terminal

The inherited CPU0 coherency worker completes and publishes pair-v6 without any
scheduler-context call or state access. Sample 3 takes the complete inherited
snapshots, resets scheduler state, and evaluates the byte-identical pair-v6
predicate. Its pass branch runs the bounded task lifecycle before emitting the
byte-identical pair-v6 terminal; its fault branch marks scheduler execution
ineligible without creating a task. Each branch then calls a `noinline`
scheduler reporter with only the already-decided parent pass/fault boolean.
That reporter takes one coherent snapshot after an acquire barrier and exposes
immutable pointers to the static result records after every successfully
created task has stopped.
It must not copy either result payload onto the parent terminal worker's stack.

This ordering is an explicit invariant: the child may delay terminal text only
after the complete parent result has already been published and snapshotted. It
must never delay `coh_reported`, multiline, or parallel publication, and it must
not execute from the inherited coherency worker.

The exact result is a two-line composite: the unchanged complete pair-v6 parent
terminal followed immediately by one pair-v7 scheduler terminal. Pair-v7 adds:

- `parent_pass`;
- `sc_reported`;
- `sc_iterations=262144 sc_rescheds=64`;
- expected, starting, and ending CPU for each task;
- task-context flags for each task;
- creation errors, wake returns, task errors, and stop returns;
- per-task ready-wait, start-wait, and completion-wait success;
- completed iterations and final ready/finished counters;
- exact deterministic CPU8/CPU9 hashes.

The positive pair-v7 line is:

```text
gemini-a72-pair-v7 result=pass parent_pass=1 sc_reported=1 sc_iterations=262144 sc_rescheds=64 sc_expected8=8 sc_start8=8 sc_end8=8 sc_expected9=9 sc_start9=9 sc_end9=9 sc_task8=1 sc_task9=1 sc_create8=0 sc_create9=0 sc_wake8=W8 sc_wake9=W9 sc_readywait8=1 sc_readywait9=1 sc_startwait8=1 sc_startwait9=1 sc_wait8=1 sc_wait9=1 sc_error8=0 sc_error9=0 sc_stop8=0 sc_stop9=0 sc_done8=262144 sc_done9=262144 sc_ready=2 sc_finished=2 sc_hash8=A sc_hash9=B
```

`A` is `f678147669874ecd` and `B` is `c2274327e9c8104c`, independently
precomputed from the fixed recurrence. `W8` and `W9` are each zero or one, with
execution established independently by the remaining fields. Partial marker
text, thread names, online CPUs, or a watchdog restart are not a pass.

### Phase-attribution marker contract

The observation-only child adds 31 unique `gemini-a72-sc-phase` source strings.
The complete successful path emits 23 ordered parent records and eight ordered
task records for each of CPUs 8 and 9, for 39 runtime records. Parent records
have no CPU field; task records require the exact CPU field.

The parent order is create8, create9, wake8, wake9, ready8 wait, ready9 wait,
release, done8 wait, done9 wait, stop8, stop9, and run-exit, with before/after
records around every operation except run-exit. Each CPU independently orders
task ready, start wait, work, and done, each with before/after records. CPU8 and
CPU9 task records may interleave in either scheduler-valid order; no global
task order may be invented.

Every trace known continuous from create8-before preserves a prefix of one
reachable parent source path, each emitted task stream as an exact prefix,
task-done-after before its emitted stop-after, and run-exit after every emitted
stop-after. The stronger
cross-causal checks belong to PASS, or to a fault field that independently
claims the corresponding wait succeeded: the relevant wake-before precedes
the task's first record, both task-ready-before records precede release-before,
release-before precedes a successful task-start-wait-after, and task-done-before
precedes a successful parent done-wait-after.

On a create failure, `kthread_stop()` can terminate the surviving never-woken
kernel task without invoking its thread function, so no task marker is
required between that CPU's stop-before and stop-after; the other CPU can have
no task or stop records. Any emitted task marker requires the corresponding
explicit wake-before. Readiness or done timeouts can also let release or a
parent wait-after precede a late task record. These are pair-v7 fault branches,
not PASS-order violations. A retained before record without its
matching after record identifies the bounded operation in progress only when
continuous fatal/reset evidence rules out capture truncation; concurrent open
task phases must both be reported rather than assigning an unsupported failing
CPU.

A retained pstore trace whose first phase record is not create8-before is
head-truncated evidence, not proof of a source-order violation. Preserve its
records and validate only relative source order among the retained records, but
do not localize a phase unless another continuous observation establishes the
missing head. The USB snapshot validator requires continuity from
create8-before and labels a lost or unclosed transport boundary instead of
manufacturing that continuity.

## Result classes

### Pass

Require an immediately adjacent complete pair-v6 pass and pair-v7 pass with
`parent_pass=1`, both exact scheduler hashes and lifecycle fields, changed-cycle
watchdog recovery, offline recovery CPUs 8/9, unchanged unmounted boot2, and no
panic, BUG, Internal error, Call trace, asynchronous SError, lockup, timeout,
affinity warning, or unexpected fault.

One pass earns one exact repeat. A second pass closes only bounded pinned
kernel-task dispatch. It does not authorize CPU_OFF, migration, userspace load,
OPP/cpufreq, thermal, suspend, or another power boundary.

### Parent regression

Any failed or incomplete pair-v6 field, or pair-v7 with `parent_pass=0`, is a
regression. Do not evaluate the scheduler fields or repeat unchanged; compare
exact source and binary boundaries against the parent.

### Creation, dispatch, placement, workload, or cleanup fault

Any create error, wake result outside zero or one, incomplete ready/start/done
wait, wrong task context/CPU, incomplete iteration count, wrong ready/finished
count, hash mismatch, nonzero task error, or stop/result mismatch rejects the
candidate. Record the earliest source/phase boundary corroborated by the full
field vector; if retained order cannot distinguish co-failing fields, report
all of them. Do not repeat unchanged.

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
- the inherited coherency worker contains no scheduler-context reset, run,
  wait, result, or publication reference;
- scheduler reset follows all inherited snapshots, scheduler execution occurs
  only inside the exact complete pair-v6 pass branch, and pair-v6/pair-v7
  terminals follow scheduler cleanup;
- exactly two `kthread_create_on_cpu()` calls target CPUs 8 and 9;
- both binds occur by construction before exactly one wake per task;
- SCHED_NORMAL is inherited and no scheduler policy, priority, nice, cpuset, or
  post-create affinity operation is added;
- task-context and start/end CPU checks, exact workload/`cond_resched()` bounds,
  one shared ready deadline, one fresh shared done deadline, two ready
  completions, one authorized shared release, both done completions,
  cleanup of every successfully created task, stop/result checks, and pointer
  clearing are present;
- representative mutations of parent gate, target CPU, task count, context
  check, recurrence, iteration/reschedule bound, rendezvous, deadline, wake,
  completion, stop, cleanup order, error propagation, hash, and terminal field
  are rejected;
- child and parent configs and diagnostics are identical; and
- the pair-v6 terminal worker remains within its parent stack boundary, the
  no-inline scheduler reporter has its own bounded frame, and no workload array
  or task payload is placed on stack.

## Explicit non-goals

- CPU_OFF, hotplug-down, migration, affinity changes after creation, or another
  power transition;
- userspace tasks, scheduler capacity/energy policy, realtime policy, priority
  changes, load balancing, or long-duration stress;
- DVFS/OPP, cpufreq, idle, thermal, suspend/resume, or production integration;
- weakening the HPS veto, watchdog, startup, serviceability, or recovery path;
- claiming general scheduler or A72 production stability from this diagnostic.
