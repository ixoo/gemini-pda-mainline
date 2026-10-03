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

Integrate the source-matched clock/resources, shared ownership and DMA exclusion,
and resolve FIFO writes and bounded IRQ receive handling. Compare upstream
STP/WMT helpers for actual framing and ownership compatibility. Then implement only
the fixed default query and matched-event parser under the existing CONSYS
owner, with focused split-response/malformed/deadline fixtures. Complete
Buildbox and candidate/deployment gates before one physical test. No patch,
calibration or full-mode negotiation belongs to that first query lifetime.

## Register-table cross-check and fixed wire helper

The retained MT6797 register table part 1, SHA-256
`e8ef503a32a8bb318a000fe6727d2bcdaa3557992a0ffed344e9de37acc2caff`,
was checked by extraction and visual inspection of pages 1371–1372. Page 1371
assigns RX interrupt enable to bit 1 and TX to bit 0, while the selected vendor
header assigns RX to bit 0 and TX to bit 1. Its FIFO-clear assignment likewise
reverses the source's RX/TX bits, and describes a FAKELCR-dependent control mode
that the source initializer does not select. These conflicts are real page
content, not extraction errors. The document cannot select new bit values by
itself; retain the discrepancy until revision-matched behavior resolves it.

Page 1372 agrees on LSR bits 0/5/6 but describes DR in terms of an RX buffer
becoming full; that does not independently prove byte-by-byte readiness with
IRQs masked. Page 1373 corroborates the timeout-reset side effect of reading
local DMA_EN. No new register operation follows from these documentary claims.

The independently authored [fixed wire helper](tests/wmt-default-query.h)
contains only the 11-byte default query and a byte-fed exact reply validator.
It accepts the source's sync/sequence variation, but rejects incorrect task,
length, opcode, status, options or zero trailer. Failure is sticky and extra
input after completion is rejected. The caller still owns timing, read budgets,
single-use lifetime and recovery; the helper claims none of those mechanisms.

[Host tests](tests/wmt-default-query-test.c) passed with AddressSanitizer and
UndefinedBehaviorSanitizer, covering every two-chunk split and incomplete prefix,
all sync bytes, every replacement value for each remaining frame byte, null
input, sticky failure and extra input after completion. Strict file style
checks also passed. No kernel build, transport implementation or device test
was performed. This helper is not a boot candidate.

## Revision-matched resources and wake boundary

The Gemian-v8 revision supplies byte-identical `mtk_btif.c`, `btif_plat.c`
and `btif_priv.h` to the selected vendor files. This narrows the source match;
it does not prove that the PIO fallback ran or resolve the register-table
conflicts. The selected Gemian DTS names BTIF at `0x1100c000`, size `0x1000`,
SPI 130 with level-low polarity, and separate TX/RX AP-DMA windows at
`0x11000a00`/`0x11000a80`, each size `0x80`, SPIs 116/117. Retained v8 boot
logging corroborates these physical bases and mapped IRQs. No FIFO/control
register values were found in that log.

Gemian and upstream v7.1.3 both map BTIF to infracfg gate bank 0 bit 31,
parent `axi_sel`, with set/clear/status offsets `0x80`/`0x84`/`0x90`. AP-DMA
is bank 1 bit 18, the same parent, with offsets `0x88`/`0x8c`/`0x94`.
Upstream already exports `CLK_INFRA_BTIF` (30) and `CLK_INFRA_AP_DMA` (46);
use the clock framework rather than new raw clock writes. The vendor prepares
both clocks, but enables the AP-DMA clock for DMA modes. PIO does not itself
establish a need to enable that engine clock.

The selected CONSYS owner and binding were replayed from file creation through
proposal 0084. They currently have no BTIF resources or clock acquisition;
the query requires explicit binding and owner integration. Canonical patch
0514 removed the unsourced `MT6797_INFRA_BTIF_RST` identifier. Do not restore
or use the old reset number for this experiment. The inspected vendor
controller initializer uses FIFO clears, with no BTIF reset-controller call.

The exported wake API is documented for use after a CONSYS sleep command. Its
WMT caller is the full-mode power-saving WAKEUP branch. The inspected startup
chain opens BTIF, initializes its controller and enters mandatory-mode `sw_init`
without that wake call. Consequently the first fresh-power query should not
add a speculative wake pulse. This is a source-path conclusion, not a measured
wake-state guarantee; any unexpected asleep state is a terminal observation,
not permission to pulse and retry.

Implement RX using the selected interrupt-based PIO boundary unless further
evidence justifies polling. PIO excludes packet DMA, not interrupts. This
avoids making unproved IRQ-masked LSR readiness a prerequisite. The IRQ handler
still needs a finite byte budget, exclusive ownership, malformed/extra-byte
terminal handling, and synchronized shutdown. FIFO alias writes, DMA-state
exclusion and failure power retention remain implementation gates. No transport
implementation or hardware candidate is added by this review.

## Query executor draft (incomplete checkpoint)

The independently authored [query executor](tests/mt6797-wmt-query.h) now
implements one fixed PIO request and a bounded IRQ receive lifetime. It requires
zeroed persistent CONSYS-owned storage and validated mappings/clocks/IRQ. It
rejects active channel EN/STOP/FLUSH or nonempty internal/virtual DMA buffers,
nonempty BTIF FIFOs, preexisting local DMA requests and startup interrupts.
It sends at most eleven bytes, consumes at most sixteen reply bytes, rejects
an immediately queued extra byte, and retires at 32 IRQ entries or a 500 ms
deadline. Malformed data and timeouts never resynchronize or retry. Terminal
handling disables the local source and CPU IRQ and synchronizes before freeing
the IRQ. Acquired clocks and CONSYS power remain held for reviewed recovery,
including failures; this is not reusable teardown.

The draft deliberately reproduces the revision-matched source's four aliased
FIFO clear operations, rather than treating IIR as a control readback. Its one
initial local DMA_EN read admits the documented timeout acknowledgment effect;
it then preserves unrelated fields while setting automatic reset. These are
explicit draft effects, not resolved empirical register semantics or an admitted
hardware protocol. Exact effects, initial-state observations, recovery and
owner/binding integration must be reviewed before selecting a build/candidate.

The existing upstream MT6797 DTS supplies the sysirq polarity provider, and the
upstream driver translates level-low into polarity inversion plus a level-high
parent interrupt. A BTIF child should inherit that provider; it must not attach
a level-low IRQ directly to GIC or add raw polarity writes.

Run `python3 experiments/2026-10-03-mt6797-wifi-audit/tests/run-wmt-query-transport-test.py`.
The sanitizer-backed [host fixtures](tests/wmt-query-transport-test.c) pass the
matched event, ten channel-busy cases, clock/request failures, nonempty startup,
local DMA requests, pre-TX IRQ, partial/malformed/extra reply, spurious IRQ,
deadline and IRQ-budget terminals, and no-write repeat refusal. They exercise
the actual draft but do not model IRQ concurrency, real MMIO semantics or clock
framework lifetimes. Strict kernel style passes for the executor. No driver
caller, format-patch, selected series/profile, kernel compile or device test is
added yet. This checkpoint is incomplete and is not a boot candidate.
