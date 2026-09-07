#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mutation fixtures for semantic keyboard prerequisite enforcement."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
P = runpy.run_path(str(HERE/'prerequisites.py'))
encode = lambda value: (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
sha = lambda raw: hashlib.sha256(raw).hexdigest()


class PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ident = '12345678-1234-1234-1234-123456789abc'
        self.boot = 'abcdefab-1234-1234-1234-abcdefabcdef'
        self.candidate = {'files': {'boot.img': '1'*64}, 'members': {
            'bin/dropbear': {'sha256': '2'*64}, 'bin/admin-shell': {'sha256': '3'*64}}}
        self.admission = {'id': self.ident, 'boot_id': self.boot, 'package_identity': '4'*64,
            'package_revision': '5'*40, 'monitor_sha256': '6'*64,
            'full_duration_receipt_sha256': '0'*64, 'disconnect_receipt_sha256': '0'*64,
            'runtime': {'event': 'event2', 'minor': 64, 'input_path': '/sys/devices/platform/input/input2',
                'capabilities': {'ev': '3\n'}, 'resource_paths': {'/sys/a': '/sys/b'},
                'logger_age_limit_seconds': 240, 'metadata_receipt_sha256': '0'*64},
            'custody': {'exclusive': True, 'no_other_device_operations': True, 'stable_power': True,
                'physical_selection': True, 'screen_readable': True, 'owner_ready': True,
                'receipt_sha256': '0'*64}}
        self.runtime = {'schema': 'keyboard-runtime-metadata-v1', 'classification': 'passed',
            'admission_id': self.ident, 'boot_id': self.boot, 'candidate_sha256': '1'*64,
            'event': 'event2', 'minor': 64, 'input_path': '/sys/devices/platform/input/input2',
            'capabilities_sha256': P['object_digest']({'ev': '3\n'}),
            'resource_paths_sha256': P['object_digest']({'/sys/a': '/sys/b'}),
            'logger_age_seconds': 120, 'map_verified': True, 'console_logs_separated': True,
            'console_status_exited': True, 'inventory_complete': True}
        self.custody = {'schema': 'keyboard-custody-v1', 'classification': 'passed',
            'admission_id': self.ident, 'boot_id': self.boot, 'candidate_sha256': '1'*64,
            'exclusive': True, 'no_other_device_operations': True, 'stable_power': True,
            'physical_selection': True, 'screen_readable': True, 'owner_ready': True,
            'continuous_reader_exclusion': True}
        self.disconnect = {'schema': 'keyboard-disconnect-v1', 'classification': 'passed',
            'admission_id': self.ident, 'boot_id': self.boot, 'candidate_sha256': '1'*64,
            'server': {'binary_sha256': '2'*64, 'admin_shell_sha256': '3'*64,
                'no_pty': True, 'authentication': 'exact-candidate-ed25519'},
            'monitor': {'source_sha256': sha((HERE/'monitor.c').read_bytes()),
                'package_identity': '4'*64, 'package_revision': '5'*40, 'binary_sha256': '6'*64,
                'probe_sha256': '7'*64},
            'claim': {'count': 1, 'retained': True},
            'transport': {'first_connection_no_pty': True, 'deliberate_disconnect': True,
                'independent_export_connection': True},
            'process': {'monitor_terminal': True, 'monitor_reaped': True,
                'observer_terminal': True, 'observer_reaped': True, 'late': False},
            'preservation': {'members': {name: None for name in P['FILES']},
                'complete_available_members': True, 'source_retained': True},
            'reader_release': {'monitor_absent': True, 'observer_absent': True,
                'tty1_reader_absent': True, 'input_reader_absent': True, 'inventory_complete': True}}

    def test_runtime_custody_disconnect_bindings_and_mutations(self):
        cases = [('runtime', self.runtime, P['runtime']), ('custody', self.custody, P['custody'])]
        for label, value, verifier in cases:
            with self.subTest(label=label):
                raw = encode(value)
                verifier(raw, sha(raw), self.admission, self.candidate)
                changed = copy.deepcopy(value)
                changed['classification'] = 'inconclusive'
                with self.assertRaisesRegex(ValueError, label):
                    verifier(encode(changed), sha(encode(changed)), self.admission, self.candidate)
                with self.assertRaisesRegex(ValueError, label + ' receipt digest'):
                    verifier(raw, 'f'*64, self.admission, self.candidate)
        raw = encode(self.disconnect)
        P['disconnect'](raw, sha(raw), self.admission, self.candidate,
                        {'keyboard-disconnect-probe': '7'*64})
        changed = copy.deepcopy(self.disconnect); changed['classification'] = 'inconclusive'
        with self.assertRaisesRegex(ValueError, 'disconnect'):
            P['disconnect'](encode(changed), sha(encode(changed)), self.admission, self.candidate,
                            {'keyboard-disconnect-probe': '7'*64})
        with self.assertRaisesRegex(ValueError, 'disconnect receipt digest'):
            P['disconnect'](raw, 'f'*64, self.admission, self.candidate,
                            {'keyboard-disconnect-probe': '7'*64})

    def test_disconnect_each_decisive_boolean_refuses(self):
        for group, key in (('claim', 'retained'), ('transport', 'deliberate_disconnect'),
                ('process', 'monitor_reaped'), ('process', 'observer_reaped'),
                ('preservation', 'complete_available_members'),
                ('reader_release', 'tty1_reader_absent'), ('reader_release', 'input_reader_absent')):
            changed = copy.deepcopy(self.disconnect)
            changed[group][key] = False
            raw = encode(changed)
            with self.subTest(group=group, key=key), self.assertRaises(ValueError):
                P['disconnect'](raw, sha(raw), self.admission, self.candidate,
                                {'keyboard-disconnect-probe': '7'*64})

    def test_duration_exact_tracked_receipt(self):
        raw = (HERE/'results/duration-6d8c9b18/receipt.json').read_bytes()
        P['duration'](raw, sha(raw), sha((HERE/'monitor.c').read_bytes()))
        changed = json.loads(raw)
        changed['classification']['classification'] = 'inconclusive'
        mutated = encode(changed)
        with self.assertRaisesRegex(ValueError, 'duration outcome'):
            P['duration'](mutated, sha(mutated), sha((HERE/'monitor.c').read_bytes()))


if __name__ == '__main__':
    unittest.main()
