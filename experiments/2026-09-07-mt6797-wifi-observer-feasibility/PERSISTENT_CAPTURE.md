# Persistent Wi-Fi capture constraints

The existing same-version Gemian pmsg storage is a possible backing store, but
the old process-context witness helper is not a suitable direct writer for all
required Wi-Fi observations. This source-only preparation selects no new memory range and admits no
physical write or recovery action. The latest
[native integration](#native-acquisition-and-raw-recovery-integration) remains
an unselected implementation with no observer/controller caller or admitted
device operation.

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

The [native hook-placement follow-up](DMA_HOOKS.md) now identifies the actual
HIF lock and reproduces the selected timeout paths. Its returned-TRUE path can
retain a mapping and lock; the separate idle-count escape can unmap without
positive idle. Hooks must preserve and identify both paths.

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

## Exclusive backing-store ownership

The [ownership source receipt](results/pmsg-ownership-sources.json) adds the
native pstore inode implementation to the pinned pmsg/ring sources. The
64-KiB pmsg zone is not owned exclusively by a prospective Wi-Fi writer merely
because that writer serializes its own calls or ordinary logging is stopped.

| Native path | Effect relevant to a capture |
| --- | --- |
| `write_pmsg()` | Ordinary userspace writes call the PMSG backend under `pmsg_lock`. The frontend ignores the backend return and reports the submitted byte count. |
| `ramoops_pstore_write_buf(PMSG)` | Writes into `cxt->mprz`; there is no capture-owner check. Console and ftrace use different zone pointers. |
| `pstore_unlink()` → `ramoops_pstore_erase(PMSG)` | Deleting the exported old-log file frees its old snapshot **and zeros the current pmsg ring's start/size**. The inode path ignores an erase error before calling `simple_unlink()`. |
| `ramoops_init_prz()` | After constructing/saving the old zone, probe zaps the current ring metadata. This is a boot-time transition, not an acquisition API. |
| `persistent_ram_post_init()` / `persistent_ram_save_old()` | Valid old data is copied into allocated RAM. Allocation failure is logged but the save function has no success return; later probe can still zap the current metadata. Recovery must establish actual preservation, not just successful probe. |

The [focused erase reproduction](test-pmsg-erase.py) compiles the three exact
native function bodies with injected storage and VFS operations. It confirms
that unlinking an old PMSG snapshot resets a distinct current-ring state. It
also confirms that returning `-EBUSY` from the backend alone leaves storage
intact but still allows the exported file to disappear. A missing erase
callback, by contrast, refuses unlink. The
[recorded result](results/pmsg-erase-test.txt) is a host reproduction, not a
concurrent, physical-persistence or hardware result. The unused-parameter
compiler exception retains the native callback signatures.

Consequently, a future default-off Wi-Fi capture owner must protect both
backend writes and erase operations for the entire admitted capture and
recovery interval. It cannot rely on chmod, removal of the character device,
absence of an observed logging process, or a capture-private spinlock. Existing
open file descriptors and the separate pstore unlink path remain relevant.
If backend refusal is selected, the frontend must preserve that refusal rather
than report a successful write or unlink; an unexpected attempt must also
invalidate the isolation result. Merely adding an erase return check is not
an ownership implementation.

The owner must be established before the first capture byte, after the exact
resolved zone, mapping attributes, ECC state and preservation of any old
unique evidence have been verified. It must remain exclusive after a failure
or overflow; resuming ordinary pmsg writes would overwrite the evidence needed
for recovery. No in-place reset, re-claim or automatic old-record deletion is
selected here. Other ramoops zones need no new ownership merely to isolate
PMSG, although their initialization and physical layout still require the
candidate's existing bounds checks.

This narrows the next implementation: a non-sleeping append path alone is
insufficient. It needs backend ownership plus refusal propagation, the already
bounded record/terminal inventory, explicit commit/readback ordering and a
reader that preserves old evidence before the native boot-time zap. The
native memory mapping can be write-combined, and its byte-copy loop supplies
no demonstrated persistence barrier or full readback. Those properties remain
unresolved; the source reproduction selects no new writer, memory range,
observer kernel, radio operation or device test.

## Native refusal propagation repair

The isolated [pstore series](patches/pstore/series) repairs the two frontend
error paths and the old-log allocation failure described below against the
pinned public native 3.18 source. The
[source receipt](results/pmsg-fixed-sources.json) pins every patch and resulting
source file; apply the series relative to that kernel's root.
It is independent of the WMT experiment patches and is not selected by any
kernel manifest or build profile. Its synthetic archive author asserts no DCO;
these patches are not submission-ready.

The write repair stops immediately on a negative backend return. A rejected
first chunk returns the error; a later rejection returns the previously
accepted byte count. Both paths release the mutex and bounce buffer. Existing
copy-from-user failure semantics are unchanged. The unlink repair returns an
erase failure before calling `simple_unlink()`, preserving the exported
record; a missing backend callback still returns `-EPERM`.

The [write test](test-pmsg-write.py) and [erase test](test-pmsg-erase.py) compile
exact source function bodies against injected operations. Each accepts the
original source directory, or `--fixed` with the repaired directory, and checks
its corresponding full-file hashes. The [recorded results](results/pmsg-repair-test.txt)
cover first, second and third chunk failures, successful and empty writes,
allocation/lock cleanup, erase rejection and normal erase. Ordered application
and reversal reproduce the pinned output and input hashes. Strict Checkpatch
reports no errors, warnings or checks with only `MISSING_SIGN_OFF` excluded for
the explicitly non-certifying archive.

This is incomplete capture preparation. Successful ordinary erase still clears
the current ring, as the fixture explicitly demonstrates. The backend owner,
interference latch, persistence/readback ordering and recovery preservation
remain unimplemented. A short userspace write cannot by itself identify why a
later chunk failed; capture isolation must rely on the future backend owner
and its failure state. No full kernel compile, boot candidate, radio operation
or device test is established by these host tests, and the closed A72 Gemian
observer line remains closed.

## Recovery allocation failure

The third patch makes `persistent_ram_post_init()` return `-ENOMEM` when a
valid nonempty retained ring has no allocated old-log copy after
`persistent_ram_save_old()`. Previously that allocation failure was only
logged; `persistent_ram_new()` returned a zone and `ramoops_init_prz()` then
cleared its current start/size fields. The caller therefore destroyed the
metadata needed to recover the old record without having copied it.

With the repair, `persistent_ram_new()` follows its existing error cleanup
and returns an error pointer. `ramoops_init_prz()` propagates the error before
its zap and before advancing the physical-address cursor. Source inspection of
`persistent_ram_free()` confirms that it unmaps the zone and frees ordinary
allocations without clearing the retained ring. The probe's failure labels
skip freeing the failed zone again. This does not fix the separate cleanup
of previously initialized zones or make a failed whole probe retryable.

The [recovery reproduction](test-pmsg-recovery.py) compiles the exact save,
post-init, new-zone and ramoops zone-initialization functions with fake mapping,
allocation, ECC and free operations. It demonstrates the old destructive
success and the repaired refusal with byte-identical retained storage, no zap,
an unchanged address cursor and released zone allocation. It also checks a
successful wrapped old-log copy and an empty ring that needs no copy, with
allocation failure both enabled and disabled. The [result](results/pmsg-recovery-test.txt)
is a host control-flow test, not evidence of persistence across physical reset.

The refusal concerns a valid nonempty header and snapshot allocation failure.
Invalid headers still follow the native reset path. ECC validation/correction
precedes the new check; the fixture models disabled ECC and establishes no
preservation guarantee for ECC repair. A future capture must verify the exact
no-ECC layout and retain malformed or partially committed evidence through a
separately reviewed reader. Successful allocation creates only a volatile copy;
it is not durable host collection, exclusive capture ownership or permission
to overwrite a previous record. No recovery image or runtime test is selected.

## Fixed metadata and ordinary recovery

The selected source-level design keeps the native ring header constant during
capture: signature `0x43474244`, start zero and size 65,524 for the exact
64-KiB no-ECC zone. These values describe the entire payload, including unused
record slots. Establish and read back that header before the first identity
record and before any observed cycle operation. The future writer then commits
only fixed 128-byte slots; it must never call `persistent_ram_write()` or update
ring start/size during capture. An interrupted payload write cannot itself tear
those unchanged ring metadata fields.

This avoids requiring a new recovery format in the ordinary Gemian pstore
reader. `persistent_ram_save_old()` copies all 65,524 bytes when start is zero
and size equals capacity. The PMSG read path selects that old copy with
`update=false`, and, with ECC disabled, exports exactly its bytes. The expanded
[recovery fixture](test-pmsg-recovery.py) confirms full-payload byte equality
through the actual save/post-init/new-zone/ramoops-init functions, including
an unfinished slot. Original and repaired source both pass this successful
allocation path; the third patch's allocation-failure protection remains a
separate prerequisite for a future revised recovery kernel. The test uses fake
memory mapping and does not establish physical retention or the live recovery
configuration.

`decode_pmsg()` in [capture-records.py](capture-records.py) implements the offline
reader for this exact exported payload. It requires the independently expected
cycle and 80-byte candidate/boot/input identity. It walks fixed slots from zero,
never searches for magic or skips a hole, and applies the existing complete
record checks to the committed prefix. A zero next slot yields incomplete
evidence. One nonzero uncommitted slot may terminate an attributable incomplete
prefix only when everything after it is zero. A damaged commit marker cannot
be distinguished from an interrupted write and therefore also yields only
incomplete evidence. A committed record with bad checksum or other invalid
fields is refused.

A recorded terminal followed by any partial or committed record is refused.
All 116 unused tail bytes must be zero. Missing identity, a shifted stream,
data after a hole, wrong expected identity and a non-exact payload length are
refusals. The reader never repairs or modifies its input. Its
`terminal-recorded` result and `producer_status` report framing and the
producer's assertion only; the separate full-cycle and resource checks still
must establish the outcome.

The [nine reader tests](test-capture-pmsg.py) cover all 127 interrupted event
prefix lengths, corruption of each of the first 124 bytes of a committed
record, all three producer terminals, identity, holes, trailing data and full
511-slot capacity. The existing 17 record tests also pass. The
[recorded result](results/pmsg-fixed-metadata-test.txt) includes the native
full-payload recovery checks.

Acquisition remains unresolved. Every payload byte must already be zero and
any previous evidence must already be preserved before this layout is admitted;
this design authorizes no clearing of a nonempty zone. The backend must exclude
ordinary PMSG writes and erases before header initialization and keep exclusion
through failure and recovery. A producer must commit/read back the body before
the final marker and preserve an interrupted slot without retry or reuse.
The exact mapping, barrier, ECC and reset-retention contracts are still needed.
Unrelated corruption of the fixed header can still defeat ordinary recovery,
and snapshot allocation alone is not durable collection. No new kernel writer,
reader image, memory access, radio operation or candidate is selected here.

## Complete-source compilation check

The existing [Buildbox object checker](check-startup-objects.py) accepts
`EXACT_PROJECT_COMMIT --pstore` to compile the original and repaired `pmsg.c`,
`inode.c`, `ram_core.c` and `ram.c` translation units. It reuses the pinned native
compiler, resolved configuration, prepared source and recorded compiler
commands, and applies only the selected pstore series to temporary files.
It leaves the prepared source untouched and removes temporary build output.
This checks a concrete gap in the function-body fixtures: compatibility with
the actual kernel headers and target compiler. It does not link a kernel,
implement capture ownership or admit a device operation.

The [completed result](results/pmsg-object-compile.json) records all three
original and patched files compiling successfully at project commit
`1f25e1cea73fc8044e914578b594b8d3d3888fc2`. Patched source hashes match the
previously reviewed repair receipt; all fifteen package files passed remote
and local inventory/checksum validation. The changed compiler logs are empty
under the recorded flags, including `-w`. Temporary output was removed and
the prepared source stayed clean. Capture ownership, its atomic writer and
physical retention remain separate implementation and runtime work.

## Boot-time PMSG exclusion

The fourth [pstore patch](patches/pstore/0004-pstore-reserve-native-pmsg-for-capture.patch)
adds default-off `ramoops.pmsg_capture=1` for a future built-in observer kernel.
It rejects ordinary PMSG backend writes and erases with `-EBUSY` before touching
current storage or the old snapshot. The first two patches propagate those
refusals to the original userspace write/unlink callers. PMSG reading and the
other ramoops zones retain their original paths.

The flag is read-only after boot. Exclusion therefore precedes backend
registration; there is no live ownership handoff, release or retry API and no
new sleeping lock in the callbacks. Capture mode refuses a modular ramoops
build and suppresses its userspace bind/unbind attributes. These constraints
avoid losing exclusion through unload/reload or ordinary driver rebinding.
They do not defend against arbitrary privileged kernel memory modification.

Read-only `pmsg_capture_denials` exposes sticky atomic bits: bit zero for a
rejected write, bit one for a rejected erase. The collector must treat any
nonzero value as interference. The bits are ordinary RAM state, not a durable
failure record; they neither prove reset retention nor replace the future
writer's committed terminal. No normal path clears them during this boot.

The [source receipt](results/pmsg-owner-sources.json) pins the original and
patched file. The [callback test](test-pmsg-owner.py) compiles the exact two
backend functions with injected storage/atomic operations and checks default
behavior, refusal without storage access, sticky bits, an absent PMSG zone,
unaffected console/ftrace callbacks and concurrent denials. Its
[result](results/pmsg-owner-test.txt) establishes callback behavior only.
Checkpatch reported zero errors, warnings and checks with `MISSING_SIGN_OFF`
excluded for the non-certifying archive; its spelling/const dictionaries were
unavailable. The first four-patch series compiled at `7764fe01bac4dc257473c3071ba851eb61a1ce8c`;
that does not establish the parameter lifetime fixed below.

This implements backend exclusion, not capture acquisition. A future writer
still must verify the exact zero payload, layout, mapping and ECC, preserve old
evidence, establish the fixed header, and commit/read back bounded slots with
the required ordering. No new reserved-memory write path, initramfs, kernel
image, radio operation or device candidate is selected by this patch.


### Parameter lifetime repair

Use the exclusion patch together with the fifth
[parameter repair](patches/pstore/0005-pstore-freeze-native-capture-parameters.patch).
The pinned native `kernfs_iop_setattr` accepts permitted mode changes, while
`param_attr_store` calls the setter without checking the original parameter
permissions. Mode 0400 alone therefore cannot establish boot-long exclusion.
The repaired capture setter refuses every change after `ramoops_init` freezes
it, before any backend/device registration. This also closes a later chmod
route. There is no unfreeze operation.

Native `parse_one` calls a matching parameter's setter without a NULL check.
The denial-mask parameter consequently has an explicit setter that always
returns `-EPERM`, instead of a missing setter. Supplying a value at boot cannot
clear the mask or call a NULL pointer. The expanded callback fixture exercises
both setter bodies, pre-freeze parsing, post-freeze refusal and denial-mask
refusal; the source receipt also pins the three parameter/kernfs files.
The [final five-patch compilation](results/pmsg-owner-object-compile.json)
passed at `f65e32bf830e65da70d286f279d59003edab3df2`: all four original and
patched translation units compiled, their source hashes match the reviewed
inputs, and all nineteen package files passed remote and local validation.
The recorded flags include `-w`; this is target/header compatibility, not a
warnings-enabled or full-kernel-link result. Temporary output was removed and
the prepared source remained clean. Neither version was selected or executed
on the Gemini.

## Fixed-slot writer implementation

[capture-slot-writer.h](capture-slot-writer.h) implements the WFC1 byte writer
as an isolated C prototype. It has no kernel caller or physical mapping and is
not part of the pstore patch series. The remaining integration must acquire
the exact PMSG zone under the boot-long exclusion above, preserve old evidence,
verify the fixed header and no-ECC layout, and serialize every call outside
NMI context. A zero-initialized ordinary-RAM state permits one begin attempt;
there is no retry, reset, clearing or ownership-release function.

The [mapping receipt](results/capture-writer-sources.json) resolves the native
source choices. With memtype zero, both `pgprot_writecombine()` in the vmap
branch and `ioremap_wc()` in the I/O branch select `MT_NORMAL_NC`. Nonzero
memtype selects different Device attributes in those branches and is outside
this prototype's intended integration contract. Source selection does not
prove a live page-table mapping, absence of conflicting cacheable aliases or
DRAM retention. Native ARM64 `mb()` expands to `dsb(sy)`; `mmiowb()` is empty
and is not a replacement. The writer uses explicit byte I/O and full barriers,
without allocation, sleeping locks, ring operations or cache-maintenance calls.

Begin reads all 65,524 payload bytes, including the unused tail, and refuses
any nonzero byte without writing. On admission it writes the identity as slot
zero. Each append constructs its own sequence, envelope, CRC and marker in a
128-byte stack buffer, then consumes the attempt before inspecting its target.
It checks all 128 target bytes for zero; writes the 124-byte body; executes a
full barrier; reads back the entire body and still-zero marker; executes a
full barrier; writes the four marker bytes; executes a full barrier; and reads
back all 128 bytes followed by another full barrier. A mismatch stops the
writer permanently without repair or a later terminal attempt. Successful
readback alone advances the sequence. All reads in each verification pass
complete even after a mismatch.

After 510 ordinary records, the next otherwise valid event request writes a
producer-overflow terminal in slot 510 and returns `-ENOSPC` only after its
successful readback. An explicitly requested terminal can use that slot or an
earlier slot. Every terminal closes the writer. Envelope argument failures
also close it without storage access. Payload-specific lifecycle validation
remains with the typed producers and existing reader; this primitive does not
interpret DMA, power or firmware results.

The [host test](test-capture-writer.py) compiles the exact header with injected
byte I/O and checks its output against the independent Python codec/decoder.
The [eight test groups](results/capture-writer-test.txt) cover all 128 event
store interruption points, all 256 body/final readback fault positions, every
lost nonzero event-byte store, every nonempty target-byte position, nonempty
admission including the unused tail, exact operation ordering, invalid arguments
and full capacity. Every failure checks that later event, terminal and begin
requests make no further stores. These tests model program order and byte
faults; they do not simulate ARM memory ordering, concurrent callers or reset.

A reset after the last marker store can leave a complete record even before
the function returns. Conversely a final-readback failure may leave complete
bytes. The reader therefore still reports framing and producer status only;
neither a marker nor the writer's volatile state supplies an independent
success or isolation verdict after reset. A future controller must join the
capture with its admitted watchdog/recovery and interference evidence.

The existing object checker accepts `EXACT_PROJECT_COMMIT --capture-writer`.
It compiles the header with emitted wrappers in the original native
`ram_core.c` translation unit, using the pinned compiler/configuration and
retaining disassembly. This checks native headers and generated code without
integrating a caller. The [target result](results/capture-writer-object-compile.json)
passed at `2196a566e2d303c6fd7a2c74d49cdf712b1b2803`, with all eight package
files validated remotely and locally. Disassembly contains the six full
barriers in append and two in begin, byte load/store loops, and the append
state advance after final readback. Its observed 224-byte append frame excludes
callee and future integration stack usage. The recorded compiler flags include
`-w`; this is not warnings-enabled validation or a full kernel link. Strict
Checkpatch on the header reported zero errors, warnings and checks with its
spelling/const dictionaries unavailable. Acquisition, header initialization,
producer integration and physical retention remain unfinished; this prototype
admits no reserved-memory access or device operation.

## Native acquisition and raw recovery integration

Pstore patches 6–8 in the [series](patches/pstore/series) integrate the reviewed
writer into the native backend. They add built-in `ramoops_capture_begin()`
and `ramoops_capture_append()` entry points; no observer or controller calls
them yet. The [source receipt](results/capture-integration-sources.json) pins
the five-patch parent, new patches and resulting files. The installed writer
header is byte-identical to the tested prototype. This remains a synthetic,
non-certifying experiment archive, not an upstream submission or candidate.

The original native DT reservation has no `no-map` property. Native ARM64
`pfn_valid()` tests membership in `memblock.memory`, and the normal ramoops
constructor can create a non-cached vmap while a linear RAM mapping remains.
Patch 8 splits only the existing reservation: the first `0xd0000` bytes remain
at `0x44410000`; the final `0x10000` bytes at `0x444e0000` receive `no-map`.
Their union remains `0x44410000..0x444f0000`. Configured ramoops sizes and all
physical zone boundaries stay unchanged. This DT is intended only for the
isolated capture/recovery kernel with capture mode enabled.

Before initializing any zones, capture-mode probe requires the exact native
base, total size, record/console/ftrace/PMSG sizes, memtype zero and all-zero
ECC settings. An atomic one-attempt guard refuses a second capture probe even
after failure. The PMSG constructor then checks the exact `0x444e0000` address,
64-KiB size and page alignment, and refuses if **any** page remains a valid RAM
PFN. It requests the region and uses `ioremap_wc()` directly. It never enters
the generic ring constructor, ECC initialization or metadata zap, and does not
switch the other zones' ring-update callbacks.

The new constructor allocates a complete 64-KiB old snapshot and copies every
raw byte, including the header, before pstore registration. Allocation or
mapping failure releases resources without changing retained bytes. Patch 6
also replaces the probe failure labels' structure-only frees with the existing
zone destructor, releasing mappings and snapshots without zapping storage.
Its dump-array cleanup saves the actual count before clearing it, stops at
that count instead of assuming a missing sentinel, and clears the freed pointer.
Malformed or interrupted headers therefore remain available as raw evidence
through the existing PMSG old-log reader when capture-mode probe succeeds.
In this mode the exported file is **65,536 bytes including the header**;
ordinary Gemian's 65,524-byte payload export remains a different input format.

Begin is process-context only and consumes its one attempt under a raw spinlock.
It requires completed backend registration, frozen capture mode, valid identity
arguments and no recorded PMSG interference. Both the entire current raw zone
and its initial snapshot must be zero. A nonempty snapshot forbids admission
even if an outside actor has cleared current memory; no clearing operation is
provided. Begin writes start/size, verifies all twelve header bytes with the
signature still zero, writes the signature, and verifies the complete fixed
header. Only successful readback reaches the identity writer. Interruptions
and errors cannot trigger another begin or a later payload write.

Append uses the same raw spinlock and rejects NMI context. It checks the sticky
ordinary-write/erase denial mask before and after the slot writer and closes
capture on interference. This serializes supported producers but does not make
the denial mask persistent: a denial racing a write can leave committed bytes,
and a denial after a terminal cannot be inferred from that terminal after reset.
The existing framing-only interpretation is unchanged. A durable isolation
result remains a controller/recovery requirement before hardware admission.

`decode_pmsg_zone()` in the [codec](capture-records.py) accepts the raw snapshot
only at exactly 64 KiB, checks all fixed header fields, then uses the existing
payload decoder and independently expected cycle/candidate/boot/input identity.
It rejects malformed headers without repairing or resynchronizing data; the
collector must retain the original raw snapshot even when decoding fails.

The [integration fixture](test-capture-integration.py) compiles the exact native
mapping, preparation, zone-initialization, owner and destructor functions with
injected allocation/I/O and a host lock. Its
[twelve test groups](results/capture-integration-test.txt) cover raw
malformed-header preservation, all sixteen RAM-PFN refusals, allocation and
mapping cleanup, exact range refusal, every header-store interruption and every
header-readback fault, old-snapshot admission refusal, interference, concurrent
append ordering, bounded dump-array cleanup, and a simulated recovery snapshot
that refuses reuse. The
raw-reader test additionally rejects all 96 single-bit header mutations.
These are control-flow and byte-preservation tests, not ARM spinlock, physical
retention, live page-table or interrupt-context evidence. The full probe's
guard/publication placement is inspected separately from the extracted fixtures.
Strict Checkpatch passes with three explicit exclusions: synthetic archive
sign-off, the new file's maintainer-inventory reminder, and the modern
`kzalloc_obj` recommendation unavailable in the native 3.18 API. The script's
spelling/const dictionaries are unavailable.

At the initial integration below, the `--pstore` object check applies eight
patches, checks the native header dependencies, retains both capture disassemblies, and compiles
the complete native board DT before and after the split using the pinned DCT
output. It requires only the one existing `reg` change and the new PMSG `reg`
and `no-map` properties. The [validated Buildbox result](results/capture-integration-object-compile.json)
passes for clean published input `2747ee92b47402b2d88293380d77e7834a16094b`:
four original and four patched translation units compile, and the full board
DT comparison finds exactly those three property changes. The reservation
table and boot CPU identity also remain unchanged. All 25 package files pass
remote and local checksum verification; the prepared source remains clean.

The emitted capture entry points contain the native IRQ-save lock pairs, and
the mapping, header preparation and slot writer retain their ordered `dsb sy`
sites. Recorded stack sizes are individual function frames, excluding callees
and future controller nesting. C compilation retains the native commands'
`-w`, so empty diagnostics do not establish warning cleanliness. Both DT builds
report 211 inherited warnings, identical after normalizing only file names and
source locations. This is object compilation and DT comparison, not a full
kernel link, binding-schema validation or hardware test.
Physical zero-state preparation, typed observer/controller callers, durable
interference evidence, the watchdog contract and reset retention remain open.
No kernel image, boot selection, memory access or radio operation is admitted.


## Rejected-access tail markers

[Patch 9](patches/pstore/0009-pstore-retain-rejected-capture-access-in-tail.patch)
addresses one loss of evidence: an ordinary PMSG write or erase rejected after
a recorded terminal previously left only a volatile denial bit. The capture
owner now reserves the first two bytes of the existing 116-byte unused payload
tail for one rejected-write and one rejected-erase marker. These are payload
offsets 65,408 and 65,409, raw-zone offsets 65,420 and 65,421, physical addresses
`0x444eff8c` and `0x444eff8d`. They are inside the already selected 64-KiB zone;
slot count, slot contents and ring metadata remain unchanged.

The marker pointer becomes available only after successful full-zone zero
admission and fixed-header readback. Earlier denials still prevent begin and
perform no retained write, including when recovery has mapped nonempty old
storage. Each callback consumes its atomic denial bit before waiting for the
same raw spinlock used by begin/append. Under that lock it closes the writer,
checks its byte, and preserves any nonzero value. A zero byte receives one
`0xff` store with ordered readback. Failed readback returns `-EIO`; ordinary
rejection and repeated calls return `-EBUSY`. There is no marker retry, clear,
repair or ownership release, even after a failed store or an outside clear.

The two process-context routes remain native `write_pmsg()` and
`pstore_unlink()`, with the input hashes already recorded in the
[initial object result](results/capture-integration-object-compile.json).
The new helper runs below the former's mutex; it calls no generic pstore path,
allocation, logging or sleeping operation while holding the capture lock.
It is not an NMI interface. Normal-mode callbacks remain unchanged.

This adds at most **two byte stores per boot after acquisition**, including
denials after a terminal. A full capture plus both markers therefore has at
most 65,422 byte stores: twelve header bytes, 511 complete 128-byte slots and
two tail bytes. Each marker adds at most two byte reads and four `dsb sy`
barriers; an already nonzero byte needs only one read and two barriers. The
emitted native ordering is checked below; physical validation remains open.

The existing reader rejects every nonzero tail, so no decoder relaxation or
new successful record type is introduced. The raw recovery snapshot preserves
the complete marked zone. A nonzero marker is a reason to reject the capture,
not an authenticated account of which actor ran; retain the original bytes.

The [expanded eighteen-group fixture](results/capture-denial-tail-test.txt)
retains the twelve acquisition tests and adds both post-terminal markers,
raw recovery and refusal to reuse, pre-acquisition preservation, repeated
concurrent denials with the two-store bound, nonempty-marker preservation,
read/write faults without retry, and a denial latched while the terminal writer
holds its lock. That deterministic interleaving joins the blocked denial only
after the writer releases the lock, then requires the terminal's `-EBUSY` and
the recovery reader's tail refusal. The injected host lock and memory do not
establish native interrupt or physical persistence behavior.

**A zero tail still cannot certify isolation.** Reset before the marker store,
a dropped store, or a false nonzero initial read can leave a framing-valid
terminal without a marker. The fault fixtures explicitly preserve that
counterexample. Even a successful readback is not physical reset-retention
proof. The controller must still establish the bounded observation interval,
account for in-flight actors and join admitted watchdog/recovery evidence;
these markers do not replace those requirements.

The [successor Buildbox result](results/capture-denial-tail-object-compile.json)
passes from clean published input `bd08277b6b3059cc03c0dd7784cec9826caa998c`
with all nine patches: four original and four patched complete translation
units compile, and all 25 package files pass remote/local checksum verification.
The helper's emitted code has its atomic attempt before the native IRQ-save
lock, the four `dsb sy` sites, one conditional byte store and the `0xff` readback
comparison. Both native callbacks call it with their distinct bit indices.
The helper's own stack frame is 48 bytes, excluding callees and enclosing
pstore calls. Begin publishes the tail pointer only after prepare succeeds.
Both full board DTBs are byte-identical to the initial integration's pair;
they still emit 211 inherited warnings each. C compilation still uses the
native `-w` commands. No full kernel link, DT schema check or device execution
was performed. No controller, boot candidate, clearing protocol or device
action is selected.

## Built-in producer activity query

[Patch 0010](patches/pstore/0010-pstore-expose-native-capture-activity-to-built-ins.patch)
adds the unexported `ramoops_capture_active()` query for the
[native DMA producer](DMA_HOOKS.md#native-producer-implementation). It returns
false outside capture mode or in NMI context. Under the existing IRQ-save raw
spinlock it requires the registered backend, acquired payload, begun writer,
no stopped state and no denial latch. It changes no retained bytes and grants
no reservation: every append must pass its own admission checks. The existing
18-group native-integration fixture now also requires false before begin and
after closure, and true after successful acquisition. Target compilation of
this tenth patch remains pending; the nine-patch receipts above are historical.
