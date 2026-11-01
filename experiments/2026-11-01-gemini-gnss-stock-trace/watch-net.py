#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stop the GNSS start as soon as uid 1021 has a socket with a remote peer.

Usage: watch-net.py HAL_SEND_PATH SECONDS
Polls five times a second, so a very short connection can be missed.
Exit 0: no connection seen. Exit 3: connection seen, stop and cleanup sent.
"""

import subprocess
import sys
import time

UID = "1021"
TABLES = ("tcp", "tcp6", "udp", "udp6")


def remote_peers():
    peers = []
    for table in TABLES:
        with open("/proc/net/" + table) as sockets:
            next(sockets)
            for line in sockets:
                fields = line.split()
                if fields[7] != UID:
                    continue
                address, port = fields[2].split(":")
                if int(address, 16) and int(port, 16):
                    peers.append((table, fields[1], fields[2], fields[3]))
    return peers


def main():
    hal_send, seconds = sys.argv[1], float(sys.argv[2])
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        peers = remote_peers()
        if peers:
            print(time.strftime("%H:%M:%S"), "connection, stopping:", peers, flush=True)
            for command in ("stop", "cleanup"):
                subprocess.run([sys.executable, hal_send, command], check=False)
            return 3
        time.sleep(0.2)
    print(time.strftime("%H:%M:%S"), "no connection seen", flush=True)
    return 0


sys.exit(main())
