#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Send one command to mnld's HAL socket, as the Android HAL does."""

import socket
import struct
import sys

COMMANDS = {"init": 0x65, "start": 0x66, "stop": 0x67, "cleanup": 0x68}

if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
    sys.exit("usage: hal-send.py init|start|stop|cleanup")
# An abstract name: the whole zero-padded 108-byte address is significant.
ADDRESS = b"\0mtk_hal2mnl".ljust(108, b"\0")
# Little-endian: a first word mnld ignores, then the command.
MESSAGE = struct.pack("<II", 1, COMMANDS[sys.argv[1]])
with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as hal:
    hal.sendto(MESSAGE, ADDRESS)
