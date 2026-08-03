# CPU8/CPU9 parallel disjoint-load design

## Parent boundary

The exact parent is the repeatable pair-v5 candidate from
`2026-08-03-a72-cpu9-multiline-integrity`. Across two exact watchdog cycles it
completed every inherited pair/HPS/scalar predicate and then 64 alternating
rounds over 256 aligned cachelines. Each cycle performed 262,144 exact
cross-CPU word checks with zero errors or mismatches and the same two
cross-matching hashes.

This experiment does not reopen those results. It adds one observation only
after the complete pair-v5 state is a pass.

## Hypothesis

Retained CPUs 8 and 9 can concurrently write disjoint cachelines in one shared
64 KiB working set, publish completion through finite release/acquire barriers,
and then verify every word owned by the peer for 128 rounds.

- CPU8 owns every even-numbered line and CPU9 owns every odd-numbered line.
- Each CPU writes `128 * 512 * 8 = 524,288` words.
- Each CPU verifies `128 * 512 * 8 = 524,288` peer-written words.
- The complete phase therefore performs 1,048,576 exact cross-CPU word checks
  and 1,048,576 deterministic writes.

The disjoint ownership removes same-line writer contention while adding genuine
concurrent write traffic. This is a bounded diagnostic, not general stress or
production coherency qualification.

## Exact execution contract

### Scheduling and parent gate

1. Keep CPU startup, three sample callbacks, HPS veto, scalar callback/wait,
   alternating multi-cacheline callback/wait, and their bounds source-identical.
2. The existing CPU0-pinned worker completes the scalar and alternating phases
   first.
3. Only if every pair-v5 scalar and multiline predicate passes, issue exactly
   one additional synchronous `smp_call_function_many(..., wait=true)` to exact
   mask `{8, 9}`.
4. Any wrong callback CPU, worker not on CPU0, wrong mask, duplicate scheduling,
   or incomplete parent result is a terminal fault.

### Shared working set and ownership

- Define exactly 1,024 lines.
- Each line is exactly eight `u64` words (64 bytes) and explicitly 64-byte
  aligned.
- The complete working set is exactly 65,536 bytes in static BSS.
- CPU8 owns lines where `line % 2 == 0`; CPU9 owns lines where
  `line % 2 == 1`.
- A callback may write only its owned lines and may verify only peer-owned
  lines. No callback writes a line owned by the other CPU.
- Every payload access uses `WRITE_ONCE()` or `READ_ONCE()`.
- No allocation, DMA, device memory, userspace mapping, or persistent storage
  is allowed.

### Deterministic payload

Use a new pure unsigned-64-bit pattern of `(writer_cpu, round, line, word)` with
fixed constants, XOR, shifts, and unsigned arithmetic only. It must not depend
on time, randomness, addresses, counters, or prior payload. The static validator
recomputes representative vectors across both writers and extreme dimensions.

### Reusable finite barriers

Maintain three monotonic atomic counters initialized to zero:

- `ready`: both callbacks have entered the current round;
- `written`: both callbacks have completed and release-published their owned
  writes; and
- `verified`: both callbacks have completed peer verification before either
  begins the next round.

For round `1..128`, each callback performs exactly:

1. increment `ready`, then wait until `ready == 2 * round`;
2. write all owned lines and fold every written value into its write hash;
3. execute `smp_wmb()`, increment `written`, wait until
   `written == 2 * round`, then execute `smp_rmb()`;
4. read every peer-owned line, fold actual values into its read hash, and
   compare each word against an independently recomputed peer pattern;
5. on the first mismatch, preserve exact round/line/word/expected/actual and a
   nonzero `-EILSEQ` result;
6. execute `smp_wmb()`, increment `verified`, wait until
   `verified == 2 * round`, then execute `smp_rmb()` before the next round.

Each callback receives one total spin budget of `1U << 26`. Its three waits per
round consume the same callback-local budget; it is never reset or expanded.
Budget exhaustion returns `-ETIMEDOUT`. If one callback faults, the peer may
consume its remaining finite budget and return; there is no retry or fallback.

The pass requires CPU8's write hash to equal CPU9's read hash and CPU9's write
hash to equal CPU8's read hash. Hash equality is supplemental: every peer word
must also pass exact comparison.

## Publication and terminal

The CPU0 worker resets state, completes the inherited phases, runs the parallel
phase synchronously, executes a write barrier, and publishes completion. The
sample-3 terminal takes one coherent snapshot after an acquire barrier.

The exact terminal version is pair-v6. Both pass and fault forms retain every
pair-v5 pair/HPS/scalar/multiline field and add:

- `pl_reported`;
- `pl_rounds=128 pl_lines=1024 pl_words=8`;
- actual callback CPUs and errors;
- completed rounds per CPU;
- final ready/written/verified counters (all 256 on pass);
- CPU8/CPU9 write and peer-read hashes;
- first mismatch round, line, word, expected value, and actual value.

The positive suffix is:

```text
pl_reported=1 pl_rounds=128 pl_lines=1024 pl_words=8 pl_cpu8=8 pl_cpu9=9 pl_error8=0 pl_error9=0 pl_done8=128 pl_done9=128 pl_ready=256 pl_written=256 pl_verified=256 pl_hash8w=A pl_hash8r=B pl_hash9w=B pl_hash9r=A pl_bad_round=0 pl_bad_line=0 pl_bad_word=0 pl_expected=0000000000000000 pl_actual=0000000000000000
```

`A` and `B` must be deterministic nonzero 64-bit hashes and cross-match exactly.
Partial marker text is never a pass.

## Result classes

### Pass

Require the complete pair-v6 pass, all inherited pair-v5 predicates, exact
parallel fields, automatic watchdog recovery, changed ordinary-Gemian boot
identity, watchdog-class reason, CPUs 8/9 offline after recovery, exact
unmounted boot2 checksum, and no panic, BUG, Internal error, Call trace,
asynchronous SError, lockup, timeout marker, or unexpected fault.

One pass earns one exact repeat. A second pass closes only bounded disjoint
parallel integrity and permits design of a changed finite same-cacheline atomic
or scheduler/load observation. It does not permit CPU_OFF or a power boundary.

### Parent regression

Any failed/incomplete pair-v5 scalar or alternating state is a regression. Do
not evaluate parallel success, do not repeat unchanged, and compare source and
binary boundaries against the exact parent.

### Parallel mismatch or callback fault

Any nonzero `pl_error*`, incomplete round, counter other than 256, hash
cross-mismatch, wrong callback CPU, wrong bounds, or nonzero mismatch record is
a reject. Record every terminal field and do not repeat unchanged. Use the first
error/mismatch boundary to choose the next source change.

### Restart without pair-v6

Use retained pair-v2/v4/v5 state, pstore continuity, and recovery facts to
classify terminal-not-reached versus evidence loss. Repeat only if a new
independent observation can distinguish those classes.

### Lost recovery

Missing automatic restart, wrong recovery identity, changed boot2, online
recovery CPU8/9, panic, SError, lockup, or another undeclared fault is a safety
failure. Recover through known-good Gemian and do not repeat unchanged.

## Source and binary invariants

Before container construction, exact parent-versus-child review must prove:

- only `arch/arm64/kernel/psci.c` changes;
- startup, generic completion, public CPU-down, HPS, watchdog, regulator,
  clock, reset, SPM, SRAM-LDO, and MMIO sources are identical;
- inherited scalar and alternating callbacks/waits are source-identical and
  linked;
- exactly one new synchronous cross-call targets exact mask `{8, 9}`;
- ownership parity, dimensions, alignment, loop bounds, total spin budget,
  atomic barrier targets, barriers, exact comparisons, deterministic pattern,
  hashes, and complete terminal are present and linked;
- representative mutations of dimensions, ownership, counter target, bound,
  barrier, target CPU, wait mode, pattern dimension, comparison, hash
  cross-check, parent gate, static placement, and terminal field are rejected;
- child and parent configs and diagnostics are identical; and
- stack capture proves no working-set object is on callback/worker stack.

## Explicit non-goals

- CPU_OFF, hotplug-down, or another power transition;
- changing HPS veto, startup, sample timing, watchdog, or power sequencing;
- same-cacheline concurrent writers, atomic RMW stress, cache maintenance,
  DMA, device memory, userspace load, scheduler migration, or long-duration
  stress;
- DVFS/OPP, cpufreq, idle, thermal, suspend/resume, or production integration;
- claiming general coherency or stability from this bounded diagnostic.
