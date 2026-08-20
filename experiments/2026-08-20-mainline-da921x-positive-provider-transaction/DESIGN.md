# Positive DA921x provider transaction design

This source-only Gate-7 step replaces neither CPU veto and creates no device
candidate. It adds a default-off positive implementation behind the private
MT6797 A72 provider callback seam.

## Lifecycle

Acquire and release are separate synchronous I2C transactions. Each holds the
root-adapter lock for its complete operation and temporarily forces adapter
retries to zero. No adapter lock spans the lifetime of the returned handle;
that would retain a bus lock across the later CPU transaction and would make
lock ownership depend on callback-thread identity.

Acquire accepts only the exact CPU8 request ABI with nonzero, non-sentinel
transaction generation and cookie. It reads the five full-byte prestate
registers, requires `CONTROL_A=0x7b`, `BUCKB_CONT=0x00`, and both selectors at
`0x46`, then writes `[0x5e, 0x01]`, waits 1 ms, and reads the same five-register
snapshot. Success requires the complete owned state to match with only
`BUCKB_CONT` changed to `0x01`. `STATUS_B` is retained as an observation, not a
mutation gate. The exact request generation and cookie become the held handle.

Release accepts only that handle and only while the state is held. It first
re-reads and proves the exact held state, writes `[0x5e, 0x00]`, then re-reads
the complete snapshot and requires restoration of every owned prestate byte.
`STATUS_B` remains record-only.

Each successful operation has eleven transfers: five reads, one write, and
five reads. The already implemented MT6797 transaction window independently
checks stopped-firmware state at the entry and exit of every physical transfer.

## Failure ownership

The state machine stops at the first transport error, short result, or owned-
state mismatch. It never retries and never makes a speculative inverse write.
Before the enable write, a failure is `failed-no-mutation`. At or after either
write, an incomplete proof is terminal `fault-retained-reset-only`, even when
the likely hardware value appears benign. This deliberately prefers a known
recovery boundary over guessing whether a failed write took effect.

The inverse is attempted only by release after an exact generation-bound
handle and an exact held-state preflight. A second acquire is forbidden even
after successful release; each provider instance therefore represents one
bounded experiment transaction.

## Isolation

The implementation does not access `PAGE_CON`, write either selector, expose a
regulator consumer, run P28, request CPU_ON, or implement CPU_OFF. The new
configuration is default-off. Its first validation uses an unregistered fake
adapter only; device execution requires a later, separate review.
