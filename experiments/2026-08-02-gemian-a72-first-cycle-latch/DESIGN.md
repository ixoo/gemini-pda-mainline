# MT6797 A72 first-cycle latch contract

## State machine

The state is protected by the existing observer spinlock. Only retained record
events advance it.

| State | Accepted event | Next state |
| --- | --- | --- |
| `wait-up` | CPU8 `HPS_CPU_UP_BEGIN` with a nonzero transaction | `capture-up` |
| `capture-up` | matching CPU8 `HPS_CPU_UP_END`, result 0 | `wait-down` |
| `capture-up` | matching CPU8 `HPS_CPU_UP_END`, nonzero result | `frozen-up-failed` |
| `wait-down` | CPU8 `HPS_CPU_DOWN_BEGIN` with a new nonzero transaction | `capture-down` |
| `capture-down` | matching CPU8 `HPS_CPU_DOWN_END`, result 0 | `frozen-complete` |
| `capture-down` | matching CPU8 `HPS_CPU_DOWN_END`, nonzero result | `frozen-down-failed` |

Before `wait-up` accepts its event, all records are ignored. In `wait-down`,
nontransactional residual records are ignored. Any CPU9 record after capture
starts freezes as `frozen-cpu9`; an unexpected CPU8 begin/end or transaction
identity freezes as `frozen-protocol`. Capacity exhaustion freezes as
`frozen-overflow` before any retained record is overwritten.

Every frozen state is terminal until reboot. There is no userspace clear,
re-arm or write interface.

## Transaction and ordering contract

- The retained first record is the accepted CPU8 HPS-up begin.
- `up_tx` is copied from that record and all required up boundaries use it.
- `down_tx` is a distinct nonzero transaction copied from the accepted CPU8
  HPS-down begin; all required down boundaries use it.
- The successful HPS-down end is retained before the state becomes
  `frozen-complete` under the same lock. No later record can enter the ring.
- Sequence identifies append order. Causal review uses monotonic nanosecond
  timestamps because cross-CPU preparation can invert timestamp and append
  order, as the parent runtime evidence demonstrated.
- The fixed ring remains 256 records. The implementation never advances a
  wraparound head and never increments an overwritten counter in ABI v2.

## Frozen ABI

The root-only proc header becomes:

```text
abi=mt6797-a72-transition-observer-v2 state=STATE count=N overflow=0|1 up_tx=U down_tx=D
```

The state and metadata are copied into the same private point-in-time proc
snapshot as the records. `frozen-complete` is accepted only with nonzero,
distinct `up_tx` and `down_tx`, the exact begin/end boundaries, successful end
results, no CPU9 records and `overflow=0`. Failure states are evidence and must
not be promoted to a successful cycle.

## Observer-effect gate

`accepts_sampling(cpu)` is true only for CPU8 in `capture-up` or
`capture-down`. It is a read-only lock-protected query and has no control side
effect.

Pure diagnostic functions must return before hardware access when that query
is false:

- composite fixed snapshot;
- direct settled-buck snapshot;
- standalone DA9214, SPM, secure, clock and DCM snapshot entry points.

Instrumented helpers that execute real vendor mutations are different:

- SPM RMW returns false outside capture so its caller executes the original
  direct RMW fallback;
- DA9214 BUCKB enable/disable selects the original vendor calls outside
  capture;
- MP2 DCM selects the exact original vendor implementation outside capture;
- TOPRGU uses an invalid observer CPU outside capture, suppressing only added
  snapshot fields/readback while preserving its original write;
- iDVFS, SRAM-LDO, PSCI and hotplug operations always execute regardless of
  latch state; only their recorder calls become no-ops.

The latch must never use its state to skip, retry, replace or change the return
value of a real vendor operation.

## Concurrency contract

- State, transaction slots, retained count, transaction identities and terminal
  status share the existing IRQ-safe spinlock.
- The event that begins or freezes capture is appended and changes state in one
  critical section.
- A terminal-state fast check may avoid timestamp/mask preparation, but the
  locked state remains authoritative.
- A concurrent CPU9 record during capture is retained if capacity permits and
  atomically changes the state to `frozen-cpu9`.
- Proc open copies immutable metadata and records while holding the same lock;
  formatting occurs after unlock.
- No writer allocates, sleeps, prints, delays, retries, warns or panics.

## Decision table

| Runtime result | Decision |
| --- | --- |
| `frozen-complete`, exact pair validates | Reconcile the pair into Gate 4; design independent rollback observation next |
| `wait-up`, no records | Natural CPU8 up did not occur; do not generate load automatically |
| `capture-up`, `wait-down`, or `capture-down` | Incomplete natural cycle; retain evidence and do not re-arm |
| `frozen-up-failed` or `frozen-down-failed` | Preserve as failure evidence; no retry |
| `frozen-cpu9` | Separate CPU9 experiment required; infer nothing about CPU8 completion |
| `frozen-protocol` | Reject attribution and inspect concurrency/hooks |
| `frozen-overflow` or `overflow=1` | Reject capture; do not enlarge the ring without a new timing review |

No result authorizes a synthetic pulse, CPU9 request, suspend, failure
injection, writable provider or mainline A72 consumer.
