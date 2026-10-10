#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Send three tiny UDP broadcast datagrams on the owner's private LAN during the traffic step.

Run on the laptop (same LAN as the device), not on the device. Standard library
only, no root. The sender binds to the given local interface address so the
datagrams can only leave through the owner's LAN, computes the directed broadcast
address from that address and prefix, refuses anything outside the private
ranges, sets TTL 1 and sends three 8-byte payloads one second apart. Whether the
access point forwards them to the station as group-addressed protected frames is
an observation for the device's rxd records, not an assumption.
"""
import argparse
import ipaddress
import socket
import sys
import time

PORT = 47110
PAYLOAD = b'gwref10!'


def broadcast_address(local, prefix):
    network = ipaddress.ip_network('%s/%d' % (local, prefix), strict=False)
    if not network.is_private or network.prefixlen < 16:
        raise ValueError('refusing a non-private or too wide network')
    return str(network.broadcast_address)


def send(local, prefix, count=3, interval=1.0):
    target = broadcast_address(local, prefix)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, 1)
        sock.bind((local, 0))
        for i in range(count):
            sock.sendto(PAYLOAD, (target, PORT))
            if i + 1 < count:
                time.sleep(interval)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('local', help='this laptop\'s IPv4 address on the owner LAN')
    parser.add_argument('prefix', type=int, help='the LAN prefix length, e.g. 24')
    args = parser.parse_args()
    target = send(args.local, args.prefix)
    print('sent 3 datagrams of %d bytes to the directed broadcast of /%d, TTL 1' % (len(PAYLOAD), args.prefix))
    return 0 if target else 1


if __name__ == '__main__':
    sys.exit(main())
