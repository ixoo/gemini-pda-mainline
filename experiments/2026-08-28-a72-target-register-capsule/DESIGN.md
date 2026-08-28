# CPU8/CPU9 target-register capsule design

## Parent boundary

The exact parent is the admitted kthread-unpark scheduler-context source with
patchset SHA-256 `bd5799ce...`. Two runtime cycles proved every pair-v6 and
pair-v7 PASS field, target placement, bounded workload, ordered cleanup,
watchdog recovery, and unchanged boot2. This child may not alter any parent
field, terminal, power path, timing bound, watchdog, or CPU_OFF prohibition.

## Capture placement and bound

`mt6797_a72_sc_run()` remains reachable only inside the complete pair-v6 PASS
branch. Each existing task verifies task context and initial CPU placement,
then performs one capture before publishing `task-ready`. `get_cpu()` holds the
task on that CPU for the fixed read and comparison sequence; `put_cpu()` closes
the region before any completion wait, workload, `cond_resched()`, or cleanup.

There is no loop, wait, retry, allocation, lock, interrupt disable, firmware
call, or device access in the capture. A failed capture is terminal for pair-v7
through the existing task `error` field, but both tasks still publish readiness
and follow the unchanged bounded release/cleanup path.

## Versioned capsule v1

Each static result owns one capsule with:

- ABI and canonical field-count metadata;
- valid mask, exact task CPU, error, and publication-complete state;
- MPIDR, MIDR, REVIDR, CNTFRQ, CTR, DCZID, and CLIDR;
- ID_AA64DFR0, ID_AA64ISAR0/1, ID_AA64MMFR0/1, and ID_AA64PFR0/1;
- AArch32 ID_ISAR0--5, ID_MMFR0--3, and ID_PFR0--1;
- exact field-by-field agreement with the target's existing `cpu_data`; and
- one 64-bit identity over 32 named fields in fixed order.

The identity uses the already-established FNV-style 64-bit mixing constants.
It never hashes structure memory or padding. Publication writes every field,
then the identity, executes `smp_wmb()`, and finally sets `complete=1` through
`WRITE_ONCE()`.

## Acceptance

A target capsule passes only when:

- expected CPU and actual CPU are exactly 8 or 9;
- MPIDR is respectively `0x200` or `0x201`;
- MIDR is Arm Cortex-A72;
- all fixed register groups were read;
- every overlapping value equals the target's prior `cpu_data` record;
- error is zero, complete is one, and the recomputed identity matches.

The existing pair-v7 line remains byte-identical and already requires both task
errors to be zero. Four additional fixed lines per target (`core`, `aa64`,
`a32isar`, and `a32mm`) repeat CPU and capsule identity so a host validator can
reject missing, mixed, duplicated, reordered, or transport-truncated records.
A runtime PASS requires the adjacent exact pair-v6 and pair-v7 PASS terminals
plus all eight capsule lines and independently recomputed identities.

## Failure classes

- `pre-parent`: no capture line; preserve the existing parent fault result.
- `pre-capture`: pair-v7 fault and an unpublished zero capsule for the affected
  task.
- `capture-fault`: complete capsule with nonzero error, incomplete valid mask,
  wrong target identity, `cpu_data` mismatch, or identity mismatch.
- `capture-pass-parent-fault`: capsules are observations only; do not promote a
  result when pair-v7 is not PASS.
- `complete-pass`: exact parent PASS plus two complete validated capsules.
- `transport-incomplete`: preserve bytes but make no register-evidence claim.

No failure authorizes a retry inside the same boot, CPU_OFF, a power inverse,
or any additional physical action. Recovery remains the inherited watchdog.

## Decision map

- Complete pass: use the captured target values to define the mainline
  attestation schema and enumerate the still-missing system/policy evidence.
- Field mismatch: stop; audit the target startup record and capture timing
  before another kernel.
- Register/capture fault with exact parent PASS: retire the child and narrow the
  read set or encoding from exact source/disassembly evidence.
- Parent fault or incomplete transport: no target-register conclusion; do not
  repeat unchanged unless a new independent observation path is added.
