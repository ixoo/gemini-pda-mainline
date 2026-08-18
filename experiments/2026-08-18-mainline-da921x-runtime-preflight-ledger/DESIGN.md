# Runtime-triggered read-only preflight design

## Fixed parent and changed boundary

The runtime-proven parent is exact profile
`da921x-lk-clock-readonly-provider`, which reached the USB/netcat shell with 20
successful I2C6 reads and no register-data write. The stopped automatic child
added both a bounded controller ledger and ten probe-time preflight reads, then
returned before mainline USB appeared. It retained no runtime ledger and cannot
separate those changes.

This successor keeps the controller ledger but defers only the same ten reads.
It must reach the shell with the parent's exact 20-entry sequence before the
host may issue one fixed token. The token is the sole new transfer trigger.

## One-shot state machine

The driver exposes one `readonly_preflight` device attribute only in the named
runtime profile:

```text
idle --exact token + exact 2/4/0 phase counts--> running
running --ten complete reads------------------> passed
running --transport/count failure------------> failed
```

An invalid token returns before taking the mutex. A repeated exact token returns
`-EALREADY`. A mismatched provider observation or phase count moves the state to
`failed` and returns `-EPROTO` before an I2C operation. There is no retry or
state reset. The automatic-preflight and runtime-preflight Kconfig options are
mutually exclusive.

## Observation order

The host must retain two independent captures:

1. Before the trigger, capture exact kernel/DT/config identity, serviceability,
   idle trigger state, and the exact 20-entry ledger with zero overflow and
   zero writes.
2. Only after that capture classifies exactly, issue token
   `run-readonly-preflight-20260818-a` once.
3. If the shell survives, capture the passed trigger state, full five-byte
   preflight, exact 30-entry ledger, serviceability, CPUs 0--7 online, and CPUs
   8--9 offline before requesting a native reboot.
4. If transport disappears during the trigger, retain the completed pre-trigger
   capture and classify only the trigger sequence as the new failure boundary.

## Observed pre-trigger contract correction

Attempts `1b` and `1c` retained the same complete 20-entry startup ledger on
the live candidate. They showed that the two registration-phase reads are
`68:d7,68:d9`, followed by the observer reads
`68:d7,68:5d,68:d9,68:5e`. The original offline contract had inferred the
registration pair as `68:5d,68:5e`; that inference was rejected before the
token and is superseded by the retained runtime evidence.

The corrected classifier accepts the retained attempt-`1c` capture and adds a
negative mutation for the old entry-14 value. This correction changes no
kernel, DT, configuration, I2C operation, or post-trigger expectation.

## Runtime sysfs mount window

Attempt `1d` reached the token command but the initramfs's read-only sysfs mount
rejected the shell redirection before the driver store callback. The retained
state remained `idle` with zero attempts, zero preflight reads, and the same
20-entry ledger.

The corrected trigger probe follows the repository's established virtual-sysfs
window: require `/sys` read-only, install exit and signal restore traps, remount
only `/sys` writable, verify that state, issue the exact token once, restore
`/sys` read-only immediately, and verify the final state. A remount or restore
failure invalidates the capture. This creates no persistent-storage write and
does not relax the driver's one-shot, phase-accounting, or zero-register-write
guards.

## Safety and decision boundary

The trigger reuses only the already reviewed combined one-byte-pointer/one-byte
read function. It adds no regulator setter, message retry, `PAGE_CON` access,
register-data byte, consumer, firmware ownership claim, or CPU request. The
ledger remains bounded at 32 entries and records only the register pointer.

Even a complete pass can close only Gate-6 blockers B3 and B4. B1 firmware
writer exclusion and B2 native two-byte write transport remain blocking, and
no Gate-6 regulator write or CPU8/CPU9 admission follows automatically.
