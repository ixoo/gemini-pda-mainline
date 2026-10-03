# Checked STP option transition preparation

[Default transport liveness](../2026-10-03-mt6797-wmt-default-query/results/runtime-2.json)
now passes. The existing query-only executor cannot send the next mandatory
set-options request or validate its different reply length. The independently
authored [fixed helper](tests/wmt-stp-options.h) supplies only that wire request,
its strict byte-fed reply validator and the subsequent full-query payloads.
It leaves the consumed default-query candidate unchanged and admits no effects.

## Selected boundary

The selected Gemian source sends the nine-byte WMT set-options command
`01 04 05 00 03 df 0e 68 01` in mandatory STP. Its 15-byte frame fits an
initially empty 16-byte TX FIFO; the 12-byte framed response must still be
drained incrementally. Require exact event `02 04 02 00 00 03`, task, length
and zero trailer, accepting only the source-permitted sync variation. Extra
input or any malformed byte is a sticky failure. Caller-owned deadlines,
IRQ/byte limits and no-retry retirement remain mandatory.

The selected mandatory TX branch writes the debug sequence into the sync byte
but does not increment it. Thus this request retains sync `80` after the first
query. Full-mode enable separately resets host sequences to zero and both
last-ACK values to seven. Follow the source's 10-ms switch wait before sending
the full query; this is source timing, not a measured peer minimum. The full
query expects `02 04 06 00 00 04 df 0e 68 01`, distinct from the default options.
Use the existing full-STP codec/state and require peer credit, exact event and
completed host ACK before advancing. No DLM, ROM patch or RF command is added.

## Validation and remaining integration

```sh
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/2026-10-03-mt6797-wifi-audit/tests/wmt-stp-options-test.c \
  -o /tmp/gemini-wmt-options-test
/tmp/gemini-wmt-options-test
rm /tmp/gemini-wmt-options-test
```

Every response split/prefix and all 256 byte values at each of its 12 positions
pass the acceptance/refusal predicates; extra input and sticky failure are
checked. A synthetic full query composes with the existing codec/state and
cannot finish before its host ACK is accounted for. Strict warnings and
address/undefined sanitizers pass. Private source comparison verifies all four
authored arrays against the pinned selected commands/events and framing.
The [receipt](results/stp-options.json) pins inputs and limits these claims.

Next integrate the checked set exchange and full-query wrapper under one
CONSYS owner with retained resources, explicit IRQ depth/synchronization,
finite whole-negotiation budget and first-failure retirement. Do not reuse the
query-only structure by resetting its attempted flag, re-enable clocks for each
command, or clear FIFOs between commands. Preserve phase, actual TX/RX bytes,
sequence/ACK state and failure evidence before reviewed recovery. No Linux
build, hardware negotiation or complete common initialization follows from
these host fixtures.

The [mandatory IRQ/FIFO integration](FULL_STP_IO.md#mandatory-set-options-integration-checkpoint)
now exercises the fixed set exchange through the existing service/process wrapper.
The combined CONSYS caller and hardware transition remain incomplete.
