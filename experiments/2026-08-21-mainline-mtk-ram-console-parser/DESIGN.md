# MediaTek retained ram-console parser

## Claim boundary

The patch owns only a pure transformation:

```text
caller-owned byte buffer -> strict wire validation -> raw status snapshot
```

It neither locates nor maps physical memory. It does not classify the returned
word and has no production A34 caller.

## Strict prefix validation

The parser implements the exact checks frozen by the authority audit:

- 64-byte little-endian header and signature `0x43474244`;
- header total size equal to the caller-supplied buffer size;
- current preloader at byte 64 with a record of at least four bytes;
- overflow-safe 64-byte alignment and exact chaining of the current and prior
  preloader records;
- exact 64-byte pinned-LK records with overflow-safe current/prior chaining;
- exact Linux offset after both LK records; and
- console offset within the buffer and not before the Linux offset.

On every error the output is invalid and zero. No fixed-offset legacy fallback
is accepted.

## Snapshot contract

The public output contains only the complete raw 32-bit current-preloader
status and explicit validity. Every bit pattern, including zero and unknown
bits, round-trips without interpretation.

## Hardware-free proof

Eight focused KUnit cases cover invalid arguments/output clearing, truncated
header, bad signature, mismatched total size, corrupt/overflowing preloader
layout, corrupt LK/Linux/console layout, exact nontrivial value, and every
individual bit. Fixtures are ordinary memory and invoke no platform service.

## Explicit exclusions

The patch adds no reserved-memory lookup, physical mapping, `no-map` override,
MMIO, watchdog operation, reset classifier, boot-reason reader, A34 evaluator
call, lifecycle publication, provider action, I2C operation, P27/P28 effect,
P30 arm, firmware call, PSCI call, CPU_ON, CPU_OFF, boot-veto change, boot
candidate, boot2 write, or device action.
