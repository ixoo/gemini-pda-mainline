# BTIF transfer owner: source limits and ordering

This review follows [full-STP frame collection](FULL_STP_STREAM.md). It resolves
which selected source behavior can inform the future transfer owner and which
behavior must be replaced. It does not integrate a kernel caller or admit a
mode switch, TX interrupt, firmware transfer or calibration.

## Selected interrupt path

The pinned `btif_plat.c` selects its software-FIFO/TX-interrupt implementation.
`hal_btif_irq_handler` repeatedly invokes RX drain while IIR indicates RX, then
services TX. The inner drain uses a 256-byte temporary buffer but resets its
local byte count after each full-buffer callback and continues draining. Neither
that buffer nor the outer loop imposes a finite total RX budget. Continuous RX
can prevent reaching TX service in that handler. A larger command path must
not inherit this order as an unbounded loop.

After delivering a full 256-byte block, the inner helper sets its local count
to zero before adding that count to its total. Consequently full blocks are
missing from its returned byte count. The callback still receives those bytes;
this is not evidence that firmware data was lost. The returned total cannot be
used as a complete transfer-accounting record. Count actual RBR reads and THR
writes in the new owner, independently from decoded event acceptance.

Source interrupt definitions select IER RX bit 0 and TX bit 1; IIR TX `0x02`
and RX/timeout mask `0x44`. The handler uses those IIR masks and checks LSR before
TX. LSR TEMT permits at most 16 writes, otherwise THRE permits at most 8 writes
at the selected threshold; otherwise it writes none. The enqueue return value,
software queue exhaustion, hardware FIFO exhaustion and peer acknowledgement
are four distinct observations.

The [register cross-check](BTIF_MANDATORY.md#register-table-cross-check-and-fixed-wire-helper)
retains the contrary IER/FIFO-clear document assignments. This review supplies
no new revision-matched hardware evidence that resolves those discrepancies.
It therefore selects source behavior for offline design only. Do not substitute
register-table bits or an IRQ-masked polling path as an unreviewed repair.

## Concrete owner design before integration

Use the existing exclusive IRQ and shared CONSYS resource owner. Keep clocks
and power held after any effect-bearing failure. Within one serialized service
step, bound RX reads, collect bytes without exposing partial events, then give
TX a service opportunity even if RX remains pending. Read fresh TX status before
each bounded batch; never carry the same observed room across several batches.
The eventual candidate must choose explicit per-IRQ, per-command and whole-run
byte/frame/IRQ/deadline limits and validate them against the complete command
list. A buffer size or hardware FIFO size alone is not a finite protocol.

Retain the immutable encoded frame until all of its bytes are submitted. Only
then commit the [sent state](FULL_STP_STATE.md); preserve buffered RX arriving
during submission and classify it after that commit. An exact accepted event
creates a four-byte host ACK obligation. Service that ACK without overwriting
an unfinished command. Do not release the next command until the peer ACK,
exact event and complete host ACK submission all satisfy the state predicate.
Partial writes, unexpected data, invalid framing and any consumed budget retire
the lifetime without retry or resetting sequence state.

Synchronize timeout retirement with IRQ progress using the same ownership lock,
disable the local source and CPU IRQ, and synchronize before releasing the IRQ.
Do not clear FIFOs to conceal outstanding bytes, reread DMA_EN casually, issue
sleep/wake commands or attempt unreviewed rollback. Preserve counters, terminal
reason and private response bytes before the reviewed retained-power recovery.
These are implementation requirements, not an executable effect protocol.

The [receipt](results/btif-transfer-review.json) pins source hashes and findings.
The installed [default query](../2026-10-03-mt6797-wmt-default-query/SESSION.md)
remains the first hardware gate. Full common initialization is not ready until
that result and the remaining firmware/calibration/resource contracts exist.
