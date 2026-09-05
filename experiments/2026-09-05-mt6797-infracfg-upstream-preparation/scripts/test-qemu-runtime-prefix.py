#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline mutation fixtures; no emulator, network or retained prefix access."""
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('verify-qemu-runtime-prefix.py')
spec = importlib.util.spec_from_file_location('prefix_check', SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class PrefixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.prefix = self.root / 'prefix'
        self.prefix.mkdir()
        self.library = self.prefix / 'library'
        self.library.write_bytes(b'x')
        members = {f'member-{n}': {} for n in range(2257)}
        (self.prefix / 'setup-receipt.json').write_text(json.dumps({'members': members}))
        self.names = list(members) + ['setup-receipt.json']
        libs = {f'$QEMU_PREFIX/library-{n}': {'bytes': 1, 'sha256': 'library'} for n in range(50)}
        for n in range(50):
            (self.prefix / f'library-{n}').write_bytes(b'x')
        self.inspection = {'resolved_libraries': libs, 'executable_sha256': 'binary', 'version': 'fixture'}
        evidence = {'destination': str(self.prefix), 'remote_receipt_sha256': 'receipt',
                    'inspection': self.inspection}
        experiment = self.root / check.EXPERIMENT
        (experiment / 'results').mkdir(parents=True)
        (experiment / 'results/qemu-debian-setup.json').write_text(json.dumps(evidence))
        self.fake = types.SimpleNamespace(verify_prefix=lambda *_: None,
                                        inspect_emulator=lambda _: self.inspection)
        loader = types.SimpleNamespace(exec_module=lambda _: None)
        for target, kwargs in [
            ('subprocess.check_output', {'return_value': check.REVISION}),
            ('importlib.util.spec_from_file_location', {'return_value': types.SimpleNamespace(loader=loader)}),
            ('importlib.util.module_from_spec', {'return_value': self.fake}),
            ('os.walk', {'side_effect': lambda *_args, **_kw: [(str(self.prefix), [], self.names)]}),
            ('sha', {'side_effect': lambda p: 'receipt' if p.name == 'setup-receipt.json' else 'library'}),
        ]:
            parts = target.split('.')
            owner = check
            for segment in parts[:-1]:
                owner = getattr(owner, segment)
            mocker = patch.object(owner, parts[-1], **kwargs)
            mocker.start()
            self.addCleanup(mocker.stop)

    def test_positive(self):
        result = check.verify(self.root)
        self.assertEqual(result['result'], 'PASS')
        self.assertFalse(result['guest_run'])

    def test_extra_and_missing_members(self):
        self.names.append('unexpected')
        with self.assertRaisesRegex(ValueError, 'inventory member'):
            check.verify(self.root)
        self.names.pop()
        self.names.pop(0)
        with self.assertRaisesRegex(ValueError, 'inventory member'):
            check.verify(self.root)

    def test_traversal_failure(self):
        def unreadable(*_args, **kwargs):
            kwargs['onerror'](PermissionError('fixture inaccessible'))
        with patch.object(check.os, 'walk', side_effect=unreadable):
            with self.assertRaises(PermissionError):
                check.verify(self.root)

    def test_changed_checkout_and_receipt(self):
        with patch.object(check.subprocess, 'check_output', return_value='different'):
            with self.assertRaisesRegex(ValueError, 'checkout identity'):
                check.verify(self.root)
        with patch.object(check, 'sha', return_value='different'):
            with self.assertRaisesRegex(ValueError, 'receipt changed'):
                check.verify(self.root)

    def test_changed_library(self):
        with patch.object(check, 'sha', side_effect=lambda p: 'receipt' if p.name == 'setup-receipt.json' else 'different'):
            with self.assertRaisesRegex(ValueError, 'library changed'):
                check.verify(self.root)

    def test_changed_resolution_and_binary(self):
        for field, reason in [('resolved_libraries', 'resolution changed'), ('executable_sha256', 'emulator changed')]:
            altered = dict(self.inspection)
            altered[field] = 'different'
            with patch.object(self.fake, 'inspect_emulator', return_value=altered):
                with self.assertRaisesRegex(ValueError, reason):
                    check.verify(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
