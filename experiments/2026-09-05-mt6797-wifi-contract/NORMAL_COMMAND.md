# Normal capability and NVRAM commands

[`normal_command.h`](src/normal_command.h) implements original bounded
serialization/transaction/reply helpers for the pinned gen3 capability query
and SET_NVRAM_SETTINGS. It reuses the fixed-port HIF encoder, not INIT framing
or INIT credit admission. It performs no I/O itself. Synthetic tests compose
it with the unchanged PIO primitive; no firmware or calibration input is read.

## Pinned wire and resource contract

All source references below use Planet
`c5b0be85017ad0c599725e8273842efdbecdd88a`, gen3.
[Ten exact source-file identities](results/normal-command-sources.json).

| Boundary | Selected source and consequence |
| --- | --- |
| Command header | `nic_cmd_event.h:294–303`, `hif_tx.h:48`: eight bytes, LE byte count/PQ ID, CID, packet type, set/query, sequence. Queue is `0x8000`, packet type is constructor constant `0xa0`; the structure's `0x20` comment is stale. |
| Capability query | `wlan_lib.c:3726–3773`: CID `0x80`, query=0, response required. Actual allocated/transmitted logical length is header plus capability structure, **124 bytes**, not an eight-byte query. |
| Capability request tail | Constructor fills only the header. `cmd_buf.c:178` uses `cnmMemAlloc`; `cnm_mem.c:345–346` returns pooled memory without clearing on that path, while fallback allocation is cleared at 358–360. This helper deliberately zeros all 116 unused query bytes, rather than reproducing uninitialized memory. Firmware acceptance remains a runtime question. |
| NVRAM | `wlan_lib.c:4240–4249`, `wlan_oid.c:7716–7786`: CID `0x48`, set=1, no response requested, exactly 512 payload bytes; total **520 bytes**. Generic constructor copies that payload and queues it. Queuing is not firmware application. |
| Resource class | `wlan_lib.c:1325–1336`, `nic_tx.c:781–805`: GENERAL_IOCTL capability and NETWORK_IOCTL NVRAM both use **normal TC4**. |
| Page charge | `nic_tx.c:2645–2690`: both call the include-descriptor path, adding no separate descriptor; charge `ceil(logical_bytes/128)`. Capability costs **1**, NVRAM **5**. HIF block padding is not charged as eight pages. |
| Normal admission | `wlan_lib.c:518–523` calls the normal resource reset before capability. The function named `wlanQueryNicResourceInformation` at 5214–5222 contains no query; it calls `nicTxResetResource`. That resets from configured quotas (`nic_tx.c:674–677`). |
| Default versus actual quota | `nic_tx.h:55,62,98–104` gives a default TC4 quota of 2 × 13 = **26 pages**, distinct from INIT's 104. `wlan_lib.c:5485` allows `Tc4Page` configuration. No default or reset is performed by this helper: an actual owner supplies normal limit/free pages explicitly. |
| Normal transmit | `nic_tx.c:1805–1837` rounds logical command size to four bytes and writes the normal command directly to TX port. For these already aligned records, byte count remains 124/520. HIF PIO sizes are 124/1024. |
| Capability reply | `nic_cmd_event.h:307–315,496–516`: eight-byte event header plus 116-byte capability body, event ID 1, packet type `0xe000`. No response-status byte is defined. |
| Reply port/staging | `wlan_lib.c:3775–3789`, `nic_rx.c:3635–3708`: port 1, WRPLR high half. Selected extra-four-byte read stages **128 bytes**, preserving logical length 124. Proper HIF logical-register access is required; this helper accepts the supplied port-1 length, not a raw MMIO mapping. |

Both normal constructors use the adapter's `nicIncreaseCmdSeqNum`, shared with
INIT. The helper accepts a caller-owned 32-byte sequence-use bitmap without
clearing it; INIT and other users must retain/share the same session history
under serialization. Refusing reuse instead of allowing vendor eight-bit wrap
is deliberate bounded-session policy, not a source claim about no wrap.

## Helper API and bounds

Zero-initialize `mt6797_normal_transaction`, then call `mt6797_normal_admit`
with the actual normal TC4 limit/free count and shared history. This requires
an explicit post-START resource context; it cannot consume `free_pages` from
an INIT transaction merely because both name TC4. Limit is bounded to the
source's 16-bit page accounting, free must not exceed limit, and a repeated
admission poisons state. No replenishment, release-counter parser or reset is
provided. Ordinary active users must not race this bounded transaction.

`mt6797_normal_prepare` serializes capability from IDLE, then NVRAM only after
a matching capability reply. It checks sequence, exact payload contract,
capacity and credit before changing output/history or debiting pages. Output
and immutable payload/state/history must be distinct. Capability requires no
caller payload; NVRAM requires exactly 512 bytes, not the storage trailer.
The prepared HIF word/span is returned alongside a zero-padded frame. No
calibration values are generated and the payload is copied byte-for-byte.

`mt6797_normal_submitted` accepts the actual transport outcome. Capability
moves to WAIT; NVRAM moves to NVRAM_SUBMITTED with no ACK expectation. A failed
transport permanently poisons state without refund. Serialization/resource
refusals before submission consume no new pages or sequence. A caller deadline,
ownership loss or RX failure must call `mt6797_normal_abort`.

`mt6797_normal_reply_span` accepts only logical port-1 length 124 and stages
128; zero returns EAGAIN, malformed/nonmatching length poisons the transaction.
The caller owns deadlines and proper logical WRPLR acquisition. The helper
never polls or reads a register itself.

`mt6797_normal_accept_capability` takes the exact 124 logical bytes, validates
length/type/event/expected sequence and returns only product, firmware own/peer
versions, hardware-5GHz-disable, EEPROM-used and RF/BB-calibration-failure fields.
MAC, date and reserved bytes are neither exported nor validated as a signature.
Reserved bytes need not be zero. The exact length and sequence checks strengthen
the vendor query, which checks packet type/event but omits those checks here.
The strict size is for this pinned ABI, not automatic support for an extension.

Nonzero RF/BB failure flags remain parsed observations; valid framing is not
successful calibration. EEPROM-used likewise is not factory provenance.
NVRAM_SUBMITTED means only successful transport submission, not an invented
NVRAM-applied ACK or calibration measurement. Firmware/board applicability and
upstream regulatory integration remain in
[CALIBRATION_APPLICABILITY.md](CALIBRATION_APPLICABILITY.md).

## Synthetic validation and integration

[`normal_command_test.c`](src/normal_command_test.c) composes preparation,
submission, actual PIO RX and reply parsing with a fixed fake bus. It checks
literal command/setup/FIFO words and zero padding across all 322 callbacks:
32 capability writes, 33 reply setup/reads, 257 NVRAM writes. All 322 injected
failure positions stop at the failing call and retain the correct debit
(25 or 20 of an explicitly supplied 26-page normal pool).

Tests cover all 65,536 logical RX lengths, undersized staging, all first-six-header-byte
mutations and ignored-private-field mutations, exact reply lengths, unknown/missing contexts, immutable synthetic
payload copy, NVRAM lengths, shared INIT/normal sequence reuse, insufficient
credit, no ACK after NVRAM, malformed/missing replies and read/submit failure.
Literal capability fields include nonzero calibration-failure reports and
noncanonical flag values, proving these are returned data rather than invented
calibration approval. [Validation receipt](results/normal-command-validation.txt).

Build and run the linked C test with strict C11, warnings-as-errors and
ASan/UBSan inside a managed temporary directory with an immediate cleanup trap.
The kernel include branch is not separately compiled here. No kernel build,
backend, actual resource reset, query, radio operation or firmware write occurs.
The HIF private-core worker received the independent normal-resource/API scope;
seven frozen protocol headers and its INIT-core API remain unchanged. This
helper is ready for a future real normal-command transport owner, not connected
to the currently INIT-only core by a fake ownership flag.

## Coordinator review

The coordinator reviewed `dc10d4e8` and independently compiled and executed the
actual test under strict C11, ASan and UBSan with sanitizer recovery disabled.
The literal PIO trace, all 322 injected transfer failures and 65,536 reported RX
length cases passed. Review checked exact output bounds, pre-debit refusals,
sequence-history preservation, failure poisoning and the absence of an invented
NVRAM acknowledgement. No blocking defect was found within this helper scope.
This host result does not validate kernel compilation or firmware acceptance.
