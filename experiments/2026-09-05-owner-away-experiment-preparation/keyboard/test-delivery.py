#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import runpy
from pathlib import Path
import unittest
from unittest.mock import patch

D = runpy.run_path(str(Path(__file__).with_name('delivery.py')))


class DeliveryRefusals(unittest.TestCase):
    def test_execution_refuses_before_any_input_or_transport(self):
        with patch('builtins.open', side_effect=AssertionError('I/O')), \
                patch('subprocess.Popen', side_effect=AssertionError('transport')):
            with self.assertRaisesRegex(ValueError, 'delivery disabled'):
                D['execute'](object(), execute=True)

    def test_missing_member_refuses_before_source_import(self):
        with patch('runpy.run_path', side_effect=AssertionError('source import')):
            with self.assertRaisesRegex(ValueError, 'member inventory'):
                D['script']({}, {}, '11111111-1111-1111-1111-111111111111')

    def test_unaccepted_binary_refuses_before_source_import(self):
        files = {name: b'x' for name in D['MEMBERS']}
        with patch('runpy.run_path', side_effect=AssertionError('source import')):
            with self.assertRaisesRegex(ValueError, 'binary identity'):
                D['script'](files, {}, '11111111-1111-1111-1111-111111111111')


if __name__ == '__main__':
    unittest.main()
