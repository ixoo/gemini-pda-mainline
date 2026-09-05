#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import runpy
from pathlib import Path
import unittest
from unittest.mock import patch
M = runpy.run_path(str(Path(__file__).with_name('mainline_host.py')))
INTERFACES = 'en7: flags=1\n\tinet 10.15.19.1 netmask 0xffffff00\n\tstatus: active\n'
ROUTES = '10.15.19 link#20 UCS en7\n'

class HostTests(unittest.TestCase):
    def check(self, interfaces=INTERFACES, routes=ROUTES):
        return M['inspect'](interfaces,routes,'10.15.19.82','10.15.19.1/24')['ready']
    def test_direct_active_unique_route(self):
        self.assertTrue(self.check())
    def test_absent_inactive_duplicate_wrong_route_and_override(self):
        for interfaces,routes in [('',ROUTES),(INTERFACES.replace('active','inactive'),ROUTES),
                (INTERFACES+INTERFACES.replace('en7','en8'),ROUTES),(INTERFACES,''),
                (INTERFACES,ROUTES.replace('en7','en0')),
                (INTERFACES,ROUTES+'10.15.19.82 192.0.2.1 UGH en0\n')]:
            self.assertFalse(self.check(interfaces,routes))
    def test_local_refusal_precedes_claim_import_and_transport(self):
        with patch.dict(M['identity_once'].__globals__,{'require_ready':lambda:(_ for _ in ()).throw(ValueError('absent'))}), \
                patch('runpy.run_path',side_effect=AssertionError('import')), \
                patch.object(Path,'mkdir',side_effect=AssertionError('claim')):
            with self.assertRaisesRegex(ValueError,'absent'):
                M['identity_once'](None,'unused')

if __name__ == '__main__': unittest.main()
