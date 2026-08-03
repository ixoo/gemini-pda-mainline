# CPU8/CPU9 bounded coherency design

## Parent evidence

The exact terminal-attribution parent passed twice. In both watchdog-bounded
cycles, CPUs 8 and 9 were Linux-accounted online and each completed three
synchronous callbacks. Its durable terminals coherently attributed 91 then 89
HPS CPU9-down requests to the public `-EPERM` veto. Both cycles excluded every
declared fault, returned through watchdog reason 4, left CPUs 8/9 offline in
Gemian, and preserved boot2 exactly.

Those callbacks prove execution and accounting but do not yet prove concurrent
shared-memory coherency or useful load across the A72 pair.

## Child hypothesis

With both A72 CPUs already online and retained, a CPU0-pinned worker can issue
one synchronous cross-call to CPUs 8 and 9. The two target callbacks can
exchange a monotonically increasing token through shared memory for exactly
1,024 rounds. If every publish is preceded by `smp_wmb()`, every consumed turn
is followed by `smp_rmb()`, and all shared payload/turn accesses use
`READ_ONCE()`/`WRITE_ONCE()`, exact final sequences and zero per-CPU errors are
bounded evidence of concurrent A72 cache coherency under controlled load.

## Exact changes

Only `arch/arm64/kernel/psci.c` may change.

1. Add static experiment-only shared state: publication state, turn, CPU8 and
   CPU9 sequences, observed CPU identities, per-CPU errors, and completion.
2. Add a finite wait helper. It checks one expected turn with `READ_ONCE()` and
   `cpu_relax()` while decrementing a per-callback budget initialized to
   16,777,216. Exhaustion returns `-ETIMEDOUT`; no wait is unbounded.
3. Add one cross-call callback:
   - CPU8 waits for turn 8, acquire-checks CPU9's preceding sequence after the
     first round, publishes its current sequence, executes `smp_wmb()`, and
     hands turn 9 to CPU9. After round 1,024 it waits for and validates CPU9's
     final acknowledgement.
   - CPU9 waits for turn 9, executes `smp_rmb()`, validates CPU8's current
     sequence, publishes the same round to its sequence, executes `smp_wmb()`,
     and hands turn 8 back to CPU8.
   - Any unexpected CPU, sequence, or exhausted budget records a negative
     per-CPU error and returns. The peer then either observes the mismatch or
     exhausts its own finite budget.
4. Add one statically declared coherency work item. Its worker must run on CPU0,
   publish state `-1`, reset all shared fields, construct a mask containing
   exactly CPUs 8 and 9, and invoke `smp_call_function_many(..., wait=true)`
   exactly once. After both callbacks return, it records the exact CPU IDs,
   errors, and sequences, executes `smp_wmb()`, and publishes state `1`.
5. After the inherited successful sample-2 pair callback and without changing
   either two-second delay, schedule that worker exactly once with
   `schedule_work_on(0, ...)`. Scheduling failure publishes an attributable
   error; it does not retry.
6. At the inherited sample-3 terminal only, snapshot the coherency state after
   `smp_rmb()`. Replace pair-v3 success text with unique pair-v4 text that keeps
   every inherited pair/HPS field and adds:
   `coh_reported`, `coh_rounds`, `coh_cpu8`, `coh_cpu9`, `coh_error8`,
   `coh_error9`, `coh_seq8`, and `coh_seq9`.
7. Emit pair-v4 `result=pass` only when publication is complete, rounds equal
   1,024, CPUs equal 8/9, both errors are zero, and both final sequences equal
   1,024. Otherwise emit one pair-v4 `result=fault` with the complete snapshot.

## Unique terminal and pass predicate

One changed watchdog cycle must retain exactly one terminal matching:

```text
gemini-a72-pair-v4 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=1 hps_cpu=9 hps_error=-1 hps_count=H coh_reported=1 coh_rounds=1024 coh_cpu8=8 coh_cpu9=9 coh_error8=0 coh_error9=0 coh_seq8=1024 coh_seq9=1024
```

`H` must be a positive decimal integer. There must be exactly one terminal and
no pair-v2 fault, pair-v4 fault, CPU9/parent startup fault, generic down-veto
marker, panic, BUG, Internal error, or Call trace. A changed-cycle watchdog
return, exact recovery kernel, offline CPUs 8/9, and unchanged boot2 checksum
remain mandatory.

Earlier pair-v2 samples are optional in the fixed-size retained tail. If
present, they must retain their exact order and fields. The inherited HPS
one-shot record remains optional because pair-v4 retains the durable snapshot.

## Failure and inconclusive classes

- `coh_reported=0`: the CPU0 worker never started before sample 3; reject.
- `coh_reported=-1`: the worker was still running at sample 3; reject the bound.
- scheduling error, wrong worker CPU, wrong target CPU, `-ETIMEDOUT`, sequence
  mismatch, wrong round count, or final sequence below/above 1,024: reject; no
  unchanged retry.
- pair-v2/pair-v4 fault, startup fault, panic, BUG, Internal error, Call trace,
  failed recovery, or changed boot2: reject; no unchanged retry.
- missing unique pair-v4 terminal, absent changed cycle, or conflicting primary
  evidence: inconclusive; improve attribution with a changed artifact.
- automatic restart, screen color, or USB availability without the exact
  terminal is recovery/serviceability evidence only.

## Static and binary invariants

- `mt6797_a72_cpu9_boot`, generic secondary completion, `cpu_down`, and the HPS
  algorithm source remain byte-identical to the exact parent.
- The initial one-second delay and both two-second pair delays remain exact.
- The inherited pair callbacks and HPS snapshot remain unchanged.
- The target mask contains exactly CPUs 8 and 9; the caller is pinned to CPU0.
- There is exactly one cross-call and it is synchronous.
- Every wait consumes one finite shared callback-local budget; no loop can
  reset that budget or wait indefinitely.
- Turn/payload accesses retain `READ_ONCE()`/`WRITE_ONCE()` and matching
  publish/consume barriers.
- Exactly 1,024 rounds are compiled in; no runtime control surface exists.
- Mutation checks reject altered masks/CPU placement, asynchronous cross-call,
  unbounded waits, relaxed accesses/barriers, wrong sequences/rounds, changed
  pair timing, weakened CPU-down vetoes, modified startup/power/HPS source, and
  a terminal missing any inherited or coherency field.

## Safety boundary

This is a short shared-memory/cache-coherency load, not a power-management or
thermal stress test. It starts only after sample 2 on already-online retained
CPUs, has finite work and spin budgets, and remains bounded by the inherited
fixed watchdog recovery. It performs no MMIO, regulator, voltage, frequency,
idle, CPU_OFF, hotplug, storage, or userspace action. Every HPS CPU8/CPU9 down
request still fails at public entry with `-EPERM`.

A pass establishes only this fixed concurrent handshake. It does not establish
general coherency stress, sustained performance, long-term stability, CPU_OFF,
DVFS/OPP, thermal behavior, suspend/resume, or default-profile readiness. One
pass earns one exact repeatability run before any wider or longer load.
