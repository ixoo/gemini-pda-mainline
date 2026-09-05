# INIT credit debit and extra-read integration

[`hif_init_bounds.h`](src/hif_init_bounds.h) supplies two concrete bounded
pieces for the existing protocol and PIO primitive: boot-INIT page debit and
the selected CMD_RESULT receive span. It does not read counters or replenish
credits. [Six pinned source identities](results/init-bounds-sources.json)
reuse Planet `c5b0be85017ad0c599725e8273842efdbecdd88a` and selected gen3.
No backend, retained-input or runtime configuration access was performed.
Build-selection facts below are source macro selections, not a newly
verified running binary or live configuration.

## Boot seed and actual page cost

`nicTxInitResetResource` clears pending/pre-used/available accounting and
initializes the INIT ledger. `nic_tx.h` selects eight maximum-frame buffers
for TC0 **and eight for TC4**, zero for the other four classes. A maximum
frame uses `ceil((28 + 0 + 1532) / 128) = 13` pages; therefore TC0 starts
with 104 pages, not eight pages. This seed belongs only to the matching
fresh INIT phase, not an arbitrary live session or software retry.

INIT CONFIG/START constructors acquire TC0 with
`nicTxGetPageCount(record_length, TRUE)`. TRUE means the frame already
includes its descriptor/header, so cost is `ceil(record_length / 128)`.
The 20-byte CONFIG and 16-byte START each cost one page. Do not add the
normal long descriptor again, use bus block count, or charge the RX extra
word against TX. Other INIT/PDA records still require their own framing
admission; accepting an arithmetic length is not permission to submit it.

`mt6797_init_debit` accepts a caller-owned free-page value in 0–104 and
nonzero frame length up to 104 pages. It refuses malformed state, zero or
overflow lengths and insufficient credit without changing state. On success
it subtracts the rounded cost. The function has no seeding/refund operation.
The caller initializes 104 only after independently establishing the fresh
phase and serializes every debit with submission. Debit before dispatch;
after uncertain submission the debit remains consumed and the session must
not be reused. A protocol ACK is not a credit refund. Exhaustion returns
`-ENOSPC` rather than manufacturing replacement credit.

## Returned counts: why no scalar refund is implemented

`HAL_READ_TX_RELEASED_COUNT` reads eight WTQCR words into 16 halfword counts.
On the selected little-endian path, TC0 maps to AC0 at index 0 (WTQCR0 low
half); FFA is index 14 (WTQCR7 low half); CPU/TC4 is index 15 (high half).
These are page-accounting inputs, despite packet-oriented enum comments.
`nicTxCalculateResource` accumulates AC/CPU done counts and a separate FFA
available-page count, then distributes the available pages among classes.
One snapshot's AC0 value alone is not a free-page increment.

The source loads `ExtraTxDone` with default **1**, through a runtime config
lookup in `wlan_lib.c:5476`. In that mode, pending completion counts first
repay pre-used counts. Remaining FFA can be distributed against outstanding
used pages before their per-class done counts arrive, recording pre-used
debt to avoid crediting the later completion twice. With the option off,
FFA and pending done counts are still reconciled; scarcity is distributed
round-robin. TC4 has its own INIT allocation, so the source cannot be
reduced to “all FFA belongs to TC0” without exclusive-use evidence.

This establishes the source interpretation, not a complete live acquisition
contract. The exact selected runtime `ExtraTxDone` value, freshness/read-clear
semantics and exclusive consumption of returned counters have not been
established here. Replaying a snapshot would add it twice in this additive
model. Those facts plus the complete multi-class state are needed before
automatic replenishment is connected. No source default is silently treated
as an observed selector, and no partial TC0 refund implementation is offered.
The finite debit-only component can support bounded work within a proven
initial allocation; sustained traffic needs the returned-credit path.

## Exact selected RX span and connection to the primitive

`config.h` selects `CFG_ENABLE_READ_EXTRA_4_BYTES=1` and
`CFG_SDIO_RX_AGG=1`. `nicRxWaitResponse` reads WRPLR, checks reported logical
length against the response buffer, reads `ALIGN_4(length + 4)` into its
coalescing buffer, then copies only `length` bytes to the response buffer.
For the selected 28-byte MT6797 CMD_RESULT, the bus span is **32 bytes**.
The extra bytes remain uninterpreted; they are not another event or a
required zero field.

`mt6797_init_result_span` is deliberately limited to this response: reported
zero returns `-EAGAIN` for a bounded caller wait, any nonzero length other
than 28 returns `-EMSGSIZE`, and staging below 32 bytes is refused. It reuses
the encoder for PIO read WRDR0 and returns word `0x1000a020`, span 32. It
does not truncate a full-width input into a valid-looking 16-bit count.

Concrete connection: extract WRPLR's low 16-bit port-0 length; validate it
with this helper; invoke `mt6797_hif_pio_transfer` with read port `0x50`,
payload length **32**, and staging capacity at least 32. After a successful
read, pass exactly the first **28** bytes to the existing CMD_RESULT/session
validator with the independently expected sequence. Passing 28 to the PIO
primitive would under-read this selected extra-word policy. Do not expose
the four extra bytes as protocol payload or perform a second FIFO read.
Unexpected length poisons the pending transaction; it is not permission to
drain, retry or reset. The session deadline/ownership guards remain external.

## Validation and remaining applicability

The [fixture](src/hif_init_bounds_test.c) checks page boundaries 127/128/129,
exact 104-page exhaustion, malformed page state, insufficient credit,
zero/SIZE_MAX lengths and unchanged failed debits. It tests every 16-bit
reported length, all undersized staging capacities, oversized full-width
input and NULL outputs; failure outputs are cleared. Strict C11 warnings
and address/undefined sanitizers pass. No kernel branch or real adapter is
compiled. Source framing/policy is explicit; exact runtime applicability,
owner/credit acquisition, stale-event exclusion and recovery remain gates
for hardware use, not blockers to these original pure components.
