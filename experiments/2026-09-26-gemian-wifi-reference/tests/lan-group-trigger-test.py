#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The trigger accepts only RFC 1918 host addresses on normal prefixes, checks the route, and sends exactly three."""
import pathlib
import runpy
import socket
import unittest

MOD = runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / 'lifecycle/lan-group-trigger.py'), run_name='x')


class FakeSocket:
    instances = []

    def __init__(self, family, kind):
        self.family, self.kind = family, kind
        self.options, self.sent, self.bound, self.connected = [], [], None, None
        FakeSocket.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def setsockopt(self, level, option, value):
        self.options.append((level, option, value))

    def connect(self, address):
        self.connected = address

    def getsockname(self):
        return (FakeSocket.route_local, 40000)

    def bind(self, address):
        self.bound = address

    def sendto(self, payload, address):
        self.sent.append((payload, address))


class TriggerTest(unittest.TestCase):
    def test_private_broadcast(self):
        self.assertEqual(MOD['broadcast_address']('192.168.4.17', 24), '192.168.4.255')
        self.assertEqual(MOD['broadcast_address']('10.9.8.7', 16), '10.9.255.255')
        self.assertEqual(MOD['broadcast_address']('172.31.5.6', 30), '172.31.5.7')

    def test_refusals(self):
        for local, prefix in (('8.8.8.8', 24), ('127.0.0.1', 8), ('169.254.1.2', 16), ('192.168.4.17', 8),
                              ('192.168.4.17', 31), ('192.168.4.17', 32), ('192.168.4.0', 24), ('192.168.4.255', 24),
                              ('172.32.0.5', 16), ('240.0.0.1', 24), ('192.168.4.1', 15)):
            with self.assertRaises(ValueError, msg=(local, prefix)):
                MOD['broadcast_address'](local, prefix)

    def test_send_schedule_and_route_check(self):
        FakeSocket.instances = []
        FakeSocket.route_local = '192.168.4.17'
        sleeps = []
        target = MOD['send']('192.168.4.17', 24, socket_factory=FakeSocket, sleep=sleeps.append)
        self.assertEqual(target, '192.168.4.255')
        probe, sender = FakeSocket.instances
        self.assertEqual(probe.connected, ('192.168.4.255', 47110))
        self.assertEqual(sender.bound, ('192.168.4.17', 0))
        self.assertEqual(sender.sent, [(b'gwref10!', ('192.168.4.255', 47110))] * 3)
        self.assertEqual(sleeps, [1.0, 1.0])
        self.assertIn((socket.IPPROTO_IP, socket.IP_TTL, 1), sender.options)
        self.assertIn((socket.SOL_SOCKET, socket.SO_BROADCAST, 1), sender.options)
        # a route through another interface address refuses before any send
        FakeSocket.instances = []
        FakeSocket.route_local = '10.0.0.9'
        with self.assertRaises(ValueError):
            MOD['send']('192.168.4.17', 24, socket_factory=FakeSocket, sleep=sleeps.append)
        self.assertEqual(len(FakeSocket.instances), 1)

    def test_payload_is_tiny(self):
        self.assertEqual(len(MOD['PAYLOAD']), 8)


if __name__ == '__main__':
    unittest.main()
