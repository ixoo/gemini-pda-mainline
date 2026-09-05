# MT6797 gen3 DOWNLOAD_CONFIG and command-result model

This bounded slice implements pure decoders and a validator for **one**
already-delimited logical DOWNLOAD_CONFIG command and its CMD_RESULT reply.
It adds no transport, file reader, packet builder, transmitter, firmware
loader, retry loop or device operation. The public implementation is
[`wifi_init_protocol.py`](scripts/wifi_init_protocol.py); its
[synthetic tests](scripts/test_wifi_init_protocol.py) use no retained firmware
or runtime packets.

Status on 2026-09-05 UTC: implemented; 36 tests pass. This is a source-based
reference model for a future driver, not hardware acceptance. The preceding
[firmware format audit](FIRMWARE_FORMAT.md) establishes the selected gen3
source and the retained MTKE file's metadata. Neither that result nor this
model proves a packet exchange occurred on Gemini.

## Exact selected source

All references below use Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a` and the selected
`drivers/misc/mediatek/connectivity/wlan/gen3/` path. The inspected C files
have GPL version 2 notices. The model is independently written from their
field layout and behavior; no vendor implementation or packet bytes are
copied into the repository.

The command header is eight bytes: byte count and queue ID as 16-bit words,
then command ID, packet type, reserved byte and sequence as bytes. Its
DOWNLOAD_CONFIG body is twelve bytes containing address, length and mode as
32-bit words. The model decodes these words as little-endian. The selected
constructor writes command ID 1, queue `0x8000`,
packet type `0xa0`, its sequence and a zero reserved byte. A nearby structure
comment says `0x20`; the assigned constant and constructor are the stronger
evidence, so the model refuses `0x20`.
[Header and constants](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_init_cmd_event.h#L51),
[selected constructor](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L2401).

For MT6797, the eight-byte event header precedes a **twenty-byte** result
body, for 28 logical bytes total. The generic branch has a shorter result
body and must not be substituted. The header declares event packet type
`0xe000`, event ID and sequence. The MT6797 body carries status, reserved
bytes, PSE FID, a key-index byte and a source-descriptor structure. The model
does not interpret or emit those diagnostic values.
[MT6797 event/result layout](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_init_cmd_event.h#L124).

The selected configuration enables download acknowledgements. The verifier
requires event ID 1, the outstanding command's sequence and status zero;
all nonzero statuses fail. It does not compare the result's diagnostic
source descriptor with the command or require response reserved bytes to be
zero. These fields therefore do not become invented validity gates here.
[ACK selection](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/config.h#L492),
[reply verifier](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L2769).

PDA payload transfers use queue `0xc000` with a different construction path;
they are not DOWNLOAD_CONFIG commands. The model explicitly distinguishes
and refuses that queue. It does not invent an ACK per PDA chunk, decode a
PDA payload, or reuse the earlier gen2 DOWNLOAD_BUF framing.
[PDA transfer construction](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L2512).

## Logical-record boundary and stricter model checks

This is not an STP, physical SDIO, AHB register or DMA-stream decoder. The
caller must supply immutable bytes representing exactly one source-level
logical command or reply. The source TX helper rounds the transfer length
to a word boundary; a 20-byte DOWNLOAD_CONFIG already has that alignment.
The RX helper obtains a length from the receive port. In its optional
extra-read mode it reads additional bus bytes and copies only the reported
packet length to the response buffer. The model does not accept those extra
bytes or try to infer where a logical record begins.
[TX helper](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_tx.c#L2259),
[RX helper](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c#L3615).

| Check | Basis and behavior |
| --- | --- |
| Command exactly 20 bytes, reply exactly 28 bytes | Conservative model policy for the selected layouts; not an observed live packet length |
| Declared byte count equals supplied logical length | Added consistency policy; the shown vendor ACK consumer does not make this check |
| Command queue, ID and packet type | Exact selected constructor values |
| Response packet type `0xe000` | Source-declared type enforced as model policy, beyond the shown ACK consumer |
| Event ID 1 and exact expected sequence | Source ACK verifier behavior |
| Sequence in 0–255, including zero | Byte-sized field; the caller provides the independently expected value |
| Command reserved byte zero | Explicit selected-constructor assignment |
| Response reserved bytes | Report only whether zero; do not reject nonzero values |
| Address plus length does not overflow a 32-bit range | Added conservative modeling policy; no destination whitelist or permission is inferred |
| Length nonzero | Zero-length source call returns without constructing a command |
| ACK requested | Required by the selected ACK-enabled configuration and this exchange's scope |
| Known mode bits only; key-selector bits require encryption | Matches the selected constructor's mode construction |
| Reply PSE FID, key-index and source descriptor | Uninterpreted, neither printed nor compared as a fabricated echo contract |

Mode decoding exposes only encryption/reset/ACK booleans. The encoded key
selector, destination address and reply diagnostic values never appear in
returned metadata. The source can reset download state for the first section
or continue a later one; the model records the reset flag without pretending
to know the section's position in a future transaction.

A nonzero firmware status is a well-formed failure result, not automatically
a malformed packet. Source-defined status values 1–4 are reported as invalid
parameters, CRC error, decryption failure and unknown command. Other nonzero
values are reported as `other_failure`; the model does not apply the generic
branch's extra comments as MT6797-specific status meanings.

The two input lengths cap an exchange at 48 bytes. There are no reads,
allocations proportional to a supplied section size, loops over untrusted
counts, timeouts, retries or discovery. A pending exchange, absent reply or
transport timeout remains a future transport-owner concern.

## API and results

The public pure functions are:

- `decode_download_config(packet, expected_sequence=...)`;
- `decode_command_result(packet, expected_sequence=...)`;
- `validate_download_config_ack(command, response, expected_sequence=...)`.

All receive already-delimited immutable `bytes`; the expected sequence is a
required integer keyword argument. Malformed or out-of-scope input raises a
`Refusal` containing only a fixed reason code. Decoders return sanitized
metadata. The pair validator returns `source_contract_match` for matching
success or `firmware_rejected` for a matching nonzero status. It always
reports `runtime_protocol_match=unproven`, `hardware_access=false` and
`load_authorized=false`.

Matching an eight-bit sequence is not authentication or replay prevention
after wraparound. A future transport must serialize outstanding commands,
attribute records to the correct power/firmware session and enforce its own
finite observation deadline. The model accepts no batch, resynchronization
search, fallback format or alternate event ID.

The executable entry point only prints the static contract. Every argument
is refused without echoing its value; there is intentionally no packet or
path input on the command line:

```sh
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/wifi_init_protocol.py
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_init_protocol.py
```

## Validation and handoff

All 36 synthetic tests pass. Coverage includes every short command/reply
length, appended transport bytes, declared-length mismatches, PDA distinction,
the contradictory `0x20` comment, wrong queues/IDs/types, command and reply
sequence mismatches, sequence boundaries, invalid caller types, every
unrecognized mode bit, missing ACK policy, key-selector construction,
address overflow, all 255 nonzero firmware statuses, advisory response
reserved fields, uninterpreted diagnostic data and no CLI file access.

The next driver-design handoff is this fixed record contract plus the
separate [shared-EMI/remap/MPU ownership analysis](OWNERSHIP.md). Before any runtime reuse,
prove logical-record extraction and source applicability against the exact
selected image and firmware session. A synthetic match does not justify
sending DOWNLOAD_CONFIG, starting Wi-Fi or choosing a device candidate.

## Immutable source identities

SHA-256 values below identify the raw source files at the pinned commit.
Paths are relative to the gen3 directory named above.

| Source | SHA-256 |
| --- | --- |
| `include/nic_init_cmd_event.h` | `46f8490382ae71485dfb4f106d9e53735ec66ef662b97a12810362309eae7a56` |
| `common/wlan_lib.c` | `56bf99536fcb96de5a5198943aec96c9efccb8af89261b29c62046e6560c422f` |
| `include/config.h` | `c773b8e5e07978d60565c2eeee976dae3e285ecb9152062fe3bb50b1358a1c32` |
| `nic/nic_tx.c` | `1f479d41bab8e2b5bba68eb6514f3e977559d31d97c39c7833f3dc9f111cd1ed` |
| `nic/nic_rx.c` | `a844bdf75065a152e78d30c789aabb398b0d0f336d30d6ffd028793bf091412b` |
