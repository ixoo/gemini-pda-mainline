#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic USB ancestry, protocol-address and direct-route attribution."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('collector', HERE / 'collect-ethernet.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
NETWORK = C.load('network', C.NETWORK)
USB = '''+-o capture@1 <class IOUSBHostDevice, id 0x1001, registered>
  | "idVendor" = 1317
  | "idProduct" = 42146
  | "USB Product Name" = "RNDIS/Ethernet Gadget"
  | "USB Serial Number" = "GEMINI_WIFI_EXPORT_TCP_1"
  +-o ethernet <class IOEthernetInterface, id 0x1002, registered>
      "BSD Name" = "en7"
'''
INTERFACES = '''en0: flags=1
    ether 00:11:22:33:44:55
    inet 192.0.2.1 netmask 0xffffff00
    status: active
en7: flags=1
    ether 42:00:15:19:82:00
    inet 10.15.19.1 netmask 0xffffff00
    status: active
'''
ROUTES = 'default 192.0.2.254 UGSc en0\n10.15.19/24 link#7 UCS en7\n'


class CollectorTests(unittest.TestCase):
    def select(self, usb=USB, before=None, interfaces=INTERFACES, routes=ROUTES):
        return C.select(C.devices(usb), set() if before is None else before, interfaces, routes, NETWORK)

    def test_new_parent_child_and_direct_route_pass(self):
        selected = self.select()
        self.assertEqual(selected['interface'], 'en7')
        self.assertTrue(selected['network']['ready'])
        # Unrelated sibling interfaces must not become this parent's children.
        other = USB.replace('0x1001', '0x2001').replace(C.SERIAL, 'unrelated').replace('en7', 'en8')
        self.assertEqual(self.select(usb=USB + other)['interface'], 'en7')

    def test_absent_or_incomplete_link_waits_without_connection(self):
        for values in ({'usb': ''}, {'usb': USB.replace('      "BSD Name" = "en7"\n', '')},
                       {'interfaces': INTERFACES.replace('inet 10.15.19.1', 'inet 169.254.1.1')},
                       {'interfaces': INTERFACES.replace('status: active', 'status: inactive')},
                       {'routes': 'default 192.0.2.254 UGSc en0\n'},
                       {'routes': ROUTES + '10.15.19.82 192.0.2.254 UGHS en0\n'}):
            with self.subTest(values=values):
                self.assertIsNone(self.select(**values))

    def test_old_ambiguous_or_mismatched_identity_refuses(self):
        for values in ({'before': {'0x1001'}}, {'usb': USB + USB.replace('0x1001', '0x3001')},
                       {'usb': USB.replace('42146', '42145')},
                       {'usb': USB.replace('Ethernet Gadget', 'Other Gadget')},
                       {'usb': USB + '      "BSD Name" = "en8"\n'},
                       {'interfaces': INTERFACES.replace('42:00:15:19:82:00', '42:00:15:19:83:00')}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.select(**values)

    def test_address_on_another_interface_cannot_authorize_capture(self):
        missing = INTERFACES.replace('    inet 10.15.19.1 netmask 0xffffff00\n', '')
        another = missing + 'en8: flags=1\n    inet 10.15.19.1 netmask 0xffffff00\n    status: active\n'
        self.assertIsNone(self.select(interfaces=another, routes=ROUTES.replace('en7', 'en8')))
        duplicate = INTERFACES + 'en8: flags=1\n    inet 10.15.19.1 netmask 0xffffff00\n    status: active\n'
        self.assertIsNone(self.select(interfaces=duplicate))


if __name__ == '__main__':
    unittest.main()
