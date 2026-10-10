#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Send three tiny UDP broadcast datagrams on the owner's private LAN during the traffic window.

Run on the laptop (same LAN as the device), not on the device. Standard library
only, no root. The local address must be an RFC 1918 host address with an
ordinary LAN prefix (16 to 30); the directed broadcast is computed from it; the
kernel's own route lookup for that broadcast must select exactly that local
address (so the datagrams can only leave through the owner's interface); the
socket is then bound to it, TTL 1 and SO_BROADCAST set, and three 8-byte
payloads go out one second apart. Whether the access point forwards them to the
station as group-addressed protected frames is an observation for the device's
rxd records, not an assumption.
"""
import argparse
import ipaddress
import socket
import sys
import time

PORT = 47110
PAYLOAD = b'gwref10!'
RFC1918 = (ipaddress.ip_network('10.0.0.0/8'), ipaddress.ip_network('172.16.0.0/12'), ipaddress.ip_network('192.168.0.0/16'))


def broadcast_address(local, prefix):
    """The directed broadcast for an RFC 1918 host address on a normal LAN prefix, else ValueError."""
    address = ipaddress.ip_address(local)
    if address.version != 4 or not any(address in net for net in RFC1918):
        raise ValueError('refusing a local address outside RFC 1918')
    if not 16 <= prefix <= 30:
        raise ValueError('refusing a prefix outside 16..30')
    network = ipaddress.ip_network('%s/%d' % (local, prefix), strict=False)
    if address in (network.network_address, network.broadcast_address):
        raise ValueError('refusing a network or broadcast address as the local host')
    return str(network.broadcast_address)


def route_selects(local, target, socket_factory=socket.socket):
    """True when the kernel's route to the target uses exactly the given local address (no packet sent)."""
    with socket_factory(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        probe.connect((target, PORT))
        return probe.getsockname()[0] == local


def send(local, prefix, count=3, interval=1.0, socket_factory=socket.socket, sleep=time.sleep):
    target = broadcast_address(local, prefix)
    if not route_selects(local, target, socket_factory):
        raise ValueError('the route to the LAN broadcast does not use the given local address')
    with socket_factory(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, 1)
        sock.bind((local, 0))
        for i in range(count):
            sock.sendto(PAYLOAD, (target, PORT))
            if i + 1 < count:
                sleep(interval)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('local', help='this laptop\'s IPv4 address on the owner LAN')
    parser.add_argument('prefix', type=int, help='the LAN prefix length, e.g. 24')
    args = parser.parse_args()
    send(args.local, args.prefix)
    print('sent 3 datagrams of %d bytes to the directed broadcast of /%d, TTL 1' % (len(PAYLOAD), args.prefix))
    return 0


if __name__ == '__main__':
    sys.exit(main())
