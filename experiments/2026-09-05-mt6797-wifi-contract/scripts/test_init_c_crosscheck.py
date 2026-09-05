#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compare an explicitly built test library with existing synthetic Python fixtures.

Argument is the managed local library built from hif_init_transaction_test.c.
No firmware, packets from disk or hardware input is consumed.
"""
import ctypes
import sys

import wifi_init_protocol as protocol
from test_wifi_init_protocol import command, result


def main():
    library = ctypes.CDLL(sys.argv[1])
    count = 0
    for name, fixture, decoder in (
        ("check_config", command(), protocol.decode_download_config),
        ("check_result", result(), protocol.decode_command_result),
    ):
        check = getattr(library, name)
        check.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint]
        check.restype = ctypes.c_int
        records = [fixture[:n] for n in range(len(fixture))]
        records += [fixture, fixture + b"\0" * 4]
        records += [fixture[:i] + bytes([b]) + fixture[i + 1:]
                    for i in range(len(fixture)) for b in range(256)]
        for packet in records:
            try:
                decoded = decoder(packet, expected_sequence=19)
                expected = 1 if decoded.get("firmware_status_code", 0) else 0
            except protocol.Refusal:
                expected = 2
            assert check(packet, len(packet), 19) == expected, (name, count)
            count += 1
        for seq in range(257):
            try:
                decoder(fixture, expected_sequence=seq)
                expected = 0
            except protocol.Refusal:
                expected = 2
            assert check(fixture, len(fixture), seq) == expected
            count += 1
    print(f"independent_python_c_wire_comparisons={count} result=pass")


if __name__ == "__main__":
    main()
