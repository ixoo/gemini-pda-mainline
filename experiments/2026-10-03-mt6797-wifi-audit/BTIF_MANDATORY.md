# First WMT query: BTIF and mandatory STP source contract

Status: selected source behavior reviewed; no driver, build or device admission.
The [source receipt](results/btif-mandatory-source.json) pins the inspected
vendor transport, register headers and STP/WMT core at commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`.

## Mandatory framing

`wmt_core_stp_init` enables BTIF mandatory mode before its hardware check and
chip `sw_init`. Mandatory TX uses a four-byte header, payload and two zero
trailer bytes. WMT task index is **4**. The payload length occupies the low
nibble of byte 1 and byte 2; header byte 3 is zero. Header byte 0 has bit 7 set
and includes the debug sequence. Reset initializes TX sequence to zero.
BTIF does not use the SDIO branch's four-byte padding.

The source-bound default option query gives this 11-byte initial frame:

```text
80 40 05 00 | 01 04 01 00 04 | 00 00
```

Its expected WMT event payload is ten bytes. One possible 16-byte enclosing
frame is:

```text
80 40 0a 00 | 02 04 06 00 00 04 11 00 00 00 | 00 00
```

The response header's low sequence bits are not fixed by this example.
Mandatory RX accepts a sync byte with bit 7 set, extracts task/length and
consumes two zero trailer bytes. The vendor parser only logs a nonzero trailer;
a diagnostic must define its own strict malformed-frame stop behavior. This
framing has not been observed on a mainline BTIF transfer.

## PIO and interrupt boundary

The selected header describes 16 TX FIFO bytes and 8 RX FIFO bytes. The
11-byte query fits one initially empty TX FIFO; the 16-byte response must be
drained incrementally. Data uses byte accesses at offset zero. LSR at `+0x14`
defines RX-data bit 0, TX-threshold bit 5 and TX-empty bit 6.

The selected build locally enables `NEW_TX_HANDLING_SUPPORT`: send queues data
in software and enables TX interrupts. The inactive direct-write branch and
the TX interrupt handler describe FIFO-room handling, but neither proves a
fully polling mainline path. RX PIO setup enables the interrupt, and its drain
loop checks IIR rather than LSR. Establish readiness with IRQs masked before
claiming the proposed polling design matches observed hardware behavior.

`hal_btif_hw_init` selects normal/new-handshake mode, pulses FIFO clears, sets
thresholds, disables loopback and TX/RX DMA requests, enables timeout automatic
reset, disables TX interrupt and enables RX interrupt. This is a source order,
not a ready-to-copy mainline initializer.

## Access effects that constrain implementation

- Offset `+0x08` reads IIR but writes FIFO control. Vendor set/clear macros perform
  read-modify-write there, so their read cannot be treated as the FIFO control
  value. Resolve direct write values and clear-pulse semantics.
- Header comments say reading local `DMA_EN +0x4c` resets a timeout interrupt
  when automatic reset is disabled. Review this effect before an initial read.
- BTIF-local DMA-request bits and AP-DMA channel enable are separate. Source
  defines TX/RX channel EN at channel `+0x08`; disabling local requests alone
  does not prove idle DMA or safe clock release.
- TX writes and RX reads consume FIFO state. A future experiment must admit
  exact values, access counts, deadlines and terminal handling, including
  unexpected startup bytes, partial transfer and timeout without retry.

## Upstream comparison

Pinned Linux v7.1.3 `drivers/bluetooth/btmtkuart.c` has the matching basic
four-byte STP header and zero checksum/trailer shape. Its send path prepends
Bluetooth H:4 and fixes the STP task to 0; RX feeds H:4, and its transport is
serdev. The first Gemini startup exchange instead uses raw WMT task 4 through
BTIF. This supports a framing reference, not whole-driver binding or use of the
HCI-wrapped WMT path for common startup. The receipt pins the upstream file.

## Next implementation gates

Resolve exact mainline clock/resource binding, shared ownership, DMA exclusion,
polling readiness and initial wake/handshake timing. Compare upstream STP/WMT
helpers for actual framing and ownership compatibility. Then implement only
the fixed default query and matched-event parser under the existing CONSYS
owner, with focused split-response/malformed/deadline fixtures. Complete
Buildbox and candidate/deployment gates before one physical test. No patch,
calibration or full-mode negotiation belongs to that first query lifetime.
