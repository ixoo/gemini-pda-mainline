# Connected ordinary-section CONFIG and PDA submission

[`hif_ordinary_section.h`](src/hif_ordinary_section.h) composes the accepted
CONFIG request/ACK phase and finite PIO primitive into one ordinary-section
flow. It uses the [corrected credit pools](INIT_CREDIT_CORRECTION.md): CONFIG
debits TC4; the PDA chunks debit neither TC4 nor START's TC0. It makes no
claim of kernel or hardware admission.

## Selected source admission rules

At Planet `c5b0be85017ad0c599725e8273842efdbecdd88a`, selected gen3
`wlanImageSectionDownloadStage` calls CONFIG and enters its payload loop
only after success. The selected ACK option makes that a matching CONFIG
CMD_RESULT success. `CMD_PKT_SIZE_FOR_IMAGE` is 2048 bytes. The separate
`wlanImageSectionDownload` constructs an eight-byte header plus a bounded
chunk and calls `nicTxInitCmd` directly: no `nicTxAcquireResource`, per-chunk
sequence allocation, returned-credit processing or ACK wait occurs there.
`nicTxInitCmd` supplies aligned bytes to WTDR1 through the existing port path.
These call sites establish the software transport admission used here:
successful CONFIG, retained owned/serialized transport, and bounded PDA
submission. They do not establish additional hardware FIFO credit semantics.
No undocumented ready register or speculative debit is inserted.
[Ordering and chunk sources](results/config-phase-sources.json),
[PIO transport sources](results/pio-sources.json).

PDA has declared count `8 + chunk`, queue `0xc000`, CID 0, type `0xa0` and
sequence 0. The original component initializes the reserved header byte to
zero; the audited PDA constructor does not explicitly assign it. This is
deterministic initialization policy, not a claimed firmware validation gate
or an observed packet byte. Payload is copied without reinterpretation.
PIO supplies zero padding beyond the logical packet. For 2048 payload bytes,
logical size is 2056 and the accepted block policy transfers 2560 bytes.
The extra bus bytes are not charged as payload or as INIT command pages.

## Coherent bounded API

The caller supplies an already-validated immutable ordinary section, its
matching CONFIG record and independently expected CONFIG sequence. It retains
that data and the transaction/resources across the entire section. This API
does not parse firmware, authorize a destination, decrypt bytes or infer an
EMI classification. State must be zero-initialized and structures/buffers
valid, distinct and stable. There is no allocation or file access.

1. `mt6797_section_begin` explicitly requires `MT6797_SECTION_ORDINARY`;
   EMI and unknown kinds are refused before I/O. It requires CONFIG's section
   length to equal the supplied validated byte span, then invokes the real
   CONFIG composition. It retains the data span and enters CONFIG-pending.
2. `mt6797_section_ack` reuses the connected 32-byte read/28-byte validation.
   Zero reported length remains pending without I/O. Only matching success
   enters payload phase. The shared transaction enters INIT_PAYLOAD so START
   or another CONFIG cannot interleave; attempts poison state.
3. Each `mt6797_section_next` submits exactly one chunk, the smaller of 2048
   and remaining section bytes. It builds its header in caller scratch and
   calls the real encoder/PIO path. Scratch must cover the encoded padded
   span (at most 2560 bytes) and must not overlap section data or state. No
   new transport seam is introduced. The caller checks its deadline and
   ownership between these finite calls; no unbounded loop exists here.
4. Only a successfully returned PIO submission advances `submitted`. Any
   reported failure poisons both section and transaction; no retry, refund,
   rewind or recovery cursor is offered. A failed operation may already
   have side effects. Invalid scratch/capacity or illegal phase also fails
   the section before more I/O. The owner uses `mt6797_section_fail` on
   timeout/ownership loss and keeps responsibility for safe recovery.
5. After the exact byte span is submitted, state becomes SECTION_SUBMITTED
   and the transaction returns to IDLE for the image owner's next phase.
   Another `next` is refused; it never creates an empty chunk.

SECTION_SUBMITTED means ordinary bytes were submitted, not that firmware
validated or executed them. No PDA ACK is fabricated. The existing CONFIG
sequence-history policy remains stricter than the vendor wrapping allocator;
PDA sequence zero is framing and does not consume that history.

## EMI and final START remain explicit image-owner boundaries

An EMI entry is an error to this function, never success or a skipped entry.
The image owner must route it to separately admitted EMI handling and account
for every required section. SECTION_SUBMITTED does not imply all ordinary
sections, EMI work, patch dependencies or the whole image are complete.
Although the shared transaction becomes idle, its caller must not issue START
until the full validated image plan is complete. This component deliberately
has no global `image_ready` or `start_allowed` output. The existing START
primitive/readiness logic remains available only at that separately owned
boundary. Shared power/EMI/ownership, real register access, timed waits and
recovery are still kernel-adapter requirements.

## Integration validation

The [fake-flow fixture](src/hif_ordinary_section_test.c) uses a 2049-byte
synthetic section, checks literal CONFIG and PDA command/data words, the
2048+1 split, zero block/word padding, exact FIFO offsets, and no intervening
PDA reads or ACKs. Complete CONFIG plus both chunks takes 660 scalar I/O
operations. Each of those 660 operations is independently failed; execution
stops at that operation, poisons state and retains CONFIG's debit. TC4 ends
at 103 and TC0 stays 104 throughout. Tests also cover explicit EMI refusal,
length mismatch, payload before ACK, insufficient padded scratch, duplicate
submission and attempted START during payload. Corrected pool-exhaustion and
connected-CONFIG fixtures pass again with strict C11, ASan and UBSan.
No device/backend action, new firmware permission or feature push is included.

## Coordinator integration review

Project Planning reviewed the five-file `2d9983c7` delta and applied it on
the independently corrected credit model, preserving the extra cross-command
sequence test from integration. Strict C11 warnings and ASan/UBSan passed
the complete two-chunk flow and all 660 individual I/O failures. Corrected
credit/sequence and connected CONFIG fixtures also passed. The integrated
repository gate passed 192 profiles with unchanged metadata debt of 37.

This accepts ordinary-section host composition only. A separate compile-only
Linux integration is assigned to check the actual kernel include paths and
ordered MMIO adapter without registering or probing hardware. Whole-image
plan completion and EMI ownership remain explicit implementation work; no
ordinary-section result permits premature START or a live firmware write.
