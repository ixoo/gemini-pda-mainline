# CPU8 single-request active-transition design

## Entry and trigger

The candidate boots with CPU8 and CPU9 offline and performs no CPU request by
itself. After USB/netcat serviceability, the host must verify the exact
candidate, kernel release, changed boot ID, CPU topology, and the complete
platform/provider/protected-clock prefix. Only then may it write one exact
candidate-specific token to a root-only, write-only, one-shot trigger.

The same netcat session starts a bounded live kernel-log stream before the
write, so every checkpoint can reach the host before a later operation can
stall. No remote file is created. Wrong and repeated tokens fail before a
hardware operation.

## Ordered effect contract

The executor consumes its one-shot before mutation, takes exclusive transition
ownership, and arms a 15-second hardware watchdog. Each effect has a `before`
checkpoint, exact operation, readback, and `after` checkpoint:

1. P27: exact MP2 reset release, B-PLL ordering read, and PWRAP assert;
2. provider: exact DA921x Buck-B `0x00 -> 0x01`, 1 ms settle, full readback,
   and generation-bound handle;
3. P28: exact external-isolation `0x00000002 -> 0x00000000`, PWRAP deassert,
   240 microsecond guard, 1.1 V SRAM-LDO call, then stable selector `0x8fb`
   and nonzero 16-bit calibration;
4. CPU request: exactly one standard PSCI `CPU_ON` for CPU8/MPIDR `0x200` and
   physical `secondary_entry`;
5. completion: the generic CPU-up path gets at most 10 seconds for secondary
   completion; and
6. post-online: CPU8 online, CPU9 offline, one synchronous CPU8 IPI/accounting
   callback, then exact MP2 DCM toggle/readback `0x0f -> 0x0d` under its owner.

The recovery timeout is longer than the CPU completion timeout, leaving a
bounded terminal-evidence window. The watchdog is deliberately not canceled,
including after success, because CPU8-off is not yet an admitted inverse.

## Failure domains

Before a successful isolation clear, unwind only state proven owned by this
attempt: release the exact provider handle, restore the exact MP2 reset word,
and deassert PWRAP if its ownership is still exact. Any mismatch becomes
terminal fault-retain; there is no retry.

At or after the isolation attempt, do not set isolation, disable Buck B,
restore MP2 reset, call an SRAM-disable service, issue CPU_OFF, or retry
CPU_ON. PWRAP may be deasserted only if the reset owner proves this attempt
still holds it. Record the last stage and wait for hardware recovery.

## Evidence contract

The host-visible record includes candidate identity, attempt number, stage,
phase, errno, isolation-crossed state, CPU request count, CPU8/CPU9 online
state, rollback mask, retained-power mask, and watchdog identity. There is one
terminal class: prestate rejection, exact pre-isolation rollback,
pre-isolation rollback fault, post-isolation retain, or CPU8-online proof.

At most two compact retained records may be used by the later candidate: one
before the first mutation and one terminal record. Live checkpoint streaming
is the primary per-stage path. Returned Gemian must show a changed boot ID,
the exact unchanged boot2 checksum, and any retained/pstore evidence available;
screen color or reset timing is never attribution.

## Exclusions

CPU9, CPU_OFF, cpufreq/OPP changes, load stress, suspend, a general userspace
control API, automatic retry, native VM build, and production A34/membership
publication are outside this first request.
