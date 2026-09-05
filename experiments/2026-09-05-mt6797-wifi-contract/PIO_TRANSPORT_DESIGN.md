# Minimal PIO transport: separate FIFO submission from firmware completion

Credit correction: [CONFIG uses TC4; START uses TC0](INIT_CREDIT_CORRECTION.md).
Earlier shared-credit/TC0-CONFIG claims below are superseded; historical
validation receipts are preserved and do not validate the corrected pools.

The earlier [PIO assessment](PIO_COMPLETION.md) overreached by treating a
missing per-access latency bound as a blanket implementation blocker. A
counted FIFO loop is a normal transport primitive. The known HIF accesses
support designing that primitive now; firmware success, credits, ownership
and safe failure containment remain separate requirements. No new hardware
observation, MMIO implementation or runtime admission is claimed here.

## Upstream comparison and correction

Linux's device-I/O documentation specifies ordered MMIO accessors and
distinguishes ordering from posted-write completion. A needed flush must use
a suitable same-device read; it is not a fabricated device-done bit.
Repeated FIFO accessors have different byte-swap semantics from scalar
accessors. Neither API supplies a software cancellation facility for an
individual bus transaction.
[Upstream documentation](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/Documentation/driver-api/device-io.rst).

At the same pin, `smsc911x_tx_writefifo` and `smsc911x_rx_readfifo` use
counted accesses or `iowrite32_rep`/`ioread32_rep` under a lock. RX status
availability and TX free-space/queue accounting are handled outside those
loops; packet status is a different concern. This is an upstream design
example, not a compatible driver or a source of MT6797 register meanings.
[FIFO primitives](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/net/ethernet/smsc/smsc911x.c#L234).

The prior observations remain: vendor PIO returns without a separate done
poll, RX can report success from a no-read guard, and the response timer
cannot interrupt a stuck access. The corrected implication is to implement
honest submission/error semantics and timed protocol waits, not to demand
an undocumented PIO busy register. Ordinary platform MMIO accessibility is
an integration assumption enforced through power/resource ownership, not a
new requirement to prove a hard timeout for every instruction.

## Exact HIF admission and completion layers

All vendor references use the existing Planet pin recorded in
[the new source ledger](results/pio-reassessment-sources.json), alongside
[the original PIO sources](results/pio-sources.json).

| Layer | Selected source evidence | Minimal transport responsibility |
| --- | --- | --- |
| Power and ownership | `nicpmSetDriverOwn` reads WHLPCR `0x4`, requests ownership with bit 9, and observes driver ownership at bit 8. Its polling has a 2048 ms source deadline and approximately 1 ms sleeps. Port helpers reject fatal/reset/firmware-own state, although RX's true return is misleading. | Hold the existing provider/lifetime owner; serialize acquisition and prevent concurrent firmware-own release/reset. Observe ownership, propagate refusal as an error, and never claim bytes were read from a skipped operation. No normal FIFO access while firmware-owned. |
| TX admission | `nicTxAcquireResource` debits TC page counts under a lock. CONFIG uses TC4 and START uses TC0, each with `nicTxGetPageCount(..., TRUE)`; pages are 128 bytes. Startup resets the source ledger to eight maximum-frame buffers for TC0. `nicTxPollingResource` reads returned counts with 256 attempts and 50 ms delays. | Debit sufficient pages before setup. Establish the boot-phase ledger and release-counter mapping from the matching firmware contract; do not equate an ACK with returned credit. One outer deadline must cover repeated acquire/poll attempts. |
| RX availability | `nicRxWaitResponse` polls WRPLR `0x90`; low/high halves describe port 0/1. It rejects logical length beyond capacity before reading. Optional extra-four-byte mode changes the transfer span. | Wait for nonzero length under a session deadline, validate logical and padded capacities separately, then read exactly the selected transfer span. Keep the reported logical length for the decoder; do not feed padding as another record. |
| FIFO submission | Existing setup at HIF `+0`, ordered data accesses at `+0x1000`, and setup/data serialization are source-supported. | Use the existing encoder with PIO-only policy and a finite word loop. Return “submitted/read” at this layer, not firmware success. No per-word ready/busy bit is required by the audited path. |
| Command completion | DOWNLOAD_CONFIG consumes a matching CMD_RESULT with success status; WIFI_START returns after TX and startup separately polls WCIR WLAN_READY. | Reuse the exact INIT decoder/session boundary for CONFIG. Use a bounded readiness wait for START; never wait for an invented START ACK. WLAN_READY after START is not a prerequisite for sending INIT commands. |

The source credit seed is an initialization convention, not permission to
create credits in an arbitrary live session. Page cost for INIT uses frame
length directly; it must not be replaced by the encoded bus block count.
The source's repeated poll/reacquire structure is not a model for an
unbounded retry loop. TC release-counter interpretation and initialization
phase must be reviewed before sustained command submission is admitted.

## Concrete minimal implementation boundary

1. A single sleeping transaction owner holds the powered HIF reference and
   firmware-session identity through admission, submission and expected reply.
   Ownership polling precedes data access. IRQ work cannot change command
   setup or consume this response; use a short setup/data lock with a reviewed
   IRQ masking convention, not a spinlock held across sleeps.
2. Validate one command and reserve its credits. Allocate/prepare bounded,
   initialized staging storage before taking the short lock. Restrict initial
   CONFIG/START commands to their already-modeled 20/16-byte forms. Do not
   generalize this design into firmware loading or arbitrary packet traffic.
3. Under the setup/data lock, recheck software reset/owner generation, encode
   fixed-port PIO, write setup and transfer the finite word count. Scalar
   `writel(get_unaligned_le32(...))` and matching `put_unaligned_le32(readl(...))`
   express the little-endian byte stream without alignment assumptions. A
   later repeated-access optimization needs its own endian/ordering review.
4. Keep resources held while awaiting the appropriate protocol condition.
   Ordered same-device status polling is part of that path. Do not add a
   speculative read of the data FIFO to flush writes. Before any separate
   unlock/power-release boundary that needs completion, identify a safe
   non-destructive register/read ordering path; a barrier alone is not a
   posted-write receipt.
5. On response timeout, length/sequence/status failure or ownership loss,
   poison the session and stop new submissions. Do not retry a possibly
   consumed command, refund uncertain credits, drain unknown data or reset
   the shared island. Report the error while the owner retains the lifecycle
   responsibility. Recovery to a new usable session is a separate contract.

## Remaining decision-changing facts

The transport algorithm no longer waits for a hypothetical PIO-done bit or
per-`readl` timeout. The real remaining integration facts are: the provider's
safe powered lifetime and ownership exclusion; exact INIT credit seed and
returned-counter accounting for the selected firmware phase; selected RX
extra-read/length policy; and the safe status-read/IRQ ordering across the
shared setup window. WASR names firmware-own invalid access and RX underflow/
TX overflow bits, but this audit does not establish clear/read side effects
or a recovery sequence. Those names must not become automatic polling or
reset behavior without that evidence.

No partial-transfer recovery is invented. Its absence prevents transparent
retry/restart, not a finite primitive that fails the session and leaves
recovery to the owner. A production removable driver still needs a reviewed
teardown path; retaining the owner on uncertainty cannot be disguised as
successful release. Full Wi-Fi usability remains the user-facing requirement.
DMA is a performance option if a functioning PIO path meets that requirement;
translation proof is required before enabling DMA, not before usable Wi-Fi
through PIO. This reassessment adds no device/backend action.
