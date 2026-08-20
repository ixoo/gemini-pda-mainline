# Gate-6 same-value-write implementation design

## Logical patches

1. `0290` upgrades only the default-off MT6797 entry ledger to v2, captures a
   second byte only for length-two messages, and exposes a read-only exact
   pointer-read-prefix verifier. The verifier asserts that the root adapter
   lock is held and performs no transfer.
2. `0291` adds the one-shot DA921x operation. One device mutex admits the exact
   token, one root lock covers prefix verification and all actions, adapter
   retries remain zero inside the window, and every exit restores them.
3. `0292` adds hardware-free KUnit coverage through the same production
   sequence helper. It registers no adapter/client and contains no MMIO path.

The normal archive identity remains explicitly synthetic and non-certifying,
with no `Signed-off-by`. These experiment patches are not submission-ready.

## Production sequence

The fixed sequence is the 12-action contract already frozen by the
[pre-write review](../2026-08-19-mainline-da921x-same-value-write-preflight-review/DESIGN.md).
The helper accepts transfer and delay operations so the exact control flow is
testable. The only production binding is:

```text
ledger verifier = mtk_i2c_gemini_verify_read_ledger(exact 20 entries)
transfer         = __i2c_transfer
delay            = usleep_range
```

The helper itself takes and releases the root lock. It does not call
`i2c_transfer()`. Its single write helper owns the only payload literal
`[0xda, 0x46]` and is called once in the action flow.

## Failure representation

Wrong tokens leave the state idle. A valid token with an invalid provider or
CPU baseline consumes the one shot and enters `failed-no-write` before the root
lock or any transfer. A ledger-prefix refusal also enters `failed-no-write`
with one lock/unlock and zero action transfers.

Transfer errors and byte mismatches at actions 1--5 enter `failed-no-write`.
Actions 6--12 enter `faulted-no-further-i2c`, record one write attempt, and
perform no diagnostic, retry, or inverse transfer after the failing action.
The partial result remains readable through sysfs.

## Test boundary

The six cases cover:

- exact 12-action success, register order, both write bytes, one lock/unlock,
  delayed-readback timing, zero retries during every transfer, and restoration;
- wrong-token, precondition, and repeated-request refusal;
- under-lock ledger refusal with zero transfers;
- each of the 12 transfer-error ordinals;
- each of the 11 read-value mismatch ordinals; and
- invalid execution state with no lock or transfer.

These are compiled tests only after the patches are generated, reviewed,
tracked, and selected by a focused manifest profile. Passing them cannot prove
physical DA921x acceptance or authorize a device attempt.
