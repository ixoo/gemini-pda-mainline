# Atomic A72 bootstrap publication contract

## Selected boundary

The implementation is a default-off source-only path with no production
caller. Its sole successful execution is injected KUnit. It adds no physical
reader, DT node, MMIO, SMC, I2C transfer, provider operation, P30 prepare,
CPU_ON, CPU_OFF, or device action.

## Entry ownership and lock lifetime

The publisher accepts only one typed A34 replay-applicability record. It
validates that record before any source callback, then acquires and retains:

1. the CPU hotplug read lock; and
2. `a72_transition_lock`.

While both remain held it creates topology, calls the existing locked direct
capture, constructs one A34-v2 observation, and evaluates the exact recovered
state. It must not call the public direct snapshot, because that API releases
both outer locks before returning.

After A34 passes, it claims exact pristine P30 state. No transition-mutex path
may begin while holding the P30 lock.

## P30 nested finalizer

The P30 subsystem adds one typed pristine-claim finalizer. It:

- rejects a null, malformed, stale, or non-owned claim before any callback;
- acquires the P30 private raw spinlock with interrupts disabled;
- revalidates the exact opaque claim;
- clears the logical claim while retaining the private lock;
- invokes exactly one non-sleeping callback; and
- releases the P30 lock only after the callback returns.

The callback may acquire only `a72_state_lock`, the next lock in the declared
order. It may not sleep, allocate, log, invoke a provider, call hardware, or
enter any other protocol. A negative callback result means no owner field was
mutated. A zero callback result means the complete owner commit occurred and
no later operation can fail.

Keeping the P30 lock across the callback closes the interval in which
`arm64_late_cpu_startup_prepare()` could otherwise enter after claim release
but before publication.

## Exact owner precondition

The publisher checks the exact pristine owner before source capture and again
inside the final callback. The second record must byte-match the owner embedded
in the direct snapshot. Private controller, next-generation, and next-cookie
state must also remain zero.

An already `AVAILABLE` owner returns `-EALREADY` before a source callback. A
different non-pristine state returns `-EPERM`. Neither path claims P30.

## Prepared destination and single commit

Before the finalizer, the publisher prepares this scalar destination:

- diagnostic blockers: `MT6797_A72_BLOCK_MASK` with only
  `MT6797_A72_BLOCK_A34_BOOTSTRAP` cleared;
- health: `MT6797_A72_OWNER_AVAILABLE`;
- phase: `MT6797_A72_PHASE_IDLE`;
- members: zero;
- provider: `MT6797_A72_PROVIDER_NONE` with empty identity;
- bootstrap and membership validity: one;
- attempts available: `MT6797_A72_ATTEMPT_MASK`;
- attempts consumed and retired mask: zero;
- next generation: one;
- next cookie: `0xa7200001`; and
- every active, retired, fault, controller, and controller-cookie field: zero.

The final callback verifies that all fields intended to remain zero are still
zero, writes the prepared scalar fields under `a72_state_lock`, and stores
`health = MT6797_A72_OWNER_AVAILABLE` last. It then returns zero. Raw-lock
release is the only subsequent action.

## Failure contract

| Condition | Result | Source callback | Owner effect |
| --- | --- | --- | --- |
| Null or malformed replay | `-EINVAL` or `-EPROTO` | zero | unchanged |
| Unknown replay applicability | `-ENODATA` | zero | unchanged |
| Already published | `-EALREADY` | zero | unchanged |
| Other non-pristine owner | `-EPERM` | zero | unchanged |
| Missing or failing source | source error | one at most | unchanged |
| Stable but non-recovered A34 input | `-EPERM` | one | unchanged |
| P30 non-pristine or claimed | `-EBUSY` | one | unchanged |
| Final owner mismatch | `-EPERM` | one | unchanged; claim released |

Every static workspace is cleared on exit. No failure consumes a membership
attempt, mints a transaction token, calls a provider, prepares P30, or reaches
PSCI.

## Required focused proof

Injected tests must cover exact success, every replay class, source absence and
failure, A34 mutation rejection, initial owner rejection, P30 claim collision,
final owner mismatch, exact destination fields, health-last instrumentation,
claim release on both callback results, and repeat-before-source rejection.

After successful injected publication, the tests must prove:

- membership preflight and validation return `-EOPNOTSUPP`;
- `mt6797_psci_cpu_boot()` remains the unconditional `-EAGAIN` body;
- CPU disable remains unconditional false;
- P30 remains pristine and unprepared; and
- all hardware, provider, and CPU request counters remain zero.
