#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mutation fixtures for semantic keyboard prerequisite enforcement."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
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
            'reader_release': {'monitor_absent': True, 'observer_absent': True,
                'tty1_reader_absent': True, 'input_reader_absent': True, 'inventory_complete': True}}
        status = {'schema': 'keyboard-monitor-v1', 'reason': 'cancelled', 'reaped': '1',
            'identity_lost': '0', 'exit': '-1', 'signal': '9', 'cancel': '1', 'term_ms': '10',
            'kill_ms': '90', 'reap_ms': '100', 'term_errno': '0', 'kill_errno': '0',
            'late': '0', 'stdout_bytes': '18', 'stderr_bytes': '0', 'forwarded_bytes': '18'}
        self.evidence = {'observer.stdout': b'fixture-child=123\n', 'observer.stderr': b'',
            'monitor.status': ''.join(key+'='+value+'\n' for key,value in status.items()).encode(),
            'outer-exit': b'2\n',
            'disconnect-process.json': encode({'schema': 'keyboard-disconnect-transport-v1',
                'classification': 'deliberate-client-disconnect', 'connections': 1, 'no_pty': True,
                'marker_seen': True, 'stdin_complete': True, 'client_signal': 9,
                'elapsed_milliseconds': 50}),
            'export-process.json': encode({'exit_status': 0, 'reason': None, 'stdin_complete': True,
                'stdout_bytes': 100, 'stderr_bytes': 0, 'elapsed_seconds': 1}),
            'reader-scan.json': encode({'schema': 'keyboard-reader-release-v1',
                'classification': 'passed', 'admission_id': self.ident, 'boot_id': self.boot,
                'processes_scanned': 8, 'descriptors_scanned': 20, 'matches': []})}
        self.disconnect['evidence'] = {name: sha(raw) for name,raw in self.evidence.items()}
        self.disconnect['preservation'] = {'members': {name: sha(self.evidence[name]) for name in P['FILES']},
            'complete_available_members': True, 'source_retained': True}
        self.evidence_root = self.root/'disconnect'; self.evidence_root.mkdir(mode=0o700)
        for name, raw in self.evidence.items():
            path = self.evidence_root/name
            path.write_bytes(raw); path.chmod(0o600)

    def regular(self, path, limit):
        raw = Path(path).read_bytes()
        self.assertLessEqual(len(raw), limit)
        return raw

    def disconnect_verify(self, value):
        raw = encode(value)
        return P['disconnect'](raw, sha(raw), self.admission, self.candidate,
            {'keyboard-disconnect-probe': '7'*64}, self.evidence_root, self.regular)

    def test_historical_source_pin_is_explicit_and_does_not_replace_other_checks(self):
        historical = copy.deepcopy(self.disconnect)
        historical['monitor']['source_sha256'] = 'a'*64
        raw = encode(historical)
        args = (raw, sha(raw), self.admission, self.candidate,
                {'keyboard-disconnect-probe': '7'*64}, self.evidence_root, self.regular)
        with self.assertRaisesRegex(ValueError, 'monitor binding'):
            P['disconnect'](*args)
        P['disconnect'](*args, monitor_source_sha256='a'*64)
        for invalid in ('', 'b'*64):
            with self.assertRaises(ValueError):
                P['disconnect'](*args, monitor_source_sha256=invalid)
        (self.evidence_root/'observer.stdout').write_bytes(b'changed\n')
        with self.assertRaisesRegex(ValueError, 'evidence inventory'):
            P['disconnect'](*args, monitor_source_sha256='a'*64)

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
        self.disconnect_verify(self.disconnect)
        changed = copy.deepcopy(self.disconnect); changed['classification'] = 'inconclusive'
        with self.assertRaisesRegex(ValueError, 'disconnect'):
            P['disconnect'](encode(changed), sha(encode(changed)), self.admission, self.candidate,
                            {'keyboard-disconnect-probe': '7'*64}, self.evidence_root, self.regular)
        with self.assertRaisesRegex(ValueError, 'disconnect receipt digest'):
            P['disconnect'](raw, 'f'*64, self.admission, self.candidate,
                            {'keyboard-disconnect-probe': '7'*64}, self.evidence_root, self.regular)

    def test_disconnect_each_decisive_boolean_refuses(self):
        for group, key in (('claim', 'retained'), ('transport', 'deliberate_disconnect'),
                ('process', 'monitor_reaped'), ('process', 'observer_reaped'),
                ('preservation', 'complete_available_members'),
                ('reader_release', 'tty1_reader_absent'), ('reader_release', 'input_reader_absent')):
            changed = copy.deepcopy(self.disconnect)
            changed[group][key] = False
            with self.subTest(group=group, key=key), self.assertRaises(ValueError):
                self.disconnect_verify(changed)

    def test_disconnect_missing_null_or_mutated_raw_evidence_refuses(self):
        changed = copy.deepcopy(self.disconnect)
        changed['preservation']['members'] = {name: None for name in P['FILES']}
        with self.assertRaises(ValueError):
            self.disconnect_verify(changed)
        path = self.evidence_root/'monitor.status'
        path.write_bytes(path.read_bytes().replace(b'reaped=1', b'reaped=0'))
        with self.assertRaisesRegex(ValueError, 'evidence inventory/digests'):
            self.disconnect_verify(self.disconnect)

    def test_disconnect_rehashed_contradictory_evidence_refuses(self):
        mutations = {
            'observer.stdout': b'',
            'observer.stderr': b'unexpected\n',
            'monitor.status': self.evidence['monitor.status'].replace(b'reaped=1', b'reaped=0'),
            'monitor-late-times': self.evidence['monitor.status'].replace(
                b'term_ms=10\nkill_ms=90', b'term_ms=600\nkill_ms=700'),
            'outer-exit': b'0\n',
            'disconnect-process.json': self.evidence['disconnect-process.json'].replace(
                b'deliberate-client-disconnect', b'inconclusive'),
            'disconnect-process-late': self.evidence['disconnect-process.json'].replace(
                b'"elapsed_milliseconds": 50', b'"elapsed_milliseconds": 101'),
            'export-process.json': self.evidence['export-process.json'].replace(
                b'"exit_status": 0', b'"exit_status": 1'),
            'reader-scan.json': self.evidence['reader-scan.json'].replace(b'"matches": []', b'"matches": ["pid"]')}
        for name, raw in mutations.items():
            with self.subTest(name=name):
                evidence_name = {'monitor-late-times':'monitor.status',
                    'disconnect-process-late':'disconnect-process.json'}.get(name,name)
                path = self.evidence_root/evidence_name
                original = path.read_bytes()
                changed = copy.deepcopy(self.disconnect)
                path.write_bytes(raw)
                changed['evidence'][evidence_name] = sha(raw)
                if evidence_name in P['FILES']:
                    changed['preservation']['members'][evidence_name] = sha(raw)
                try:
                    with self.assertRaises(ValueError):
                        self.disconnect_verify(changed)
                finally:
                    path.write_bytes(original)

    def test_disconnect_missing_evidence_file_refuses(self):
        path = self.evidence_root/'export-process.json'
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.disconnect_verify(self.disconnect)

    def test_duration_exact_tracked_receipt(self):
        raw = P['DURATION'].read_bytes()
        receipt = json.loads(raw)
        repo = HERE.parents[2]
        historical = subprocess.check_output(['git', '-C', str(repo), 'show',
            receipt['source_revision'] + ':' + (HERE/'monitor.c').relative_to(repo).as_posix()])
        source_sha = sha(historical)
        self.assertEqual(source_sha, receipt['source_inputs']['monitor.c'])
        P['duration'](raw, sha(raw), source_sha)
        with self.assertRaisesRegex(ValueError, 'duration monitor source'):
            P['duration'](raw, sha(raw), sha((HERE/'monitor.c').read_bytes()))
        changed_source = json.loads(raw)
        changed_source['source_inputs']['monitor.c'] = '0'*64
        mutated_source = encode(changed_source)
        with self.assertRaisesRegex(ValueError, 'duration monitor source'):
            P['duration'](mutated_source, sha(mutated_source), source_sha)
        changed = json.loads(raw)
        changed['classification']['classification'] = 'inconclusive'
        mutated = encode(changed)
        with self.assertRaisesRegex(ValueError, 'duration outcome'):
            P['duration'](mutated, sha(mutated), source_sha)


if __name__ == '__main__':
    unittest.main()
