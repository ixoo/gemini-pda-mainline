# Gate-6 B2 hardware-free transport design

## Decision boundary

B2 closes only if a fetched Buildbox `Image` executes a production-coupled
KUnit suite under isolated arm64 QEMU with every required case passing. No
Gemini boot or physical I2C transaction belongs to this gate.
No Gemini boot is permitted anywhere in the B2 procedure.

The suite uses this in-memory sentinel message:

```text
fake adapter address: 0x2a
messages:             1
flags:                0 (write)
length:               2
payload:              [0xa5, 0x5a]
```

Address `0x2a` and the sentinel payload deliberately avoid either DA921x
address and the proposed future register/value pair. They are fixture data,
not a bus request.

## Production-path coupling

The kernel change must factor helpers actually called by the MT6797 iDVFS
production path. The helpers must cover:

1. one-message short-write planning: operation, slave address, FIFO/DMA
   selection, transfer length, transaction count, and ordered FIFO bytes;
2. exact controller completion classification; and
3. final transport-versus-lease result precedence.

The KUnit configuration may add an in-memory DATA_PORT sink or equivalent
test seam, but runtime configurations must not contain the hook or suite. A
test-only copy of the algorithm does not satisfy the contract.

## Exact programmed shape

For the sentinel message, the production helper and in-memory sink must prove:

```text
operation=I2C_MASTER_WR
slave_addr=0x54
use_dma=0
control_dma_en=0
control_dir_change=0
transfer_len=2
transac_len=1
fifo_write_count=2
fifo_write_0=0xa5
fifo_write_1=0x5a
start_writes=0
physical_adapter_registrations=0
```

The helper must reject a null buffer, zero length, read flag, message count
other than one, and lengths other than two for the focused witness. Those
rejections constrain the witness API; they do not remove the controller's
existing general read or combined-read support.

## Completion classes

Only a nonzero wait result with IRQ state exactly `I2C_TRANSAC_COMP` is a
controller success. The suite must exercise these outcomes:

| Input | Controller result |
| --- | --- |
| exact completion | `0` |
| arbitration loss | `-EAGAIN` |
| wait timeout | `-ETIMEDOUT` |
| ACK or high-speed NACK | `-ENXIO` |
| completion plus any error bit | error, never success |
| nonzero unexpected IRQ state | `-EIO` |
| zero IRQ state after wake | `-EIO` |

For the one-message adapter call, controller result `0` becomes final result
`1`. No error becomes a positive message count.

## No-retry contract

The fixture starts with the MT6797 adapter's normal retry count of one. The
production one-shot helper itself must:

1. acquire one `I2C_LOCK_ROOT_ADAPTER` lock;
2. record `retries_before = 1`;
3. set `retries_during = 0`;
4. invoke the injected/fake transfer callback once while that lock is held;
5. preserve the callback's exact result;
6. restore `retries_after = 1` on success and every failure; and
7. release that same root-adapter lock exactly once.

An `-EAGAIN` fixture must still observe exactly one callback. No second
message, inverse, repair, or compensating call is permitted.

## Lease-result precedence

The final result helper must obey:

```text
transport >= 0 and lease_exit < 0  -> lease_exit
transport < 0  and lease_exit == 0 -> transport
transport < 0  and lease_exit < 0  -> transport
transport >= 0 and lease_exit == 0 -> transport
```

The transaction-window owner records its own sticky exit fault. Preserving an
already-negative transport result avoids hiding the first failed operation;
replacing a nonnegative result prevents a failed exit gate from being reported
as success. The entry ledger must finish once with this final result.

## Required KUnit cases

The suite must contain, execute, and pass at least these cases:

1. exact two-byte FIFO plan and ordered sentinel writes;
2. focused-witness malformed-message refusals;
3. exact completion to one-message success;
4. timeout classification;
5. ACK/NACK classification;
6. arbitration-loss classification;
7. unexpected and mixed IRQ-state refusal;
8. `-EAGAIN` with one root lock, exactly one fake callback, retry restoration,
   and one root unlock;
9. success with root-lock and retry restoration;
10. ordinary failure with root-lock and retry restoration;
11. negative lease exit overriding positive message count;
12. negative transport result retaining precedence over lease failure.

Zero skipped cases are allowed.

## Prohibited effects

The patch, profile, and test must add none of the following:

- a sysfs/debugfs/procfs trigger, module parameter, ioctl, DT property, or
  userspace transfer path;
- a physical adapter/client registration or MMIO mapping in the suite;
- `0x68`, `0x69`, `[0xda, 0x46]`, PAGE_CON, regulator setter/consumer, or rail
  state operation in executable test code;
- a retry, second write, rollback write, START write, DMA start, firmware call,
  CPU8/CPU9 request, boot image, or device action; or
- KUnit symbols/options in any future device-runtime profile.

## Exit criteria

B2 remains open until all of these exist for the same clean pushed commit:

- canonical patch order and manifest-profile invariants pass;
- source and mutation validators prove production coupling and prohibited
  effects;
- focused checkpatch has no new actionable finding;
- the focused Buildbox profile applies, compiles, links, and validates its
  package;
- the fetched `Image` and configuration identities are recorded; and
- isolated arm64 QEMU reports every required KUnit case passed, with zero
  failure and zero skip.

All criteria are satisfied by the exact retained-log classification in
[`results/qemu-attempt-1-success-20260819.txt`](results/qemu-attempt-1-success-20260819.txt),
so B2 is closed for the named repository commit and package.

This closes only the software transport blocker. It does not authorize the
bounded no-op write or admit CPU8/CPU9.
