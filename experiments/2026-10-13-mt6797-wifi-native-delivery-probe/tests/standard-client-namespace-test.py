#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the real standard-client CLI admission before any device command."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('standard_client_namespace', HERE.parent / 'laptop-wifi-ssh-retain.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class NamespaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='standard-client-namespace-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.main = Mock(return_value=17)
        self.commands = Mock(side_effect=AssertionError('offline fixture must not issue a command'))
        for manager in [patch.object(sys, 'platform', 'darwin'),
                        patch.dict(os.environ, {'GEMINI_RUNTIME_ROOT': str(self.root)}),
                        patch.object(M.D.O.C.M, 'main', self.main),
                        patch.object(M.D.O.C.M, 'run'),
                        patch.object(M.subprocess, 'run', self.commands)]:
            manager.start()
            self.addCleanup(manager.stop)

    def invoke(self, receipt, platform='darwin', extra=()):
        with patch.object(sys, 'platform', platform), patch.object(
                sys, 'argv', ['laptop-wifi-ssh-retain.py', '--receipt', str(receipt), *extra]):
            return M.main()

    def receipt(self, name):
        p = self.root / 'ccmp-stable-monitor' / name
        p.mkdir(parents=True)
        return p / 'wifi-ssh-receipt.json'

    def test_i50_reaches_frozen_client_main(self):
        self.assertEqual(self.invoke(self.receipt('session-ccmp-i50')), 17)
        self.main.assert_called_once_with()
        self.commands.assert_not_called()

    def test_existing_numeric_and_gtk_names_still_admitted(self):
        for name in ['session-ccmp1', 'session-ccmp12', 'session-ccmp-gtk1', 'session-ccmp-gtk100']:
            with self.subTest(name=name):
                self.main.reset_mock()
                self.assertEqual(self.invoke(self.receipt(name)), 17)
                self.main.assert_called_once_with()

    def test_unreviewed_names_still_refused(self):
        for name in ['session-ccmp0', 'session-ccmp', 'session-ccmp-gtk0', 'session-ccmp-i500',
                     'session-ccmp-i50-extra', 'session-ccmp-gtk8-s1', 'session-ccmp-other']:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, 'receipt does not name a CCMP session'):
                    self.invoke(self.receipt(name))
        self.main.assert_not_called()

    def test_foreign_root_and_wrong_filename_refused(self):
        p = self.receipt('session-ccmp-i50')
        for bad in [p.with_name('other.json'), self.root / 'foreign' / p.parent.name / p.name]:
            with self.subTest(path=bad):
                with self.assertRaisesRegex(ValueError, 'receipt is outside the owned session'):
                    self.invoke(bad)
        self.main.assert_not_called()

    def test_symlinked_session_refused(self):
        target = self.root / 'target'
        target.mkdir()
        parent = self.root / 'ccmp-stable-monitor'
        parent.mkdir()
        (parent / 'session-ccmp-i50').symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'receipt is outside the owned session'):
            self.invoke(parent / 'session-ccmp-i50/wifi-ssh-receipt.json')
        self.main.assert_not_called()

    def test_non_custodian_platform_refused(self):
        with self.assertRaisesRegex(ValueError, 'custodian laptop and one owned receipt required'):
            self.invoke(self.receipt('session-ccmp-i50'), platform='linux')
        self.main.assert_not_called()

    def test_duplicate_receipt_argument_refused(self):
        p = self.receipt('session-ccmp-i50')
        with self.assertRaisesRegex(ValueError, 'custodian laptop and one owned receipt required'):
            self.invoke(p, extra=('--receipt', str(p)))
        self.main.assert_not_called()


if __name__ == '__main__':
    unittest.main()
