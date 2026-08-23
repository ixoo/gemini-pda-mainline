# A72 direct-state compositor owner contract

## Split boundary

The first implementation is hardware-free. It adds a default-off direct-state
source registry and a single snapshot entry point to the existing A72
membership owner. Tests inject a source callback; no DT node or physical
reader is enabled.

A later, separately reviewed platform binding supplies the hardware-only
callback. That callback may call only:

- `mt6797_a72_provider_snapshot()`;
- `mt6797_a72_platform_state_snapshot()`;
- `mt6797_dvfsp_clock_backend_read()`; and
- `mt6797_bigidvfs_backend_read()`.

It publishes no policy decision. A34 remains a separate later consumer.

## Outer lock order

The owner entry point uses this fixed outer order:

```text
cpu_hotplug_lock (read)
  -> a72_transition_lock
    -> direct-state source registry lock
      -> hardware-only source callback
```

The callback preserves each existing owner-local order. The four physical
readers execute sequentially, never nested inside one another:

```text
platform-state local mutex
DA921x provider registry -> endpoint -> I2C root-adapter
protected-clock backend operation -> handoff state/transfer lease
BigiDVFS backend operation mutex
```

The production callback must document any refined internal order obtained
from the exact generated source. No new lock may be inserted ahead of the
CPU-hotplug or A72 transition lock.

## Publication rule

The caller record is cleared before lookup. All source and generic/Linux
fields are assembled in local storage. The owner publishes only after:

- CPU8 and CPU9 are possible and present but offline;
- both targets are at `CPUHP_OFFLINE`;
- the A72 owner is exactly `CLOSED / UNINITIALIZED` with no live controller,
  member, provider hold, attempt, retired transaction, or first fault;
- every hardware record has its exact ABI, valid bit, generation, reserved,
  and field-shape contract;
- generic possible, present, and online masks remain exact; and
- a final owner-state check still matches the initial owner state.

Every error returns a specific errno and leaves the complete caller record
all-zero. No partial record is observable.

## Source registry lifecycle

Exactly one source callback and context may be registered. Duplicate
registration returns `-EBUSY`; mismatched unregister does nothing. The
registry lock remains held through the callback, so teardown cannot release
its borrowed devices during a snapshot.

Registration is not A34 registration and cannot change the A72 owner health,
phase, blockers, attempt budget, generation, cookie, provider state, or CPU
admission hooks.

## Hardware-free proof matrix

The focused tests must cover:

1. one exact injected record accepted under the owner and hotplug locks;
2. absent and duplicate source registration;
3. every callback error with a zero destination;
4. each record ABI, validity, generation, reserved, and shape mutation;
5. CPU8-online, CPU9-online, and generic mask mutations;
6. non-closed owner, live controller, provider hold, transaction, retired
   state, attempt, and first-fault mutations;
7. callback output mutation after an initial valid fixture;
8. unregister waiting for or following a completed snapshot; and
9. no change to the owner, P30 state, provider ledger, or CPU admission result.

## Explicit exclusions

No A34 ABI revision, reset/replay classifier, `AVAILABLE / IDLE` publication,
blocker clear, provider acquire/release, register read in the first patch,
MMIO/SMC/I2C operation, retry, poll, setter, DT enablement, CPU veto change,
CPU_ON, CPU_OFF, boot image, device access, or partition write belongs to the
hardware-free boundary.
