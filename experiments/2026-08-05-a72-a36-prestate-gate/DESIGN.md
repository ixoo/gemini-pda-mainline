# A36 operation-specific prestate gate

The source-only order is:

```text
P31 attempt -> A28 generic entry -> frozen token -> A36 prestate -> P17/P18
```

The A36 input is an immutable evidence record. It is not a register accessor,
hardware-control interface, or proof that the prestate was captured by a
trusted observer. The current slice only validates the record and retains it
in the frozen transaction.

Common fields are exact READY operation, open observer window, two-argument
PSCI call shape, target MPIDR (`0x200` or `0x201`), physical
`__pa_symbol(secondary_entry)`, and matching transaction generation/cookie.

CPU8 (`0x0 -> 0x1`) requires the one-way predecessor values from the accepted
2026-08-02 design: page `0x80`, BUCKB disabled, VSEL `0x46`, SPM registers
`0x218=0x00010132` and `0x290=0x00000002`, clear PWRAP reset and MP2 DCM,
stable secure sentinels, valid protected-clock snapshot, pstore console
availability, and watchdog ownership. CPU8 and CPU9 are both offline and no
cluster/DCM publication or shared write is accepted in this record.

CPU9 (`0x1 -> 0x3`) requires CPU8 online, CPU9 offline, inherited CPU8
cluster/DCM publication, an empty shared-write set, and watchdog ownership.
CPU8-only hardware fields must be zero so a stale one-way record cannot be
reused for cluster reuse.

Any mismatch returns `-EPERM` after the P31 attempt has been consumed. The
frozen token is moved to the retired set and the owner enters terminal
`REJECTED`; a second request cannot allocate a new generation. No hardware,
provider, CPUHP, P17/P18, P30, or CPU_ON effect occurs.
