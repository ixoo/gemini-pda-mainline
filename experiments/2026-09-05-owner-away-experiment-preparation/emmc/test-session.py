#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Same-process fake-transport identity/read/seal and terminal interruption tests."""
from dataclasses import replace
from pathlib import Path
import runpy
import io
from contextlib import redirect_stdout
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
T = runpy.run_path(str(HERE / 'test-finish-emmc.py'))
Q = runpy.run_path(str(HERE / 'session.py'))
Session = Q['Session']
G = Session.start.__func__.__globals__
H = Q['H']
HG = H['identity_window'].__globals__
L, M, C = T['L'], T['M'], T['C']
Base = T['CompletionTests']


class SessionTests(unittest.TestCase):
    setUp = Base.setUp
    fixture_collect = Base.fixture_collect
    seal_manifest = Base.seal_manifest
    admission_for = Base.admission_for
    execute = Base.execute

    def wire(self, changes=None, identity_edit=None, identity_metadata=None):
        self.identity_calls = 0
        def prepare(_):
            L['check_admission'](self.admission)
            return self.context
        def collect(context, execute, window):
            self.assertIs(context, self.context)
            self.assertTrue(execute)
            self.window = window
            result = self.fixture_collect(changes)
            self.observation_hash = L['sha']((self.root / 'attempt/SHA256SUMS').read_bytes())
            return result
        def perform(context, execute, window):
            self.assertIs(window, self.window)
            self.assertTrue(execute)
            return self.execute(context)
        def transport(command, script, directory, seconds, **limits):
            self.identity_calls += 1
            self.assertTrue((directory / 'claim.json').exists())
            expected = (b'BB=/bin/busybox\nexport LC_ALL=C\nset -eu\n'
                b'$BB cat /proc/sys/kernel/random/boot_id\n$BB uname -r\n$BB cat /proc/uptime\n'
                + L['observer_guard'](self.prepared['candidate']))
            self.assertEqual(script, expected)
            self.assertEqual(seconds, 10)
            self.assertEqual(limits, {'stdout_limit': 4096, 'stderr_limit': 4096})
            out = (T['BOOT'] + '\n' + L['S']['RELEASE'] + '\n10.00 9.00\n').encode()
            if identity_edit:
                out = identity_edit(out)
            T['write'](directory / 'stdout.txt', out)
            T['write'](directory / 'stderr.txt', b'')
            return T['process'](out, **(identity_metadata or {}))
        host_module = dict(L, REPO=self.root)
        for mock in (
            patch.dict(G, {'L': dict(L, REPO=self.root, prepare=prepare, collect=collect,
                                    execution_gate=lambda: None),
                           'M': dict(M, perform=perform)}),
            patch.dict(HG, {'runpy': SimpleNamespace(run_path=lambda _: host_module),
                            'require_ready': lambda: {'ready': True}}),
            patch.dict(C, {'run_once': transport}),
        ):
            mock.start(); self.addCleanup(mock.stop)
        return self.root / 'artifacts/a53-authenticated/emmc-readonly/identities' / self.admission['admission_id']

    def test_identity_collect_and_separate_seal_same_process(self):
        directory = self.wire()
        session = Session.start(self.root / 'admission.json')
        self.assertEqual(self.identity_calls, 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.finish_calls, [])
        self.assertEqual(session.dispatch({'action': 'collect'})['classification'],
                         'read-serviceability-only-pass')
        self.assertEqual(self.finish_calls, [])
        self.admission_for('preserve-log')
        result = session.dispatch({'action': 'preserve-log',
                                   'admission': str(self.root / 'admission-preserve-log.json')})
        self.assertIn('classification', result)
        self.assertEqual(self.calls, ['pre', 'read', 'post'])
        self.assertEqual(self.finish_calls, ['preserve-log'])
        self.assertTrue(session.closed)
        self.assertIsNone(session.window)
        self.assertEqual(self.identity_calls, 1)

    def test_failed_read_can_preserve_without_extra_observation(self):
        directory = self.wire({'read': {'process': {'reason': 'outer-timeout'}}})
        session = Session.start(self.root / 'admission.json')
        self.assertEqual(session.dispatch({'action': 'collect'})['classification'], 'inconclusive')
        self.admission_for('preserve-log')
        session.dispatch({'action': 'preserve-log',
                          'admission': str(self.root / 'admission-preserve-log.json')})
        self.assertEqual(self.calls, ['pre', 'read'])
        self.assertEqual(self.finish_calls, ['preserve-log'])

    def test_closed_or_restarted_process_cannot_resume(self):
        directory = self.wire()
        session = Session.start(self.root / 'admission.json')
        session.close()
        with self.assertRaisesRegex(ValueError, 'interrupted or closed'):
            session.dispatch({'action': 'collect'})
        with self.assertRaisesRegex(ValueError, 'restart cannot resume'):
            Session.start(self.root / 'admission.json')
        self.assertEqual(self.identity_calls, 1)
        self.assertEqual(self.calls, [])

    def test_invalid_identity_never_mints_window(self):
        directory = self.wire(identity_edit=lambda out: out.replace(T['BOOT'].encode(), T['FIRST'].encode()))
        with self.assertRaisesRegex(ValueError, 'new identity boot required'):
            Session.start(self.root / 'admission.json')
        self.assertEqual(self.identity_calls, 1)
        self.assertFalse((self.root / 'attempt').exists())

    def test_failed_identity_transport_and_elapsed_guard_refuse(self):
        directory = self.wire(identity_metadata={'reason': 'outer-timeout'})
        with self.assertRaisesRegex(ValueError, 'transport incomplete'):
            Session.start(self.root / 'admission.json')
        self.assertEqual(self.identity_calls, 1)
        self.assertEqual(self.calls, [])

    def test_identity_duration_and_coordination_count_against_lifetime(self):
        directory = self.wire(identity_edit=lambda out: out.replace(b'10.00', b'350.00'))
        # The wrapper starts at 100; mint checks at 150, conservatively age 400.
        with patch('time.monotonic', side_effect=[100.0, 150.0]), \
             patch('time.time', side_effect=[100.0, 150.0]):
            with self.assertRaisesRegex(ValueError, 'insufficient live logger timing'):
                Session.start(self.root / 'admission.json')
        self.assertEqual(self.identity_calls, 1)
        self.assertFalse((self.root / 'attempt').exists())

    def test_cli_interruption_discards_receipt_without_collection(self):
        directory = self.wire()
        session = Session.start(self.root / 'admission.json')
        stream = SimpleNamespace(readline=lambda _: (_ for _ in ()).throw(KeyboardInterrupt()))
        with patch.object(Session, 'start', return_value=session), redirect_stdout(io.StringIO()):
            result = Q['main'](['--execute', '--admission', 'fixture'], stream)
        self.assertEqual(result, 2)
        self.assertTrue(session.closed)
        self.assertIsNone(session.window)
        self.assertEqual(self.calls, [])

    def test_expired_before_collect_never_claims(self):
        directory = self.wire()
        session = Session.start(self.root / 'admission.json')
        session.window = replace(session.window, uptime=400)
        with self.assertRaisesRegex(ValueError, 'insufficient live logger timing'):
            session.dispatch({'action': 'collect'})
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / 'attempt').exists())


del Base  # Do not rediscover the reused fixture class's independent suite.

if __name__ == '__main__':
    unittest.main(verbosity=2)
