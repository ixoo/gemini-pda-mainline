# Bounded WIFI_START constructor decoder

This adds the missing 16-byte WIFI_START command boundary to the existing
[INIT record helper](scripts/wifi_init_protocol.py). DOWNLOAD_CONFIG/result
validation and [session tracking](INIT_SESSION.md) already exist and are not
duplicated. `decode_wifi_start(packet, expected_sequence=...)` is a pure
decoder for an independently delimited immutable record. It neither builds
nor sends a command and is not admitted into the download session state
machine.

## Exact source contract

The existing selected gen3 source pin is Planet
`c5b0be85017ad0c599725e8273842efdbecdd88a`. The files were re-read over HTTPS
in memory; [their identities](results/wifi-start-sources.json) match the
earlier [INIT protocol audit](INIT_PROTOCOL.md). No retained input was
recaptured, opened or published in this follow-up. This is a public-source
contract component, not new retained-binary or runtime attribution.

The eight-byte command header contains little-endian count and queue, then
command ID, packet type, reserved byte and sequence. WIFI_START ID is 2;
queue is `0x8000` and packet type is `0xa0`. The body is two little-endian
32-bit words: override and address. The selected constructor zeroes the
whole record, sets override to either zero or one from its Boolean argument,
and assigns the supplied address. Although the header names bit 1 as
delay-calibration, this constructor does not set it.
[Layout and constants](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_init_cmd_event.h#L110),
[constructor](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L2821).

The MT6797 source configuration disables start-address override, selecting
the startup call with false and address zero. The decoder deliberately models
both constructor branches, not just that call site; accepting override one
does not establish that it was selected or is safe for the retained image.
[Configuration](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/config.h#L508),
[call site and subsequent ready polling](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L475).

The constructor transmits and returns without consuming CMD_RESULT. Startup
then polls WCIR readiness. Therefore this component does not create a
WIFI_START/CMD_RESULT pair validator or infer readiness from a decoded command.

## Refusal and metadata boundary

The implementation reuses the existing sequence and exact-record checks.
It requires exactly 16 supplied bytes, declared count 16, the source header
values, reserved byte zero, an independently expected sequence in 0–255, and
override exactly zero or one. Appended bus padding and concatenated records
are refused. Exact logical length/count checks remain conservative model
policy, not evidence of a live received packet.

Rejecting delay-calibration and other override bits is a constructor-scope
gate, not a claim that every other firmware command form is invalid. The
32-bit address is neither emitted nor whitelisted; arbitrary address values
produce the same sanitized metadata for a given override. In particular,
zero address with override one is not classified as an executable target.
Outputs explicitly keep address validation, firmware readiness, hardware
access and load authorization false, and runtime matching unproven.
Fixed refusal codes contain no packet data.

## Validation and unresolved prerequisites

The [nine synthetic tests](scripts/test_wifi_start.py) cover both constructor
branches, address non-disclosure, every truncation, padding/concatenation,
declared lengths including endian confusion, queue/ID/type/reserved
mutations, all 256 sequences and mismatches, invalid caller types, and each
non-constructor override bit with and without bit zero. They also verify
that the existing download/result decoders refuse a start record. The 36
existing INIT protocol and 32 session tests pass unchanged.

```sh
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_start.py
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_init_protocol.py
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_init_session.py
```

Runtime prerequisites remain exact retained firmware/protocol applicability,
logical record extraction, owner/session serialization and freshness,
completed download attribution, authorized start-address policy, bounded
readiness/failure recovery, and the unresolved power/HIF/DMA/EMI contracts.
An eight-bit sequence is not authentication or replay protection. No runtime
observation, radio/device/backend action, calibration input, kernel change
or readiness claim is included. The [validation receipt](results/wifi-start-validation.txt)
records this documentation-and-host-test handoff; roadmap ordering stays with
the coordinator.

## Integration review

Project Planning independently fetched and hash-verified the three pinned public
sources, checked the constructor and subsequent readiness poll, and reviewed the
helper's exact-length/type/sequence gates and sanitized output. All nine new,
36 existing protocol and 32 session tests pass in the integration checkout.
The original source bytes were read in memory and not retained in Git. Acceptance
is confined to decoding; no transmit operation or runtime proof follows.
