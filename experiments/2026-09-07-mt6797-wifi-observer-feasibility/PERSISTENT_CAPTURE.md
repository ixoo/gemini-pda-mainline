# Persistent Wi-Fi capture constraints

The existing same-version Gemian pmsg storage is a possible backing store, but
the old process-context witness helper is not a suitable direct writer for all
required Wi-Fi observations. This assessment selects no new memory range,
changes no kernel code and admits no physical write or recovery action.

The [source receipt](results/persistent-capture-sources.json) pins five complete
public Git objects at the selected Gemian revision and the retained build
configuration. The earlier [pmsg witness](../2026-08-28-a72-pmsg-witness/DESIGN.md)
and its [runtime result](../2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt)
supply same-version retention evidence for their exact candidate, not a
replayable Wi-Fi artifact or cross-version mainline storage contract.

## Lock context

The old `pstore_write_pmsg_kernel()` takes `pmsg_lock`, a mutex, before calling
the backend. It is intended for fixed process-context sites. In the selected
power provider, `disable_subsys()` holds `mtk_clk_lock` across both the initial
state check and `sys->ops->disable()`. The pinned header defines that lock as
`spin_lock_irqsave`. Therefore a direct call to the old mutex-taking helper
from those status-read sites is invalid. Moving the physical read outside the
lock or repeating it later would change the operation being observed.

A deferred worker could copy an ordinary RAM record into pmsg later, but it
would leave the interval before that worker runs unprotected against reset or
a stalled cycle. Such a design cannot silently claim persistent in-progress
capture. A separate atomic-context-safe writer or an explicitly weaker capture
contract is needed; no such writer is implemented here.

## Capacity and write semantics

The retained configuration requests a 64-KiB pmsg zone. The persistent-ring
header contains three 32-bit fields; with no ECC allocation, usable payload is
65,524 bytes. The historical recovered pmsg file had exactly that size, but
this does not establish a future candidate's platform parameters or available
space. Candidate and recovery must verify the same resolved layout, ECC and
ownership before selecting it. The broader reserved area's size is not the
pmsg payload budget.

`ramoops_pstore_write_buf()` returns zero for a present pmsg zone after calling
`persistent_ram_write()`. The latter silently keeps only the tail of an
oversized write, overwrites old ring content as later writes wrap, and returns
the original requested count. Neither return proves retention of a complete
record sequence. The earlier witness actually lost its initial record; its
accepted suffix rule cannot be imported into a joined Wi-Fi lifetime trace.

The ring writer updates size/start metadata before copying payload bytes and
then updates header ECC. An interrupted write can therefore leave metadata
covering incomplete payload. A serialization lock alone would not establish
record commit ordering or power-loss durability. The future format needs
independently recognizable complete records, cycle identity, ordering and
integrity checks, and refusal on malformed, missing or overwritten required
records. It must reserve room for a failure/overflow terminal before admitting
normal records and stop recording before wrap; these limits are not provided
by the existing backend.

The [focused reproduction](test-persistent-ring.py) compiles the actual ring
writer with injected storage helpers. It confirms oversized-write truncation,
subsequent overwrite, the original return counts and metadata publication
before the first payload copy. The host compile uses GNU C11 and
`-Wall -Wextra -Werror -Wno-sign-compare`; the exception preserves the original
signed/unsigned comparison. This is an ordering/format test, not a physical
persistence, memory-barrier or concurrent-writer test.

## Next implementation boundary

Keep the existing reserved-memory layout as the first design option. Before
adding a writer, account for every producer and enumerate the bounded record
inventory for one complete native cycle, including DMA mapping/programming,
positive idle before unmap, firmware-stop reads and coherent common OFF.
Polling observations must preserve the original read count and short-circuit
order. No guessed transfer count or silently discarded overflow can establish
the complete cycle. If the resulting inventory cannot fit the verified zone,
resolve that conflict before choosing another layout or reducing evidence.

Then bind the exact capture budget to the separately reviewed watchdog owner
and recovery reader. The controller's four-second wait and the historical
12-second recovery window do not supply this contract. No observer, controller,
new runtime writer, kernel image or device action is introduced by this review.

## Source-derived record inventory

The [sizing receipt](results/capture-sizing.json) pins six complete source files
and reuses the existing sanitized retained-image inspection. It separates
firmware payload chunks from actual DMA transactions and from polling reads.

For the selected MT6797 divided loader, sections 0 and 1 use HIF download;
sections 2 onward take the conditional EMI-copy path. The retained image's
first two sections contain 5,840 and 8,992 bytes. At the source's 2,048-byte
`CMD_PKT_SIZE_FOR_IMAGE`, these produce three and five payload chunks:
`2048, 2048, 1744` and `2048, 2048, 2048, 2048, 800`. The other sections,
331,296 and 65,392 bytes, must not be charged as HIF payload chunks.

This gives eight payload submissions if the selected load completes, not eight
DMA transfers for the whole cycle. Section-configuration commands, subsequent
initialization commands, events and shutdown are additional. `nicTxInitCmd()`
passes through `HAL_WRITE_TX_PORT` to WTDR1, but the AHB writer takes DMA only
when its runtime `use_dma`, `fgDmaEnable` and callback checks also pass. Neither
the submission count nor the helper's unconditional success return proves a
mapping, completion or firmware execution. Common WMT patches are a separate
BTIF transfer path and must not be mixed into WLAN AHB counts.

The native EN idle loop can call its polling helper 100,001 times before the
count escape. Even one byte per read would exceed the nominal pmsg payload
capacity. The INTFLAG loop is time-based, so its read count is not supplied by
the source's five-second comparison. Capture each loop as an entry plus a
summary of existing reads: read count, last raw value, whether a read occurred,
and the exact exit reason. Preserve the original calls and branch ordering.
A loop that stalls before its summary remains an incomplete phase; its entry
must never be accepted as positive idle. Counter overflow must also invalidate
the summary rather than wrap into a small count.

The required record families are now:

| Family | Required content and joining rule |
| --- | --- |
| Cycle and initializer | Candidate/boot identity, single cycle identity, component entry/result, selected HIF and firmware identities; no arithmetic aggregate as readiness. |
| DMA acquisition | Transaction identity, device identity, RX/TX direction, requested and rounded byte counts, full DMA API address and selected mapping branch. |
| DMA programming | Same transaction, actual low SRC/DST and LEN/CON store arguments, existing ADDR2 read values and store arguments, and start/interrupt-control arguments. No extra readback. |
| DMA completion/release | INTFLAG and EN loop summaries, ACK/stop operation arguments, exact timeout/escape/reset branch, and unmap entry/completion joined to a prior positive idle result. |
| Firmware and EMI | Section/configuration outcomes, conditional EMI extent/protection/copy outcomes, stop-command outcome and actual WCIR-read completion/value with exit branch. No payload or calibration bytes. |
| Shared OFF | Actual provider dispatch, shortcut state pair, protection/control arguments, existing polling summaries and the terminal pair of clear power bits; retain short-circuit read validity. |
| Isolation and terminal | Unexpected consumer, transmit/mode/reset/boost activity; completion, failure or overflow; no successful terminal with missing required records. |

This inventory selects loop summaries rather than per-poll logging while
retaining every DMA transaction. It does not yet choose encoded record sizes,
a maximum transaction count or a new memory layout. The full-cycle transfer
count remains unbounded by the inspected sources; the writer must enforce a
finite admitted capacity and refuse overflow. The eight-chunk calculation
makes a compact capture plausible but does not prove that one complete cycle
fits. The next step is an explicit byte layout and capacity calculation for
these fields, followed by the atomic-context writer and recovery contract.

## Offline record framing prototype

[capture-records.py](capture-records.py) now defines a fixed 128-byte,
little-endian envelope. This is an offline encoding/decoding prototype, not a
kernel writer, raw-pmsg scanner or complete event-payload schema.

| Offset | Bytes | Field |
| --- | ---: | --- |
| 0 | 4 | `WFC1` magic |
| 4 | 2 | Format version 1 |
| 6 | 2 | Record kind |
| 8 | 4 | Contiguous sequence starting at zero |
| 12 | 16 | Nonzero cycle identity, independently expected by the reader |
| 28 | 4 | Transaction identity |
| 32 | 4 | Used payload length, at most 84 |
| 36 | 84 | Payload followed by mandatory zero padding |
| 120 | 4 | IEEE CRC32 of bytes 0–119 |
| 124 | 4 | Final marker `0x57464331` |

Kind 1 is the sole first record: an 80-byte payload containing the candidate
SHA-256, 16-byte boot ID and input-manifest SHA-256; transaction is zero.
Kinds 2–10 reserve initializer, DMA acquisition, programming, poll summary,
unmap, firmware, EMI, shared-OFF and isolation records respectively. Their
field-level payload contracts remain unfinished; the decoder deliberately
makes no lifecycle verdict from them. Kind 255 has zero transaction and a
four-byte producer-reported status: 1 complete, 2 failed or 3 overflow. A
producer's complete status is not an independently validated cycle result.

The largest identity payload fits without splitting. The nominal 65,524-byte
zone accommodates 511 records (65,408 bytes), leaving 116 bytes unused.
Only 510 slots are available to ordinary records, including the identity;
slot 510 is terminal-only. This is an explicit capacity limit, not a proof
that the complete cycle fits. The writer will need to reserve the terminal
before recording ordinary events and terminate capture on exhaustion.

The decoder takes an exact record stream and an independently supplied cycle
identity. It rejects missing prefixes, sequence gaps/duplicates, mixed cycles,
unknown kinds, nonzero padding, bad CRC/marker, partial records, excess capacity
and records after a terminal. A complete committed prefix without a terminal
can be returned as partial evidence. It does not search untrusted raw pmsg for
magic, discard bad records, accept a suffix, verify payload semantics or turn
a recorded terminal into hardware success.

The [six focused tests](test-capture-records.py) passed round-trip/prefix checks,
every single-bit mutation of the first record (1,024 cases), every nonempty
partial-final-record length (127 cases), cycle/order failures, invalid fields
and full capacity with the reserved terminal. No physical storage is touched.
CRC is an accidental-corruption check, not authentication or a proof of atomic
writes. The future writer must still establish ownership, write ordering,
readback and recovery behavior; this encoder merely places the marker last
in a byte string. Stale-record exclusion also requires a fresh externally
bound cycle identity, not just a nonzero field.

## DMA payload layouts

The offline codec now checks exact payload sizes and discriminators for kinds
3–6. All integer fields below are little-endian. Device is a nonzero ID that
the future candidate must bind to its exact DMA device; it is not a kernel
pointer. Transaction is the nonzero envelope field, shared by the records of
one transfer. Direction is observer enum 0 RX or 1 TX, corresponding to the
native FROM_DEVICE or TO_DEVICE mapping call respectively.

| Kind | Payload fields, in order | Bytes |
| --- | --- | ---: |
| 3 acquisition | device u32, direction u32, requested bytes u32, rounded bytes u32, full DMA address u64, port u32, branch u32 | 32 |
| 4 programming | device u32, phase u32, full source argument u64, full destination argument u64, thirteen register values u32 | 76 |
| 5 polling | phase u32, stage u32, reason u32, reserved zero u32, read count u64, last raw value u32, read-valid u32 | 32 |
| 6 unmap | stage u32, device u32, full DMA address u64, rounded bytes u32, direction u32 | 24 |

Acquisition branch 1 means the DMA API path and 2 the preallocated path. A
branch-2 record is representable so the observer can retain an unexpected
selection; it does not satisfy the DMA API acquisition predicate. Zero or
unexpected addresses and inconsistent requested/rounded counts are likewise
preserved, not normalized into validity.

Programming phase 1 stores the full configuration source/destination arguments
and these thirteen actual values: CON read, CON store, low SRC store, low DST
store, LEN store, SRC_ADDR2 read/store, DST_ADDR2 read/store, INT_EN read/store,
and EN read/store. Phase 2 records ACK read/store and stop INT_EN read/store in
the first four slots; full source/destination and the other nine slots are
zero. These are values at existing accesses, not added readback transactions.
The encoder does not require the observed programming to match the DMA address;
that comparison belongs to the later lifecycle validator.

Polling phase 1 is INTFLAG and 2 is EN. Stage 1 is entry, with all result fields
zero. Stage 2 is exit. Reasons are 1 condition satisfied, 2 deadline escape,
3 count escape, 4 native error path, or 5 observer counter overflow. Read-valid
must agree with a nonzero read count; without a read, last value must be zero.
These are record-consistency checks, not proof that an EN result is idle or
that an INTFLAG result is completion. The raw value remains available to the
future validator. Unmap stages 1/2 are entry/return and repeat its exact native
address, length and direction.

The core DMA sequence therefore costs nine records: acquisition, setup,
INTFLAG entry/exit, shutdown programming, EN entry/exit, unmap entry/return.
That is 1,152 bytes per transaction. After the identity record, at most 56 such
sequences fit in the ordinary-record allowance, even before initializer,
firmware, EMI, shared-OFF, isolation and other wrapper observations are added.
The eight firmware payload submissions would consume 72 records if all eight
take DMA, leaving 437 ordinary records after identity. This arithmetic is a
capacity illustration, not a whole-cycle bound or a decision to omit any
required observation. Event schemas and the final admitted budget must account
for those other records before constructing a candidate.

Eight focused tests now pass, including exact DMA layout round trips, full
64-bit address preservation, poll entry/exit consistency and truncated or
unattributed DMA payload refusal. Existing framing corruption and capacity
tests still pass. Cross-record transaction ordering, positive idle before
unmap, non-DMA payload schemas and physical writer/recovery behavior remain
unfinished; no producer-reported success is promoted by these checks.

## Cross-record DMA consistency

`check_dma()` now checks each recorded DMA transaction after strict framing
validation. The [additional source receipt](results/dma-check-sources.json)
pins the native direction enum and register masks; the previously pinned
`ahb_pdma.c` supplies the actual transformations. Native TX/RX are 0/1,
while the observer enum is RX/TX 0/1, so the CON direction bit is translated
explicitly rather than copied from the observer field.

The checker requires exactly the nine core records per transaction, including
both poll entries/exits and unmap entry/return. Missing records, reuse of a
transaction ID or moving unmap before the idle result are refusals. It requires
a DMA API mapping with positive, nontruncated transfer length, matching device
and full mapped address in the selected programming source/destination, matching
low-word stores and LEN, the native CON masks/burst/direction, and the recorded
ADDR2/interrupt/enable OR operations. ACK and interrupt-stop stores must match
their recorded reads with bit zero cleared.

Both polling exits must report the condition branch and include an actual
read: INTFLAG bit zero set for completion, EN bit zero clear for idle. Unmap
must then use the same device, address, length and direction. A count escape,
missing read or a producer's claimed completion with the wrong raw bit is not
accepted. The decoder still preserves those structurally valid fault records;
only the consistency check refuses them.

Ten tests pass, including RX and TX sequences, seventeen payload mutations
re-encoded with valid CRCs, and incomplete, repeated and reordered lifetimes.
The new mutations cover mapping branch/length/address, register transformations,
false completion/idle, timeout/count-escape classification and mismatched unmap.
This is stronger than CRC checking but remains a check of recorded software
operations. It does not establish bus translation, actual endpoint ownership,
visibility of posted stores, firmware execution, a full Wi-Fi cycle or a safe
physical release. In particular, reproducing the vendor's unconditional ADDR2
OR does not prove it encodes the DMA API address correctly. The result contains
only checked transaction IDs and that limited scope; no hardware pass is emitted.

Non-DMA events are outside this function's verdict. Their schemas and causal
checks, capture hooks, physical storage ownership and recovery remain required
before a candidate can use this format for the complete experiment.
