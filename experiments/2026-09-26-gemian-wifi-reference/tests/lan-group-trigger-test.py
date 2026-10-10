#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The trigger computes a private directed broadcast and refuses anything else; no packets sent."""
import pathlib
import runpy
import unittest

MOD = runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / 'lifecycle/lan-group-trigger.py'), run_name='x')


class TriggerTest(unittest.TestCase):
    def test_private_broadcast(self):
        self.assertEqual(MOD['broadcast_address']('192.168.4.17', 24), '192.168.4.255')
        self.assertEqual(MOD['broadcast_address']('10.9.8.7', 16), '10.9.255.255')

    def test_refusals(self):
        for local, prefix in (('8.8.8.8', 24), ('192.168.4.17', 8), ('172.16.0.5', 12)):
            with self.assertRaises(ValueError):
                MOD['broadcast_address'](local, prefix)

    def test_payload_is_tiny(self):
        self.assertEqual(len(MOD['PAYLOAD']), 8)


if __name__ == '__main__':
    unittest.main()
