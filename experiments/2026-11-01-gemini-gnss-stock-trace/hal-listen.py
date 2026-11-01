#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record what mnld sends to the HAL, one line per datagram: time, then hex.

Usage: hal-listen.py OUTPUT_FILE
The output can hold position, so it stays private.
"""

import socket
import sys
import time

# An abstract name: the whole zero-padded 108-byte address is significant.
ADDRESS = b"\0mtk_mnl2hal".ljust(108, b"\0")


def main():
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    listener.bind(ADDRESS)
    with open(sys.argv[1], "a") as output:
        while True:
            data = listener.recv(65536)
            output.write("%.3f %s\n" % (time.time(), data.hex()))
            output.flush()


main()
