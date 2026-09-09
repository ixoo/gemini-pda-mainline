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

## Firmware-stop observation boundary

A source audit of the three inputs pinned in
[the capture-sizing receipt](results/capture-sizing.json) narrows the next
producer hooks. In `wlan_lib.c`, `wlanAdapterStop()` initializes both its local
WCIR value to zero and its returned status to success. Its power-down work is
conditional on D0, a responsive chip and a present card, then on driver
ownership and successful `wlanSendNicPowerCtrlCmd(adapter, 1)`. The returned
status is not changed when those gates skip work or when the polling loop
uses a fallback or reset branch. Adapter-stop return alone cannot establish
firmware shutdown.

The ordinary loop first tests READY clear, then conditionally invokes
`wlanPowerOffInt()`, then handles removal, bus failure or polling timeout.
Consequently an exit record must distinguish ordinary READY clear, successful
fallback and reset-trigger branches, as well as skipped command/polling work.
The actual branch matters: reconstructing an assumed timeout decision from
only the final loop counter loses the source's branch priority.

There is also a read-attribution hazard before that first test. In the non-SDIO
`hal.h` path, `HAL_MCR_RD` either calls the accessor directly or stores a shared
register offset/result pointer, wakes the HIF thread and calls
`wait_for_completion_interruptible()`. The macro discards the wait result.
A macro return therefore does not by itself prove that a read supplied the
local value. If a wait returns early before the first read, the initialized
zero could satisfy READY clear. This is a source-level possible path, not an
observed device failure or a claim that the selected shutdown uses the queued
path. Direct dispatch depends on the HIF-thread pointer and caller name and
must itself be observed.

In the selected AHB `ahb.c`, `kalDevRegRead()` assigns the result of
`HIF_REG_READL` to the output and returns TRUE unconditionally. Its return is
not an independent bus-error check. The producer needs a record after the
actual accessor assignment, joined to the stop invocation and particular
read request, followed by the caller's consumed value and selected exit
branch. Record direct/queued dispatch and, for queued dispatch, the actual
completion-wait result. A missing accessor completion, unmatched request,
interrupted wait or mismatched consumed value cannot establish ordinary
READY-clear shutdown. Capturing only the wrapper return and local value is
insufficient even with valid framing and CRC.

The selected removal caller and HIF completion lifecycle are resolved below.
Queued-read attribution remains outside the ordinary-stop checker. Do not
publish kernel pointers as correlation IDs. This audit adds no runtime
instrumentation or hardware evidence.


## Firmware-stop payload and consistency check

The previously pinned `gl_init.c` confirms that normal `wlanRemove()` clears
its HIF-thread pointer before `wlanAdapterStop()`, even after a completion
wait times out. Probe-failure cleanup calls stop separately without that
sequence. The [additional source receipt](results/stop-check-sources.json)
pins `gl_kal.c` and the register definitions: WCIR offset is zero and READY
is bit 21. The HIF loop completes queued register reads after calling the
accessor. Its halt completion is signalled before final wake-lock cleanup
and thread return. Neither a null pointer nor that completion alone proves
that every thread cleanup operation finished. The existing
[removal wait requirements](CYCLE_CONTROL.md#native-request-and-teardown-paths)
remain separate from firmware-stop consistency.

Kind 7 now admits four stop subtypes, each beginning with a little-endian
`u32` subtype. The envelope transaction is a nonzero stop-invocation ID;
firmware-load payloads remain unsupported. All fields below are `u32` unless
explicitly `u64`; adapter IDs are observer-assigned ordinals, never pointers.

| Subtype | Fields in wire order, including subtype |
| --- | --- |
| 1, entry | subtype, adapter ID, caller (1 normal remove, 2 probe failure), HIF pointer present, D0 predicate, chip-no-ack predicate, card-removed predicate |
| 2, command | subtype, firmware-owned predicate, command attempted, native command status (zero placeholder when not attempted) |
| 3, poll summary | subtype, dispatch (0 none, 1 direct, 2 queued, 3 mixed), actual exit branch (1 READY clear, 2 successful fallback, 3 reset, 4 skipped), request count `u64`, accessor-completion count `u64`, last completed request ordinal `u64`, fallback-call count `u64`, register offset, final accessor value, final caller-consumed value |
| 4, return | subtype, native adapter-stop status |

Boolean fields use 0/1. Entry gate fields reflect the evaluated native
predicates; unevaluated predicates use zero and cannot make an ineligible
entry pass. Command ownership is recorded at the command gate, after power
acquisition. Counters and request ordinals are scoped to this stop's outer
WCIR loop, starting at one for the first request; exclude nested fallback
reads and unrelated accesses. Count every fallback call, including failed
ones. Increment completion only after the accessor assigned its result,
with the originating request ordinal. With no completed accessor, its value
and last ordinal are zero. These are producer requirements still awaiting
hooks, not properties established by the offline decoder.

`check_stop()` requires exactly subtypes 1–4 for every recorded invocation.
It accepts only eligible normal removal with the HIF pointer cleared, driver
ownership and an attempted successful stop command. The poll must be direct,
exit on READY clear without any fallback call, address WCIR, and have positive
equal request/completion counts with the final request completed. The final
accessor and consumed values must match and have READY clear; the adapter
return must also be successful. Queued dispatch, probe cleanup, skipped work,
fallback, reset and missing or inconsistent reads cannot pass. Structurally
valid fault records remain decodable as evidence. Four records consume 512
bytes per stop, in addition to removal/thread records still to be specified.

Twelve framing/checker tests pass, including twenty valid-CRC stop mutations,
READY still set, zero reads, missing/reordered/reused invocations, malformed
payloads and absent stop evidence. The output names only checked stop IDs and
its limited scope. It does not establish thread quiescence, bus health,
firmware execution, shared OFF, physical capture persistence or full-cycle
success. Other event kinds are outside this check's verdict. No producer or
runtime candidate is added by this offline format change.

## EMI section payload and consistency check

Kind 8 now describes one later-section operation using the pinned
`wlanImageDividDownload()` path. The
[additional source receipt](results/emi-check-sources.json) pins its MPU
wrapper, lower operation and permission encoding. As established in the
[whole-image audit](../2026-09-05-mt6797-wifi-contract/WHOLE_IMAGE_EMI.md), the
wrapper discards the lower result, the loader ignores mapping failure, and a
failed copy-span condition can leave load status successful. Capture the lower
protection operation's actual result and the actual copy entry/return;
wrapper status and `fgEmiDownloaded` cannot substitute.

Each record starts with a `u32` subtype. Other fields are `u32` except those
marked otherwise. The envelope transaction is a nonzero section-operation ID.
Adapter, immutable image and mapping IDs are observer-assigned ordinals; no
kernel pointer or firmware bytes enter this format.

| Subtype | Fields in wire order, including subtype |
| --- | --- |
| 1, section | subtype, adapter ID, image ID, physical EMI base `u64`, section index, source offset, length, original destination, image byte length |
| 2, protection | subtype, phase (1 open, 2 restrict), stage (1 entry, 2 return), branch (1 secure call, 2 no-op), start `u64`, inclusive end `u64`, actual packed region/permission argument, lower signed `s32` status (zero placeholder at entry) |
| 3, mapping result | subtype, mapping ID (zero on failure), requested physical base `u64`, requested mapping byte length |
| 4, copy | subtype, stage (1 entry, 2 return), mapping ID, destination offset, source offset, copied byte length |

Record protection at the lower call, inside the existing lock, preserving its
packed argument and returned status before the outer wrapper discards it.
Distinguish the secure-call branch from the configuration-dependent zero-return
stub. Mapping records describe `ioremap_nocache()` arguments and whether its
result was non-null. Copy records surround the existing `kalMemCopy`, without
adding a read or replacing its implementation. Missing return after a stall is
partial evidence. The inspected path supplies no corresponding unmap operation;
this format does not invent one or claim mapping release.

`check_emi()` requires eight records per section: section, open entry/return,
mapping, copy entry/return, restrict entry/return. It checks positive source and
destination spans without 32-bit wrap, a nonzero base with a representable
512-KiB inclusive extent, and an EMI index of at least two. Both protection
pairs must use that extent, the secure branch and a zero lower status. Packed
arguments must match the native region-18 open policy and subsequent domain-2
policy. The mapping must cover the same base and 512 KiB; both copy records
must match that mapping and the section's source, length and masked destination.
Missing, reused or reordered operations are refused. Eight records occupy
1,024 bytes per section; the retained two-EMI-section image would need 2,048
bytes for these core events, separate from loader completion and ownership.

Fourteen focused tests pass, including twenty-four valid-CRC EMI mutations,
32-bit span-wrap refusal, negative and unknown positive lower statuses, no-op
protection, failed mapping, mismatched copy/protection fields and partial or
reordered sections. Fault records remain decodable when structurally valid.
This checks recorded operation consistency only. It does not bind the image
ID to actual immutable bytes, prove that every image section was handled,
grant reservation/remap authority, identify masters with permission domains,
establish copy visibility or authorize the native broad permissions. Those
remain whole-image and shared-owner requirements. No EMI write or producer
hook was executed or added by this offline change.

## Shared-OFF condition records

The provider source was rechecked against the
[existing source receipt](results/persistent-capture-sources.json). Its terminal
CONN OFF loop reads `PWR_STATUS`, then reads `PWR_STATUS_2ND` only when the first
CONN bit is clear. The mask is bit 1 in each register. These condition reads
are separate from diagnostic reads in the loop body and from the earlier
`sys_get_state_op()` pair used to decide whether to skip provider execution.
A value retained from a previous condition evaluation is not a final pair.

Kind 9 subtypes 1 and 2 describe that terminal condition loop. Its exact payload
is little-endian `<IIIQQIIII`: stage (1 entry, 2 summary), nonzero provider ID,
exit reason, primary condition-read count `u64`, secondary condition-read count
`u64`, final primary value, final secondary value, primary-valid and
secondary-valid. Other fields are `u32`; IDs are observer ordinals. The envelope
transaction is a nonzero provider OFF invocation ID, shared with the provider
records below. Entry has zero counters, values,
validity and reason. Summary reasons are 1 normal condition exit, 2 polling
compiled out, and 3 observer counter overflow. A stalled native loop has its
entry and no successful summary; no native timeout is invented.

Counters include only the existing reads in the condition, preserving their
short-circuit order. Final validity describes the last condition evaluation,
not whether a register was ever read. An invalid final value is encoded zero.
Secondary count cannot exceed primary count; a valid final secondary read
requires a valid primary with the CONN bit clear. Counter overflow invalidates
the capture instead of wrapping. If ACK polling is compiled out, record the
phase as skipped; do not fabricate a pair from a later diagnostic access.

`check_off_poll()` requires matching entry/summary provider IDs and a normal
exit with positive counts, both final reads valid, and both CONN bits clear.
It permits unequal read counts and preserves 64-bit counts. It refuses a missing final
secondary read despite earlier secondary reads, contradictory short-circuit attribution,
skipped polling, missing records and invocation reuse. Two records consume
256 bytes. Fifteen focused tests pass, including a primary count above 32 bits,
fewer secondary reads, a valid pair with unrelated status bits set, partial
polls and valid-CRC fault summaries.

This is a check of the recorded terminal condition only. It cannot establish
that CCF dispatched this provider, that the earlier state shortcut was avoided,
that bus protection completed, that control writes occurred or that other
CONSYS consumers are excluded. Those shared-OFF records and their causal join
remain required. Neither `disable_subsys()` return nor the common clock-disable
wrapper can substitute for them. No physical reads or capture hooks were added.


## Provider OFF sequence

Kind 9 now also records the dispatch and operations surrounding that loop.
The [additional header identity](results/provider-off-sources.json) pins native
`SYS_CONN=1`; the previously pinned provider supplies the key, protection mask,
control bits and exact call order. The transaction joins one `disable_subsys`
invocation and its selected CONN operation, including the two condition records.
All fields below are little-endian `u32` except explicit signed or `u64` fields.
Every record repeats the observer-assigned provider ID.

| Subtype | Fields in wire order, including subtype |
| --- | --- |
| 3, provider entry | subtype, provider, native subsystem ID, route (1 normal, 2 bring-up, 3 control-limit skip), before-off callback present (0/1) |
| 4, state decision | subtype, provider, primary raw status, secondary raw status, actual `get_state` result (0/1), decision (1 dispatch, 2 shortcut) |
| 5, CONN dispatch/key | subtype, provider, native state argument, issued POWERON_CONFIG_EN value |
| 6, protection entry | subtype, provider, requested protection mask, enable argument |
| 7, protection summary | subtype, provider, PROTECTEN input read, issued store, existing PROTECTEN verification read, reason (1 normal return, 2 count-limit fault, 3 verification fault, 4 counter overflow), condition-read count `u64`, last condition read, read-valid (0/1), helper-returned (0/1), helper status `s32` (zero placeholder when not returned) |
| 8, control stores | subtype, provider, five input-read/issued-store pairs in ISO-set, CLK_DIS-set, RST_B-clear, ON-clear, ON_2ND-clear order |
| 9, provider return | subtype, provider, CONN-operation status `s32`, `disable_subsys` status `s32` |

Dispatch/key is recorded after the native key store and before bus protection.
Protection entry precedes the selected locked helper. Its summary uses the
helper's existing input, verification and condition reads, excluding diagnostics;
a fault branch may lack a normal return and must not become success. Capture
fault information before BUG where possible, without retrying the operation.
The five control pairs preserve each actual input read independently; do not
invent readback or assume an earlier store equals the next read. Provider
return records the inner results before the void CCF callback discards them.

`check_provider_off()` requires exactly subtypes `3,4,5,6,7,8,1,2,9` with the
same provider and transaction. The normal CONN route must observe both initial
status bits set, get state ON and dispatch rather than shortcut. The CONN
operation must receive POWER_DOWN=0 and issue key `0x0b160001`. Protection must
request mask `0x60000`, issue the native OR update, see both bits in its existing
verification and terminal condition reads, and return normally with status zero.
Each control store must match its own input with the specified bit operation.
Finally the existing OFF-poll check must pass and both operation results must
be zero. Nine records occupy 1,152 bytes, including the two poll records.

Sixteen focused tests pass, including twenty-five valid-CRC provider mutations
covering mixed initial status, skipped dispatch, wrong key/mask/control stores,
incomplete protection and failed returns. Missing, repeated and reordered
sequences are refused; an isolated passing OFF pair cannot pass the provider
check. These remain consistency checks of recorded operations. They do not
prove callback effects, common-layer request attribution, other-consumer
exclusion, physical write visibility, safe release or the complete Wi-Fi cycle.
The callback-present field preserves that remaining isolation obligation rather
than treating callback presence or absence as an ownership grant. Atomic capture
hooks, common-owner joins and recovery remain unimplemented.

## Image identity and EMI coverage

Kind 7 subtypes 5–7 bind the divided-image metadata around its native section
sequence. Subtype 5 uses `<5I32s`: subtype, adapter ID, image ID, actual image
byte length, section count and SHA-256 of the actual immutable input buffer.
Subtype 6 uses `<9I`: subtype, adapter ID, image ID, section index, source
offset, length, original destination, native encryption byte and key-index byte.
Subtype 7 uses `<4I`: subtype, adapter ID, image ID and divided-loader return
status. The envelope transaction identifies the image invocation. Stop subtypes
1–4 remain separately checked; neither family substitutes for the other.

The producer must bind the hash to the actual buffer being used, not copy a
manifest hash into the record without checking the input. Describe each section
before its native operation and record loader return afterward. Hashing and
buffer immutability still need concrete producer hooks and a measured acquisition
budget. No hashing or firmware access was added to the kernel here.

`check_image_sections()` takes a separately reviewed expected hash, image size
and ordered section table. That table contains source offset, length, destination,
encryption and key-index bytes from the same independently validated image.
It is not reconstructed from the capture under test. The checker requires one
matching image invocation, exactly ordered matching descriptors, valid spans
and successful loader return. It then requires complete checked EMI operations
for every index from two onward, with matching adapter/image/section metadata,
a stable EMI base, and each operation entirely between its own descriptor and
the next descriptor or loader return. Missing or duplicate EMI indices cannot
be hidden by individually valid copies. The retained four-entry image adds six
metadata records (768 bytes), separate from its section-operation records.

Seventeen focused tests pass, including wrong expected hash/size/table, altered
section flags and identity, missing and duplicate complete EMI operations,
misplaced operations and failed loader return. This establishes only recorded
metadata consistency and EMI coverage relative to the supplied independent
metadata. The checker does not perform private-image parsing, HIF configuration
or chunk checks, START/readiness validation, ownership admission or full-cycle
classification. No device or firmware action occurred during implementation.
