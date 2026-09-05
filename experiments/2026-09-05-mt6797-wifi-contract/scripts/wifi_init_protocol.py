#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Pure model for one MT6797 gen3 DOWNLOAD_CONFIG / CMD_RESULT exchange.

Inputs are already delimited logical records, not raw transport captures.
There is no file reader, transmitter, loader, packet builder or hardware API.
"""

import json
import struct
import sys


DOWNLOAD_CONFIG_BYTES = 20
MT6797_RESULT_BYTES = 28
COMMAND_QUEUE = 0x8000
PDA_QUEUE = 0xC000
COMMAND_PACKET_TYPE = 0xA0
EVENT_PACKET_TYPE = 0xE000
DOWNLOAD_CONFIG_ID = 1
COMMAND_RESULT_ID = 1
ENCRYPTION_MODE = 1
KEY_INDEX_MASK = 0x6
RESET_OPTION = 0x8
ACK_OPTION = 1 << 31
KNOWN_MODE_BITS = ENCRYPTION_MODE | KEY_INDEX_MASK | RESET_OPTION | ACK_OPTION
ADDRESS_LIMIT = 1 << 32


class Refusal(Exception):
    """Fixed classification code, with no input data embedded in the error."""


def contract():
    return {
        "status": "contract_only",
        "model": "mt6797_gen3_download_config_cmd_result",
        "command_bytes": DOWNLOAD_CONFIG_BYTES,
        "result_bytes": MT6797_RESULT_BYTES,
        "max_exchange_bytes": DOWNLOAD_CONFIG_BYTES + MT6797_RESULT_BYTES,
        "input_boundary": "already_delimited_logical_records",
        "runtime_protocol_match": "unproven",
        "file_access": False,
        "hardware_access": False,
        "transmit_capability": False,
        "load_authorized": False,
    }


def _check_sequence(sequence):
    if type(sequence) is not int or not 0 <= sequence <= 255:
        raise Refusal("invalid_expected_sequence")


def _check_record(packet, size):
    if type(packet) is not bytes:
        raise Refusal("immutable_bytes_required")
    if len(packet) != size:
        raise Refusal("logical_record_length_policy")
    if struct.unpack_from("<H", packet)[0] != size:
        raise Refusal("declared_byte_count_policy")


def decode_download_config(packet, *, expected_sequence):
    """Validate a source-constructor-shaped command, returning metadata only."""
    _check_sequence(expected_sequence)
    _check_record(packet, DOWNLOAD_CONFIG_BYTES)
    _, queue, command, packet_type, reserved, sequence = struct.unpack_from("<HHBBBB", packet)
    if queue == PDA_QUEUE:
        raise Refusal("pda_is_not_download_config")
    if queue != COMMAND_QUEUE:
        raise Refusal("command_queue_mismatch")
    if command != DOWNLOAD_CONFIG_ID:
        raise Refusal("not_download_config")
    if packet_type != COMMAND_PACKET_TYPE:
        raise Refusal("command_packet_type_mismatch")
    if sequence != expected_sequence:
        raise Refusal("command_sequence_mismatch")
    # The selected wlanImageSectionConfig constructor explicitly writes zero.
    if reserved != 0:
        raise Refusal("command_reserved_not_source_constructor")

    address, length, mode = struct.unpack_from("<III", packet, 8)
    if length == 0:
        raise Refusal("zero_length_has_no_source_command")
    if length > ADDRESS_LIMIT - address:
        raise Refusal("destination_overflow_policy")
    if mode & ~KNOWN_MODE_BITS:
        raise Refusal("mode_not_source_constructor")
    if not mode & ACK_OPTION:
        raise Refusal("ack_not_requested_by_command")
    if mode & KEY_INDEX_MASK and not mode & ENCRYPTION_MODE:
        raise Refusal("key_selector_without_encryption")
    return {
        "status": "decoded",
        "command": "download_config",
        "packet_bytes": DOWNLOAD_CONFIG_BYTES,
        "section_bytes": length,
        "sequence_matches": True,
        "encryption_requested": bool(mode & ENCRYPTION_MODE),
        "reset_requested": bool(mode & RESET_OPTION),
        "ack_requested": True,
    }


def decode_command_result(packet, *, expected_sequence):
    """Check the MT6797 result shape; do not interpret diagnostic fields.

    Nonzero firmware status is a decoded failure, not malformed input.
    Reserved response bytes are observed only as a boolean, not gated.
    """
    _check_sequence(expected_sequence)
    _check_record(packet, MT6797_RESULT_BYTES)
    _, packet_type, event, sequence = struct.unpack_from("<HHBB", packet)
    if packet_type != EVENT_PACKET_TYPE:
        raise Refusal("event_packet_type_policy")
    if event != COMMAND_RESULT_ID:
        raise Refusal("not_command_result")
    if sequence != expected_sequence:
        raise Refusal("result_sequence_mismatch")
    status = packet[8]
    # The source verifier does not gate these fields or compare rSrc.
    reserved_zero = not any(packet[6:8] + packet[9:12] + packet[15:16])
    status_name = {
        0: "success",
        1: "invalid_parameters",
        2: "crc_error",
        3: "decryption_failure",
        4: "unknown_command",
    }.get(status, "other_failure")
    return {
        "status": "decoded",
        "event": "command_result",
        "packet_bytes": MT6797_RESULT_BYTES,
        "sequence_matches": True,
        "firmware_status_code": status,
        "firmware_status": status_name,
        "reserved_fields_zero": reserved_zero,
        "diagnostic_fields_interpreted": False,
    }


def validate_download_config_ack(command, response, *, expected_sequence):
    """Match one supplied command/response pair; never send or wait for either.

    A matching 8-bit sequence does not authenticate a record or exclude replay
    after wraparound; the future transport must serialize and attribute it.
    """
    request = decode_download_config(command, expected_sequence=expected_sequence)
    result = decode_command_result(response, expected_sequence=expected_sequence)
    return {
        "status": "source_contract_match" if result["firmware_status_code"] == 0 else "firmware_rejected",
        "command_bytes": request["packet_bytes"],
        "result_bytes": result["packet_bytes"],
        "section_bytes": request["section_bytes"],
        "sequence_matches": True,
        "encryption_requested": request["encryption_requested"],
        "reset_requested": request["reset_requested"],
        "firmware_status_code": result["firmware_status_code"],
        "firmware_status": result["firmware_status"],
        "response_reserved_fields_zero": result["reserved_fields_zero"],
        "response_diagnostic_fields_interpreted": False,
        "runtime_protocol_match": "unproven",
        "hardware_access": False,
        "load_authorized": False,
    }


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        print(json.dumps({"status": "refused", "reason": "arguments_not_supported"}))
        return 2
    print(json.dumps(contract(), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
