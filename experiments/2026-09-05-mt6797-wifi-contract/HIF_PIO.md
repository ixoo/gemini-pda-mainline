# Finite PIO setup/data primitive

[`hif_pio.h`](src/hif_pio.h) implements the finite access portion of
[the corrected transport design](PIO_TRANSPORT_DESIGN.md), using the
[accepted encoder](HIF_COMMAND.md). It performs one setup write at relative
offset zero followed by exactly the padded byte count divided by four
scalar accesses at relative offset `0x1000`. There are no status accesses,
waits, retries, credit operations, interrupts, resets or active probes.
Source attribution is the existing [PIO ledger](results/pio-sources.json).

The narrow I/O seam consists of a context and ordered scalar read/write
callbacks returning zero on success. A subsequent kernel adapter supplies
ordinary `readl`/`writel` access to its held mapping. Callback error reporting
supports an adapter that can report an error and deterministic host fixtures;
it does not promise Linux can catch a synchronous bus fault or interrupt a
stuck access. No real adapter or mapping is included here.

The caller must already hold powered resource lifetime, observed driver
ownership and exclusive setup/data serialization. It must exclude reset,
firmware-own release and another FIFO consumer, validate RX-reported length,
reserve TX credits and attribute the session. These are caller-held contracts,
not Boolean “proof” parameters or hidden operations performed by this helper.
The caller also owns any required interrupt masking and safe posted-write
flush at its lifecycle boundary. All validation and buffer preparation must
precede hardware dispatch; the primitive independently checks its pointers,
callbacks, encoder fields and padded capacity before its first callback.

`mt6797_hif_pio_transfer` always selects PIO-only sizing. Its buffer can be
unaligned. TX explicitly assembles little-endian words from payload bytes
and supplies zero padding through the encoded transfer span; it never reads
the caller's stale padding or modifies the TX buffer. RX stores every padded
word as little-endian bytes within validated capacity. A partial read leaves
the successfully read prefix in the buffer; a failed read callback's value
is not stored. Buffers and output/seam structures must be distinct, valid
and stable for the synchronous call; callbacks must obey their scalar ABI.

Zero return and `transfer_complete=true` mean the finite callback sequence
completed: TX submitted, or RX copied the padded words. They do not mean
posted writes have drained, firmware accepted a command or Wi-Fi is ready.
`setup_submitted` and `data_bytes` count only successfully returned operations.
An operation reporting an error can already have side effects, so those
fields are not a recovery cursor. Every callback error becomes `-EIO` and
immediately stops the sequence. The result is cleared on pre-dispatch
refusal. The caller must invalidate an uncertain transaction without replay,
credit refund or automatic shared-resource teardown, as described in the
transport design.

The [host fixture](src/hif_pio_test.c) checks literal setup/data words and
offset order, both directions, unaligned little-endian buffers, byte/block
zero padding, unchanged TX storage, RX canaries, capacity and pointer/field
refusals before dispatch, and errors at setup/first/second data access in
both directions with no retry. Address/undefined sanitizers and strict C11
warnings pass. The kernel include branch and a real MMIO adapter remain
uncompiled. No device/backend action or runtime support is claimed.

DMA translation remains necessary to enable DMA. It is not a requirement
for usable Wi-Fi if PIO meets the user-facing functionality and performance
needs. DMA remains an optional performance path unless evidence establishes
otherwise.
