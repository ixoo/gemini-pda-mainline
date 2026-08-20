# Gate-6 same-value-write implementation freeze

## Decision

The B1--B4 evidence ledger is closed and the bounded write is now eligible for
implementation and hardware-free validation. This review does not authorize a
device action.

The only permitted future register-data write remains:

```text
I2C address 0x68
one message, length 2, flags 0
payload [0xda, 0x46]
VBUCKB_B 0x46 -> 0x46
one attempt, no retry, no inverse write
```

## Closure ledger

| Blocker | Exact closure | Scope retained |
| --- | --- | --- |
| B1 firmware owner | 20 entry and 20 exit reset-control checks, all zero; no failure | Named unit and exact runtime revision only |
| B2 write transport | 12/12 production-coupled KUnit cases pass | Software/controller contract only; no physical I2C |
| B3 transfer attribution | Exact 20-entry startup sequence, zero foreign/write-shaped traffic | Named unit and exact runtime revision only |
| B4 live preflight | Two stable samples: `0x7b`, `0xc1`, `0x00`, `0x46`, `0x46` | Read-only prestate only |

The receipt paths, checksums, and required markers are machine-checked in
[`contract.json`](contract.json).

## Exact action window

The retained controller ledger has capacity 32 and exactly 20 attributable
entries before the runtime token. The complete successful action consumes the
remaining 12 entries:

| Action | Transfer | Required result | Ledger count |
| --- | --- | --- | --- |
| 1 | Read `CONTROL_A` `0x56` | `0x7b`; `V_LOCK` clear | 21 |
| 2 | Read `STATUS_B` `0x51` | `0xc1` | 22 |
| 3 | Read `BUCKB_CONT` `0x5e` | `0x00` | 23 |
| 4 | Read `VBUCKB_A` `0xd9` | `0x46` | 24 |
| 5 | Read `VBUCKB_B` `0xda` | `0x46` | 25 |
| 6 | Write `[0xda, 0x46]` | exactly one message | 26 |
| 7 | Immediate read `0xda` | `0x46` | 27 |
| 8 | After `usleep_range(10000, 11000)`, read `0xda` | `0x46` | 28 |
| 9 | Re-read `0x56` | full byte `0x7b` | 29 |
| 10 | Re-read `0x51` | full byte `0xc1` | 30 |
| 11 | Re-read `0x5e` | `0x00` | 31 |
| 12 | Re-read `0xd9` | `0x46` | 32 |

There is no spare ledger entry. An implementation that adds a transfer,
retry, inverse write, second sample, or different ordering violates the
review. Full-byte equality is required; bit-only post-comparison is
insufficient.

## Locking and transfer API

The exact token is accepted once under the DA921x device-state mutex. Refused
tokens, repeated tokens, invalid CPU/serviceability state, and host-observed
pretrigger mismatch make zero I2C transfers.

After acceptance, the kernel must:

1. take the root-adapter lock exactly once;
2. under that lock, verify the controller ledger still has the exact 20
   complete startup entries, zero overflow, and no foreign/write shape;
3. save `adapter->retries`, set it to zero, and keep it zero for the complete
   action window;
4. use `__i2c_transfer()` for each action because the root lock is already
   held;
5. stop at the first transfer error or value mismatch;
6. restore `adapter->retries` on every exit; and
7. release the root-adapter lock exactly once.

`i2c_transfer()` is forbidden inside the held root lock because it acquires an
adapter lock itself. `mtk_i2c_idvfs_transfer_once()` cannot implement this
window because it locks and unlocks around one transfer. The regulator driver
must not reach into `drivers/i2c/busses/` through a private header. The
controller may expose only the smallest read-only, default-off public
experiment interface needed to validate the ledger while the caller holds the
root lock; that interface must itself perform no transfer.

Each `__i2c_transfer()` still traverses the production MT6797 controller and
the B1 transfer lease, so success must finish with 32 entry checks, 32 exit
checks, reset control zero, and zero reset failures.

## Payload attribution

The v1 ledger records address, shape, length, the first buffer byte, result,
and completion. For a register read, the first byte is the register pointer.
For the proposed write it proves only `0xda`, not data byte `0x46`.

The successor profile must use a bounded v2 ledger that records the first two
bytes for the sole one-message length-two entry. The final classifier must
find exactly one complete write-shaped entry:

```text
address=0x68 num=1 flags=0x0000 len=2 payload=da:46 result=1 complete=1
```

Every other action entry must have the declared pointer/read shape. Overflow,
a second write shape, another address, a different data byte, or missing
completion rejects the candidate or runtime. Driver-local intent text cannot
substitute for controller attribution.

## Failure and terminal recovery

Actions 1--5 fail in `failed-no-write` with ledger counts 21--25 and zero
write attempts. Actions 6--12 fail in `faulted-no-further-i2c` with ledger
counts 26--32 and exactly one write attempt. Both a negative transfer result
and a successful transfer with the wrong byte stop at that action.

After action 6 begins, no failure path performs another I2C transfer beyond
the already predeclared next action that led to the failure. In particular,
an ambiguous write completion gets no diagnostic read, retry, or inverse
write. This preserves the first failure and avoids compounding uncertain bus
state. Because the starting and requested bytes are identical, an inverse
write cannot improve the requested state.

The kernel publishes the terminal state and partial ledger. The validated host
collector must copy immutable evidence before issuing the predeclared native
reboot. Changed-boot-ID Gemian recovery and the exact inactive boot2 checksum
remain mandatory. If the runtime shell is unavailable, the independent owner
recovery path remains available; it does not authorize an automatic second
trigger.

## Implementation and candidate gates

Implementation is eligible only as a default-off isolated experiment. Before
any physical DA921x action, the successor must pass:

- source validation of the exact token, target, sequence, lock lifetime,
  retry restoration, state machine, and forbidden operations;
- hardware-free KUnit of success, every transfer failure, every value
  mismatch, wrong/repeated/precondition refusal, and retry restoration;
- controller-ledger v2 and payload mutation coverage;
- canonical patch-series and every-profile manifest audits;
- an exact clean pushed Buildbox build—never the native VM backend;
- package, candidate, container, collector, serviceability, and predeployment
  validation; and
- sanitized evidence publication before owner selection of a candidate.

Passing these gates would create a candidate for a separately recorded single
runtime attempt. It would not admit CPU8 or CPU9. Roadmap Gate 6 remains open
until one exact physical write/readback/recovery protocol passes.
