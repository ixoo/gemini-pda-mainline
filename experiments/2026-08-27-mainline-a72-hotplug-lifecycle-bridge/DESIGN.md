# CPU8 PSCI/generic-hotplug lifecycle bridge

## Fixed ownership boundary

The bridge separates three facts that the current synchronous injected
executor represents as adjacent callbacks but Linux produces at different
ownership points:

1. the MT6797 `.cpu_boot` callback is the sole CPU_ON issuer and may report
   only PSCI acceptance;
2. arm64 owns `secondary_data`, the shared `cpu_running` completion, its
   five-second wait, and the first successful `cpu_online(8)` observation; and
3. generic CPU hotplug owns all remaining AP and controller callbacks through
   the requested `CPUHP_ONLINE` target.

The executor must therefore pause after its single accepted CPU_ON callback.
It may not wait for `cpu_running`, poll `cpu_online()`, inspect arm64-private
state, call `psci_ops.cpu_on()` directly, or continue to IPI/DCM work before
generic hotplug has completed.

This phase adds no MT6797 production registration. The existing
`mt6797_psci_cpu_boot()` veto remains unchanged, and the new arm64 operation
callbacks are unset in `mt6797_psci_ops`. The complete binder is the only later
unit allowed to attach them to an exact attempt.

## Controller handoff points

The existing one-shot controller gains an internal lifecycle state. Entry
validation and the pre-isolation/post-isolation rules remain unchanged.

`mt6797_a72_transition_begin()` consumes the one-shot and executes exactly the
watchdog, P27, provider, isolation, SRAM, and CPU_ON stages. A successful return
means only that the one injected CPU_ON callback returned zero. It leaves the
controller in `CPU_ON_ACCEPTED`, keeps the result nonterminal, and performs no
online, IPI, or DCM callback.

The first generic handoff is immediately after selected arm64
`__cpu_up()==0`, while the controller still owns the CPU-up operation. A new
optional `cpu_operations.cpu_up_secondary_complete` callback receives CPU8 at
that point. The later binder will use it to call
`mt6797_a72_transition_secondary_complete()`, which accepts only the paused
controller, CPU8 online, CPU9 offline, and one injected secondary-publication
callback. It replaces the old private ten-second wait callback; the bounded
timeout is the existing arm64 five-second completion wait.

The second handoff is after `cpuhp_up_callbacks()` has successfully completed
the requested target, before the CPU write lock is released. A new optional
`cpu_operations.cpu_up_complete` callback receives the original target. The
later binder will accept only `CPUHP_ONLINE`, then call
`mt6797_a72_transition_complete()` for one synchronous CPU8 IPI proof followed
by the already-owned DCM update. A nonzero post-CPUHP result returns to the
caller without entering generic rollback; the transition stays retained for
the armed watchdog.

Both generic hooks default to zero for every operation table that leaves them
unset. The selected arm64 configuration does not use split startup; source and
profile validation must keep that fact explicit for this first CPU8 path.

## Failure boundary

A PSCI rejection is an executor CPU_ON-stage fault. A secondary timeout or any
generic CPUHP failure after CPU_ON acceptance reaches the existing MT6797
rollback publication point before generic reverse callbacks. The complete
binder must call `mt6797_a72_transition_fail()` there before the existing P32
owner publishes and guards rollback. This bridge only supplies and tests the
one-shot terminal transition; it does not replace P32 or infer that generic
rollback restored hardware.

Failures at or after the isolation attempt retain P27/provider state and never
call CPU_OFF, retry CPU_ON, release a provider, or guess an inverse. A malformed
handoff, wrong CPU, duplicate phase, CPU8-offline observation, or CPU9-online
observation is a retained protocol fault. Once terminal, every later handoff is
rejected without another checkpoint, IPI, DCM, CPU_ON, or rollback operation.

The full-success terminal remains possible only after all 18 before/after
checkpoints, exactly one CPU_ON, one secondary completion, one IPI proof, and
one DCM update. The result continues to record zero CPU_OFF requests and zero
retries.

## Hardware-free proof

The focused KUnit suite exercises the split controller with only in-memory
callbacks. It must prove:

- exact pause after CPU_ON acceptance;
- exact resume order at secondary and full-CPUHP completion;
- unchanged pre-isolation rollback and post-isolation retention;
- failure before and after secondary completion;
- wrong CPU, online-state, duplicate, out-of-order, and terminal handoffs;
- IPI and DCM failure retention; and
- one-shot CPU_ON with no CPU_OFF, retry, private completion, PSCI, SMP call,
  MMIO, retained RAM, watchdog, regulator, or device action.

Static validation independently pins both hook placements, no-op defaults,
unset MT6797 production callbacks, the unchanged `.cpu_boot` veto, exact source
hashes, and the focused profile. QEMU runs only the injected suite with no
network. It cannot prove a physical CPU, PSCI firmware, IPI, or DCM effect.
