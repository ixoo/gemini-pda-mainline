#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise A53 phase ordering and recovery refusals with inert transport."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = load('service_host', HERE / 'a53-ram-host.py')
B = load('service_binding', HERE / 'a53-ram-session.py')
O = load('observation_fixture', H.BASELINE / 'test-collect-baseline.py')
L = load('log_fixture', H.BASELINE / 'test-session-steps.py')
BOOT, PREVIOUS = O.BOOT, O.RECOVERY
RETURNED = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='a53-host-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root.chmod(0o700)
        self.c = load('host_reader', H.BASELINE / 'collect-baseline.py')
        self.s = load('host_steps', H.BASELINE / 'session_steps.py')
        self.s.RELEASE = B.RELEASE
        self.f = load('host_finish', H.BASELINE / 'finish-baseline.py')
        legacy = load('host_classifier', self.c.HISTORICAL / 'classify_observation.py')
        legacy.RELEASE = B.RELEASE
        self.c.source_tools = lambda: vars(legacy)
        members = set(self.c.MEMBERS.values()) | set(L.CANDIDATE['members'])
        self.context = {'candidate': {'members': {name: {'sha256': self.s.REBOOT_SHA if name == 'bin/reboot' else 'a' * 64}
                                                  for name in members},
                                      'files': {'kernel.config': 'b' * 64}},
                        'admission': {'candidate_sha256': 'c' * 64}, 'recovery_id': PREVIOUS}
        self.session = self.root / 'session'
        self.session.mkdir(mode=0o700)
        self.c.write_new(self.session / 'deployment-summary.txt', b'synthetic deployment fixture\n')
        self.key = self.root / 'fixture-key'
        self.c.write_new(self.key, b'inert fixture key\n')
        self.calls, self.route_calls, self.return_calls = [], 0, 0
        self.change = None
        self.responses = {
            'observation': (O.good_capture(self.context).replace(b'7.1.3-gemini-mt6797-pwrap-reset', B.RELEASE.encode()), 0),
            'probe': (('authenticated_boot_id=' + BOOT + '\n').encode(), 0),
            'log-export': (L.frame(), 0),
            'native-reboot': ((f'__A53_NATIVE_RECOVERY_BEGIN__\nboot_id={BOOT}\nreboot_sha256={self.s.REBOOT_SHA}\n'
                              'request_count=1\npartition_access=none\nsync_requested=no\n__A53_NATIVE_RECOVERY_END__\n').encode(), 255)}
        self.prepared = {'candidate_path': self.root / 'unused-candidate', 'context': self.context,
                         'collector': self.c, 'steps': self.s, 'finish': self.f,
                         'binding': {'classify_observation': B.classify_observation, 'SOURCE_PINS': B.SOURCE_PINS},
                         'network': SimpleNamespace(require_ready=self.network),
                         'returning': SimpleNamespace(prepare=self.return_prepare, watch=lambda value: value),
                         'credentials': {self.key: H.sha(self.key.read_bytes())},
                         'deployment': b'synthetic deployment fixture\n', 'root': self.session,
                         'command': ['inert-transport'], 'claim': {'fixture': True}}

    def network(self):
        self.route_calls += 1
        return {'ready': True, 'device_packets_sent': False}

    def return_prepare(self, candidate):
        self.return_calls += 1
        self.assertEqual(candidate, self.prepared['candidate_path'])
        request = self.session / 'native-reboot'
        self.assertEqual({p.name for p in request.iterdir()}, {'command.sh', 'stdout.txt', 'stderr.txt', 'process.json'})
        self.assertTrue((self.session / 'PRE_RECOVERY_SHA256SUMS').is_file())
        return {'recovery_confirmed': True, 'boot_id': RETURNED, 'classification': 'changed-ID-Gemian'}

    def transport(self, command, script, child, seconds, **limits):
        label = child.name
        self.calls.append(label)
        self.assertEqual(command, ['inert-transport'])
        self.assertEqual((seconds, limits['stdout_limit']), H.BUDGETS[label])
        self.assertEqual(limits['stderr_limit'], 16384)
        self.assertEqual(json.loads((self.session / 'execution-claim.json').read_text())['budget'], 'consumed')
        expected = {'observation': self.c.remote_script(self.context), 'probe': self.s.probe_script(self.context['candidate'], BOOT),
                    'log-export': self.s.seal_script(self.context['candidate'], BOOT),
                    'native-reboot': self.s.recovery_script(self.context['candidate'], BOOT)}
        self.assertEqual(script, expected[label])
        if label == 'native-reboot':
            manifest = self.c.regular(self.session / 'PRE_RECOVERY_SHA256SUMS', 16384)
            snapshot = self.f.verified_snapshot(self.session, manifest)
            self.assertEqual(snapshot['kmsg.log'], L.LOG)
        raw, code = self.responses[label]
        self.c.write_new(child / 'stdout.txt', raw)
        self.c.write_new(child / 'stderr.txt', b'')
        if self.change:
            self.change(label)
        return {'stdout_bytes': len(raw), 'stderr_bytes': 0, 'stdin_complete': True,
                'exit_status': code, 'reason': None}

    def run_session(self):
        with patch.object(self.c, 'run_once', self.transport):
            return H.execute(self.prepared)

    def test_success_orders_preservation_before_recovery_and_refuses_reuse(self):
        result = self.run_session()
        self.assertTrue(result['regression_pass'])
        self.assertEqual(result['returned_gemian_boot'], RETURNED)
        self.assertEqual(self.calls, list(H.BUDGETS))
        self.assertEqual(self.return_calls, 1)
        self.assertEqual(self.route_calls, 4)
        self.assertEqual(json.loads((self.session / 'session-result.json').read_text()), result)
        with self.assertRaises(ValueError):
            self.run_session()
        self.assertEqual(len(self.calls), 4)

    def test_bad_observation_stops_after_one_connection(self):
        raw, code = self.responses['observation']
        self.responses['observation'] = (raw.replace(b'cpu_online_after=0-7', b'cpu_online_after=0-9'), code)
        result = self.run_session()
        self.assertFalse(result['regression_pass'])
        self.assertEqual(self.calls, ['observation'])
        self.assertEqual(self.return_calls, 0)

    def test_changed_boot_probe_stops_before_log_or_recovery(self):
        self.responses['probe'] = (('authenticated_boot_id=' + PREVIOUS + '\n').encode(), 0)
        result = self.run_session()
        self.assertFalse(result['recovery_requested'])
        self.assertEqual(self.calls, ['observation', 'probe'])

    def test_partial_export_is_saved_without_recovery(self):
        raw = L.frame()[:-12]
        self.responses['log-export'] = (raw, 0)
        result = self.run_session()
        self.assertFalse(result['recovery_requested'])
        self.assertEqual(self.calls, ['observation', 'probe', 'log-export'])
        self.assertEqual((self.session / 'log-export/stdout.txt').read_bytes(), raw)
        self.assertEqual((self.session / 'kmsg.log').read_bytes(), L.LOG)

    def test_failed_logger_with_complete_preservation_can_return(self):
        self.responses['log-export'] = (L.frame(raw_status=L.status(result='failed', reason='read-failed'),
            stop='preexisting-terminal', overrides={'kmsg-exit': {'data': b'1\n'}}), 0)
        result = self.run_session()
        self.assertTrue(result['recovery_requested'])
        self.assertTrue(result['recovery_confirmed'])
        self.assertFalse(result['regression_pass'])
        self.assertEqual(result['classification'], 'returned-with-incomplete-log')

    def test_corruption_after_manifest_stops_recovery(self):
        original = self.f.verified_snapshot
        def corrupt(root, manifest):
            (root / 'kmsg.log').write_bytes(b'changed saved log\n')
            return original(root, manifest)
        with patch.object(self.f, 'verified_snapshot', corrupt):
            result = self.run_session()
        self.assertFalse(result['recovery_requested'])
        self.assertNotIn('native-reboot', self.calls)

    def test_changed_observation_before_manifest_is_reclassified(self):
        def change(label):
            if label == 'log-export':
                (self.session / 'observation/stdout.txt').write_bytes(b'changed evidence\n')
        self.change = change
        result = self.run_session()
        self.assertFalse(result['recovery_requested'])
        self.assertNotIn('native-reboot', self.calls)

    def test_changed_credentials_stop_next_connection(self):
        def change(label):
            if label == 'probe':
                self.key.write_bytes(b'changed key\n')
        self.change = change
        result = self.run_session()
        self.assertFalse(result['recovery_requested'])
        self.assertEqual(self.calls, ['observation', 'probe'])

    def test_changed_saved_log_count_stops_recovery(self):
        original = H.preserved_snapshot
        def altered(prepared, boot):
            path = self.session / 'log-export/process.json'
            process = json.loads(path.read_text())
            process['stdout_bytes'] += 1
            path.write_bytes(H.encoded(process))
            return original(prepared, boot)
        with patch.object(H, 'preserved_snapshot', altered):
            result = self.run_session()
        self.assertFalse(result['recovery_requested'])
        self.assertNotIn('native-reboot', self.calls)

    def test_missing_route_does_not_claim_or_connect(self):
        self.prepared['network'].require_ready = lambda: (_ for _ in ()).throw(ValueError('route absent'))
        with self.assertRaises(ValueError):
            self.run_session()
        self.assertFalse((self.session / 'execution-claim.json').exists())
        self.assertEqual(self.calls, [])

    def test_changed_deployment_does_not_claim_or_connect(self):
        (self.session / 'deployment-summary.txt').write_bytes(b'changed deployment\n')
        with self.assertRaises(ValueError):
            self.run_session()
        self.assertFalse((self.session / 'execution-claim.json').exists())
        self.assertEqual(self.calls, [])
        self.assertEqual(self.route_calls, 0)

    def test_returned_helper_cannot_confirm_recovery(self):
        raw, _ = self.responses['native-reboot']
        self.responses['native-reboot'] = (raw, 0)
        result = self.run_session()
        self.assertIsNone(result['recovery_requested'])
        self.assertFalse(result['recovery_confirmed'])
        self.assertEqual(self.return_calls, 0)

    def test_return_silence_cannot_pass_regression(self):
        self.prepared['returning'].watch = lambda _value: {'recovery_confirmed': False, 'classification': 'return-unconfirmed'}
        result = self.run_session()
        self.assertTrue(result['recovery_requested'])
        self.assertFalse(result['regression_pass'])
        self.assertFalse(result['recovery_confirmed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
