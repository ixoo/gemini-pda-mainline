# P30E MMU-off-visible object design

This document defines the wire contract required between the MMU-on startup
controller and the target's early MMU-off assembly. It is not a Linux C ABI,
not a firmware ABI, and not an implementation. The object must be allocated in
a reserved physical region that is present before the target is released and
cannot be reclaimed or aliased during the transaction.

## Fixed object layout

The implementation must use a fixed-width little-endian word layout. No
compiler bitfields, pointers, `bool`, implicit padding, or architecture-sized
enums are permitted. The following fields are 64-bit words in this order:

```text
0   magic
1   abi_and_size
2   boot_identity_0
3   boot_identity_1
4   boot_identity_2
5   boot_identity_3
6   operation
7   target_cpu
8   target_mpidr
9   generation
10  cookie
11  controller_state
12  target_state
13  target_sequence
14  controller_sequence
15  target_reason
16  target_effects
17  target_entry_pc
18  target_entry_sp
19  crc64
```

`magic`, ABI, size, boot identity, operation, CPU, MPIDR, generation, and
cookie are immutable after arming. `controller_state`,
`controller_sequence`, and `crc64` are controller-owned; `target_state`,
target sequence, reason, effects, and entry diagnostics are target-owned.
`controller_sequence` increments on every state publication. `crc64` covers
words 0 through 18 and is recomputed whenever the controller arms the object;
the target validates the immutable header and token, but does not rewrite
them.

The controller passes only the object's physical address and exact expected
token to assembly. The target never dereferences a normal C virtual pointer.
The physical address must be range-checked, naturally aligned, and tied to the
same boot identity before release.

## States and legal transitions

```text
EMPTY -> ARMED -> TARGET_CLAIMED -> TARGET_PUBLISHED
                         |                |
                         +-> FAILED ------+
                         +-> PARKED
                         +-> PANICKED
```

The controller alone publishes `EMPTY` and `ARMED`. The target alone claims a
valid `ARMED` object and publishes `TARGET_CLAIMED`, then exactly one terminal
outcome. The controller consumes `TARGET_PUBLISHED` only after an explicit
cache-invalidate/readback and exact token/sequence check. It may then expose
the result to the P30 C model; P14/P15 remains forbidden until the complete
P30 publication and online checks succeed.

Any state outside this set, a backwards sequence, a duplicate terminal, or a
terminal after a different terminal is P30U. A target that cannot validate the
object publishes `FAILED` with a reason if the object is writable; otherwise
it enters the reviewed bare-STUCK/reset branch without claiming success.

## Cache and barrier order

The controller must:

1. write the immutable header and zero target-owned words;
2. compute and store `crc64`;
3. clean the complete object range to the point of coherency;
4. execute the required full-system data barrier; and
5. publish `ARMED` with release ordering before the first CPU_ON.

The target must acquire the object after its entry synchronization, validate
the header/CRC/token, and issue the architecture-required instruction/data
barriers before using any field. Before publishing a target result it writes
the reason/effects/diagnostics, increments `target_sequence`, cleans the whole
object range to the point of coherency, executes the full-system barrier, and
publishes the terminal state with release ordering. The controller must issue
the matching barrier and invalidate/read back the complete range before
accepting the result. A cache flush of only the state word is insufficient.

The exact arm64 instructions and linker section are implementation review
items; a patch must record them and prove that the selected source's MMU-off
entry actually observes the same physical bytes.

## Failure and stale-object policy

The target enters P30U for a bad magic/ABI/size, CRC, boot identity, operation,
CPU, MPIDR, generation, cookie, physical range, sequence, or state. It must
not call P14/P15, set Linux online state, or infer an inverse. The controller
enters quarantine for an unreadable object, a timeout with unproven CPU_ON,
non-return, stale generation, mismatched terminal, or failed readback. A
quarantine is first-cause and reset-only.

The object is reinitialized only by the known-good platform/external-reset
bootstrap after the previous generation is no longer live. Ordinary Linux
reboot, a caller acknowledgment, or a second CPU request cannot clear it.

## Ownership exit

P30E is implementation-eligible only when the exact linker placement, physical
address handoff, assembly entry, cache maintenance, barriers, failure store,
controller readback, and P14/P15 ordering are all source-reviewed and tested
against the P30 model. This contract does not relax the provider, A41, P24,
P32, A26, or A14 blockers.
