# Frame collection and the remaining FIFO owner

The [byte collector](tests/wmt-full-stp-stream.h) combines the
[full-STP codec](FULL_STP.md) with bounded persistent frame storage. A full
patch-command frame can contain 1011 bytes; the fixed default query collector
cannot be widened safely by merely changing its 16-byte expected reply.
This helper has no MMIO, clock, IRQ, firmware or radio operation.

## Collection boundary

Collect four header bytes first, then validate sync, selected WMT task,
header checksum and the 1005-byte payload ceiling before accepting a body.
A zero-length ACK completes at four bytes. A data frame completes only after
its complete payload and two CRC bytes validate through the codec. Incomplete
input exposes no decoded result. A malformed header or CRC is terminal;
additional bytes cannot repair it or start a resynchronization search.

Completed frames remain terminal until the owner consumes and accepts them.
The payload aliases the collector buffer. Only after acceptance may the owner
initialize the collector for the next frame. A burst containing ACK followed
by data therefore needs two explicit acceptance boundaries, even if both arrive
in one IRQ. The [state helper](FULL_STP_STATE.md) validates peer ACK, sequence
and exact WMT event before releasing an exchange. An extra frame after exchange
completion must be classified rather than discarded or treated as the next
command's response. Retire on unexpected input under a finite owner protocol.

## FIFO source findings

The pinned BTIF source and header in the
[earlier receipt](results/btif-mandatory-source.json) select
`NEW_TX_HANDLING_SUPPORT=1`. The ordinary send routine enqueues bytes into a
software FIFO and enables the TX interrupt; its returned count is an enqueue
count. It does not establish complete hardware FIFO submission or wire delivery.
The selected IRQ handler reads LSR: TEMT permits up to 16 writes; otherwise
THRE permits up to 8 writes; when neither is set, it writes nothing. It dequeues that batch,
writes bytes through THR and disables TX interrupt when the software queue is
empty. Empty software queue is distinct from an empty hardware FIFO.

Use these as source-backed design inputs, not an admitted polling algorithm.
The source header and register documentation have conflicting interrupt bit
assignments, the FIFO control aliases IIR reads, and DMA_EN reads can acknowledge
timeout state. The installed query protocol resolves only its exact small
RX-only exchange. A full transfer owner still needs selected TX/RX causes,
bounded IRQ work and frame/byte totals, fresh status before each batch, serialized
TX/RX state, partial-TX retirement, deadline retirement and preserved clocks/power.
Do not reuse one LSR observation to write multiple unrestricted batches or call
the state's sent transition after enqueue alone. Buffer RX arriving during TX.
No new TX interrupt, FIFO-control write, DMA operation or mode switch is admitted.

## Focused checks

```sh
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/2026-10-03-mt6797-wifi-audit/tests/wmt-full-stp-stream-test.c \
  -o /tmp/gemini-wmt-stream-test
/tmp/gemini-wmt-stream-test
rm /tmp/gemini-wmt-stream-test
```

Tests feed frames byte by byte at payload lengths 1, 5, 10, 255, 256, 1000 and
1005; no intermediate result is exposed. Every encoded length 1006–4095 is
refused at byte four. Bad payload CRC remains terminal without a decoded result.
An ACK and subsequent exact event pass through collector and state acceptance,
but the exchange cannot finish until host ACK submission is confirmed.
Extra bytes after completion are refused. Strict warnings and address/undefined
behavior sanitizers pass. The [receipt](results/full-stp-stream.json) pins the
files. Real FIFO timing, interrupts, peer behavior, kernel integration and Wi-Fi
reception remain untested. The installed [default query session](../2026-10-03-mt6797-wmt-default-query/SESSION.md)
still precedes any additional transport effects.
