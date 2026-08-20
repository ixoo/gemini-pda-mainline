# Gate-7 pre-P28 provider-owner integration design

## Current state

The current positive path can advance:

```text
NONE -> ACQUIRE_INFLIGHT -> HELD
```

The only clean rejection path is:

```text
NONE -> ACQUIRE_INFLIGHT -> NONE (R03 before-vote refusal)
     -> REJECTED (P29 exact P27 inverse proof)
```

A returned non-refusal error or invalid success has no owner terminal edge.
A successful `HELD` state has no CPU8-up release edge before P28. The exported
provider release callback is therefore not yet a membership-owned inverse.

## Next implementation slice

The slice remains default-off, hardware-free, and unreachable from production
CPU hotplug. It adds no lifecycle opener or caller.

### Returned acquire fault

After R01, every provider return that is neither an exact success nor the
existing exact before-vote refusal publishes:

```text
provider = FAULT_UNKNOWN
phase = FAULT
recovery = reset-only
```

The generation remains consumed. There is no retry, release guess, P29
retirement, or owner re-open. A malformed success is treated identically
because the hardware may be held without an admissible handle.

### Positive pre-P28 abort

CPU8-up gains one distinct `provider_abort` budget. It is available only after
R02 and only while:

- the transaction is exact and live in `ON_ISSUED`;
- provider state is `HELD` with the exact durable generation/cookie identity;
- P27 is complete;
- P28 is `NONE`, its budget is unconsumed, and no P28 effect started;
- CPU_ON remains unissued and its budget is unconsumed; and
- the abort budget is available.

The owner consumes the budget and publishes `RELEASE_INFLIGHT` before calling
`mt6797_a72_provider_release()` with the exact R02 handle. It accepts only a
complete returned response bound to that same handle, origin generation,
disabled Buck B, exact page/VSEL, and positive provider/rail mutation fields.
Success stores an exact positive-abort proof, clears the durable provider
identity, and returns provider state to `NONE`.

Any release error, nonreturn, short proof, mismatched handle, or malformed
response retains conservative ownership:

```text
provider = FAULT_UNKNOWN
phase = FAULT
recovery = reset-only
```

There is no second release or speculative inverse.

### P29 retirement

P29 retains its exact P27 inverse proof. It may retire only one of two mutually
exclusive provider predecessors:

- the existing R03 before-vote refusal; or
- the new exact positive pre-P28 abort proof.

Both require provider `NONE`, P28 never started, CPU_ON unissued, exact
generation/cookie identity, and zero residual P27 effect. No other positive
provider state can reach `REJECTED`.

## Hardware-free proof

The focused KUnit profile must traverse:

```text
test-only AVAILABLE seed
  -> P31/A28/A36/P17
  -> attested P27 completion
  -> production provider registry
  -> DA921x positive transaction on an unregistered fake adapter
  -> R02 HELD
  -> production provider release
  -> positive-abort proof
  -> P29 retirement
```

It must cover exact success, wrong/stale handles, duplicate abort, every
returned acquire failure class, malformed success, every returned release
failure class, malformed release success, and all P29 predecessor mutations.
The test registers no physical I2C adapter and performs no MMIO, PSCI, CPUHP,
P28, CPU_ON, or CPU_OFF action.

## Explicitly deferred boundaries

- production `CLOSED -> AVAILABLE` lifecycle bootstrap;
- current-mainline P27 hardware executor and inverse;
- physical positive DA921x execution;
- P28 isolation/PWRAP/SRAM/calibration executor;
- complete A41 READY evidence;
- P24 CPU_ON and P30/P32 production integration;
- P14/P15 membership commit and A33 final proof;
- normal CPU_OFF and A14 veto removal.
