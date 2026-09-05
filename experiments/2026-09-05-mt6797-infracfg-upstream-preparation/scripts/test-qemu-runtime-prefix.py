#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline mutation fixtures; no emulator, network or retained prefix access."""
import importlib.util
import builtins
import hashlib
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
ORIGINAL_SHA = check.sha
setup_spec = importlib.util.spec_from_file_location('real_setup', SCRIPT.with_name('setup-qemu-debian.py'))
real_setup = importlib.util.module_from_spec(setup_spec)
setup_spec.loader.exec_module(real_setup)


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
        evidence = {'destination': str(self.prefix), 'remote_receipt_sha256': hashlib.sha256((self.prefix / 'setup-receipt.json').read_bytes()).hexdigest(),
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
        receipt = self.prefix / 'setup-receipt.json'
        receipt.write_bytes(receipt.read_bytes().replace(b'member-0', b'member-X', 1))
        with self.assertRaisesRegex(ValueError, 'receipt changed'):
            check.verify(self.root)

    def test_replacement_after_snapshot_does_not_change_inventory(self):
        # Real prefix verifier: one member changes together with its receipt
        # immediately after the receipt's read, before hashing/parsing.
        members = {}
        for name in self.names[:-1]:
            (self.prefix / name).write_bytes(b'x')
            members[name] = {'kind': 'file', 'bytes': 1, 'sha256': hashlib.sha256(b'x').hexdigest()}
        receipt = self.prefix / 'setup-receipt.json'
        original = json.dumps({'members': members}).encode()
        receipt.write_bytes(original)
        evidence_path = self.root / check.EXPERIMENT / 'results/qemu-debian-setup.json'
        evidence = json.loads(evidence_path.read_text())
        evidence['remote_receipt_sha256'] = hashlib.sha256(original).hexdigest()
        for record in self.inspection['resolved_libraries'].values():
            record['sha256'] = hashlib.sha256(b'x').hexdigest()
        evidence['inspection'] = self.inspection
        evidence_path.write_text(json.dumps(evidence))
        changed = {name: dict(record) for name, record in members.items()}
        changed['member-0']['sha256'] = hashlib.sha256(b'y').hexdigest()
        replacement = json.dumps({'members': changed}).encode()
        original_open = builtins.open
        original_path_open = Path.open
        swapped = []

        class ReadThenReplace:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *_): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, size=-1):
                result = self.stream.read(size)
                if result and not swapped:
                    swapped.append(True)
                    (self_prefix / 'member-0').write_bytes(b'y')
                    receipt.write_bytes(replacement)
                return result

        self_prefix = self.prefix
        def opening(path, mode='r', *args, **kwargs):
            stream = original_open(path, mode, *args, **kwargs)
            return ReadThenReplace(stream) if path == receipt and mode == 'rb' else stream

        def path_opening(path, mode='r', *args, **kwargs):
            stream = original_path_open(path, mode, *args, **kwargs)
            return ReadThenReplace(stream) if path == receipt and mode == 'rb' else stream

        with patch.object(builtins, 'open', opening), \
             patch.object(Path, 'open', path_opening), \
             patch.object(check, 'sha', ORIGINAL_SHA), \
             patch.object(self.fake, 'verify_prefix', real_setup.verify_prefix):
            with self.assertRaisesRegex(ValueError, 'regular file mismatch: member-0'):
                check.verify(self.root)
        self.assertEqual(swapped, [True])
        self.assertEqual(receipt.read_bytes(), replacement)

    def test_receipt_size_and_type_refuse(self):
        receipt = self.prefix / 'setup-receipt.json'
        with patch.object(check, 'RECEIPT_MAX_BYTES', 16):
            with self.assertRaisesRegex(ValueError, 'receipt size'):
                check.verify(self.root)
        receipt.unlink()
        receipt.symlink_to(self.library)
        with self.assertRaisesRegex(ValueError, 'regular setup receipt'):
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
