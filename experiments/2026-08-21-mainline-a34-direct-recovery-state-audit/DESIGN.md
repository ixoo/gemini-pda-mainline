# Direct A34 recovery-state decision

## Accepted reference, absent current proof

The exact historical first-cycle record establishes one coherent reference
tuple because its pre-CPU8 and post-off snapshots are byte-identical. It is a
reference for exact comparisons, not a value source for another boot.

Current A34 authority requires all of the following in one immutable record:

- full DA921x control/status/Buck B state;
- complete A72-relevant SPM status and control state;
- PWRAP reset and MP2 DCM state;
- protected clock, secure SRAM/B-PLL/control, and A72 CCI state;
- physical and generic CPU8/CPU9 state;
- applicable primary-BL31 replay-zero proof; and
- the complete empty Linux membership/provider/P30/attempt tuple.

Each hardware member must be read fresh through its owner, have an exact
failure return, and remain serialized against writers through publication.
Two values sampled at unrelated probe times cannot be combined into this
record.

## Rejected substitutions

The following are not direct recovery-state authority:

- the caller-populated A36 prestate;
- the existing probe-time `mt6797-a72-power` cache;
- `pwrap_reset_acquired=1` without reset state;
- generic `CPUHP_OFFLINE` without physical power/status state;
- CCI PLL frequency without A72 snoop/DVM port state;
- a secure-call success code without fixed-register readback;
- enabling currently disabled DT nodes without owner composition; or
- matching a subset of the historical tuple.

## Selected boundary

The next implementation-independent audit is the exact MT6797 A72 CCI and
platform-state ownership boundary. It must identify the source-backed CCI port
and status registers, safe read path, SPM field meanings, TOPRGU bit-state
access, and serialization constraints. No magic physical mapping or CCI write
is admitted by this result.

## Explicit exclusions

This decision adds no A34 ABI change, observer implementation, DT enablement,
hardware read, SMC, I2C transaction, lifecycle publication, provider action,
P27/P28 effect, P30 arm, PSCI call, CPU veto change, build, boot image, device
write, or CPU8 request.
