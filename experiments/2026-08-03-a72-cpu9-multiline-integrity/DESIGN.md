# CPU8/CPU9 multi-cacheline integrity design

## Parent boundary

The exact parent is the repeatable pair-v4 candidate from
`2026-08-03-a72-cpu9-bounded-coherency`. The parent has already passed two
identical runtime cycles. Each cycle brought CPUs 8 and 9 online, completed
three inherited callbacks per CPU, attributed bounded HPS CPU9-down requests to
the fail-closed `-EPERM` veto, completed a 1,024-round scalar turn/sequence
exchange with zero errors, and recovered by watchdog with CPUs 8/9 offline and
boot2 unchanged.

This experiment does not reopen that result. It adds one observation after the
unchanged scalar phase succeeds.

## Hypothesis

Once the scalar pair-v4 phase has completed, retained CPUs 8 and 9 can
alternately publish and verify exact deterministic payloads across 256 distinct
64-byte lines for 64 rounds. A pass requires every one of the 262,144 payload
word checks to match its independently recomputed expected value:

- CPU9 verifies `64 * 256 * 8 = 131,072` words written by CPU8; and
- CPU8 verifies `64 * 256 * 8 = 131,072` words written by CPU9.

The 16 KiB working set and alternating writers materially expand the observation
beyond the parent's scalar turn/sequence words. This remains a bounded
diagnostic, not general memory stress or production coherency qualification.

## Exact execution contract

### Scheduling and CPUs

1. Keep the parent's CPU startup, three sample callbacks, HPS veto, scalar
   coherence callback, and scalar result checks source-identical.
2. The existing CPU0-pinned observation worker first completes the parent's
   single synchronous scalar cross-call to the exact mask `{8, 9}`.
3. Only if the complete scalar result is a pass, issue exactly one additional
   synchronous `smp_call_function_many(..., wait=true)` to exact mask `{8, 9}`.
4. The additional callback records its actual CPU. Any callback other than CPU8
   or CPU9, a worker not on CPU0, a wrong mask, duplicate scheduling, or an
   incomplete scalar parent result is a terminal fault.

### Shared working set

- Define exactly 256 lines.
- Each line is exactly eight `u64` words (64 bytes) and explicitly aligned to
  64 bytes.
- The complete working set is exactly 16,384 bytes in static BSS.
- No allocation, userspace mapping, DMA, device memory, or persistent storage is
  allowed.
- Each payload word is accessed through `WRITE_ONCE()` or `READ_ONCE()`.

### Deterministic payload

Define one pure unsigned-64-bit pattern function of `(writer_cpu, round, line,
word)`. It must use only fixed constants, XOR, shifts, and unsigned arithmetic;
it must not read time, randomness, addresses, CPU counters, or prior payload.
The independent static validator recomputes representative vectors and rejects
any changed constant, missing dimension, signed operation, or non-deterministic
input.

For each round `1..64`:

1. CPU8 writes all eight words of all 256 lines using the CPU8 pattern, folds
   the written values into its deterministic unsigned-64-bit hash, executes
   `smp_wmb()`, and publishes turn 9.
2. CPU9 waits for turn 9 with a finite shared callback budget, executes
   `smp_rmb()`, reads all words, and compares every word against an independently
   recomputed CPU8 value. It records only the first mismatch location,
   expected value, and actual value while preserving a nonzero error.
3. If verification passes, CPU9 writes the CPU9 pattern across the same working
   set, folds its write hash, executes `smp_wmb()`, and publishes turn 8.
4. CPU8 waits for turn 8, executes `smp_rmb()`, and verifies every word against
   the independently recomputed CPU9 value while folding its read hash.
5. CPU8 starts the next round only after the complete CPU9 payload verifies.

The final pass requires CPU8's write hash to equal CPU9's read hash and CPU9's
write hash to equal CPU8's read hash. Hash equality is supplemental; every word
must also pass exact comparison.

### Bounds

- `ML_ROUNDS = 64`.
- `ML_LINES = 256`.
- `ML_WORDS = 8`.
- Each callback receives one total spin budget of `1U << 24`; waits consume and
  never reset or expand that budget.
- Every data loop is bounded by the constants above.
- A wait budget exhaustion returns `-ETIMEDOUT`.
- A data mismatch returns `-EILSEQ` after recording the first mismatch.
- The callbacks stop useful work after the first error, publish their result,
  and return. There is no retry, fallback, delayed work, or unbounded polling.

## Publication and terminal

The CPU0 worker initializes state to running, completes the scalar phase, then
the multiline phase. After the synchronous callback returns it captures:

- reported/completed state;
- rounds, lines, and words;
- actual callback CPUs;
- CPU8/CPU9 errors;
- completed rounds per CPU;
- CPU8-write/CPU9-read and CPU9-write/CPU8-read hashes;
- first mismatch round, line, word, expected value, and actual value.

It executes a write barrier before publishing completed state. The inherited
sample-3 terminal takes one coherent snapshot after an acquire barrier.

The exact pass terminal version is pair-v5 and must contain every inherited
pair-v4 pair/HPS/scalar field plus all multiline fields. The positive form is:

```text
gemini-a72-pair-v5 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=1 hps_cpu=9 hps_error=-1 hps_count=H coh_reported=1 coh_rounds=1024 coh_cpu8=8 coh_cpu9=9 coh_error8=0 coh_error9=0 coh_seq8=1024 coh_seq9=1024 ml_reported=1 ml_rounds=64 ml_lines=256 ml_words=8 ml_cpu8=8 ml_cpu9=9 ml_error8=0 ml_error9=0 ml_done8=64 ml_done9=64 ml_hash8w=X ml_hash8r=Y ml_hash9w=Y ml_hash9r=X ml_bad_round=0 ml_bad_line=0 ml_bad_word=0 ml_expected=0 ml_actual=0
```

`H` must be positive. `X` and `Y` are deterministic nonzero 64-bit hashes and
must cross-match exactly as shown. Pass additionally requires no recorded
mismatch and every exact scalar-parent predicate. The fault terminal has the
same complete fields with `result=fault`; partial marker text is never a pass.

## Result classes

### Pass

Require the complete pair-v5 pass, automatic watchdog recovery, a changed
ordinary-Gemian boot identity, watchdog-class reason, CPUs 8/9 offline after
recovery, exact unmounted boot2 checksum, and no panic, BUG, Internal error,
Call trace, asynchronous SError, lockup, or unexpected fault.

One pass earns one exact repeatability cycle. A second exact pass closes only
this bounded multi-cacheline integrity gate and permits design of a changed,
finite parallel/disjoint load oracle. It does not permit CPU_OFF or a power
boundary.

### Scalar-parent failure

Any failed or incomplete pair-v4 scalar state is a regression. Do not evaluate
multiline fields, do not repeat unchanged, and compare source/binary boundaries
against the exact parent.

### Multiline mismatch or callback fault

Any nonzero `ml_error*`, incomplete round count, hash cross-mismatch, nonzero
mismatch location, wrong callback CPU, or wrong bounds is a reject. Record all
fields and use the first mismatch boundary to choose the next source change. Do
not repeat unchanged.

### Restart without pair-v5

Use earlier retained pair-v2/v4 state, changed-cycle pstore, and recovery
continuity to classify terminal-not-reached versus evidence loss. Repeat only
if a new independent observation can distinguish those classes.

### Lost recovery

Treat a missing automatic restart, wrong recovery identity, changed boot2,
online recovery CPU8/9, panic, SError, lockup, or other undeclared fault as a
safety failure. Recover through the known-good path and do not repeat unchanged.

## Source and binary invariants

Before container construction, exact parent-versus-child review must prove:

- only `arch/arm64/kernel/psci.c` changes;
- CPU startup, `mt6797_a72_cpu9_boot`, generic completion, public CPU-down, HPS
  policy, watchdog, regulator, clock, reset, SPM, SRAM-LDO, and MMIO sources are
  identical;
- the complete parent scalar callback and scalar wait function are
  source-identical and linked;
- exactly one new synchronous cross-call targets exact mask `{8, 9}`;
- working-set dimensions, alignment, loop bounds, total spin budget, barriers,
  exact comparisons, deterministic pattern, hashes, and complete terminal are
  present in source and linked code;
- representative mutations of every dimension, bound, barrier, target, wait
  mode, pattern input/constant, comparison, hash cross-check, mismatch field,
  scalar-parent gate, and terminal field are rejected;
- child and exact parent configurations and compiler diagnostics are identical;
  and
- stack-usage capture proves bounded callback/worker stack with no large
  working-set object on the stack.

## Explicit non-goals

- CPU_OFF or any hotplug down transition;
- changing the HPS veto, startup method, sample timing, watchdog, or power
  sequencing;
- parallel unsynchronized writers, atomics stress, cache maintenance, DMA,
  device memory, userspace load, scheduler migration, or long-duration stress;
- DVFS/OPP, cpufreq, idle, thermal, suspend/resume, or production integration;
- claiming general coherency, stability, or upstream support from this bounded
  diagnostic.
