#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test return attribution and finite collection without SSH or device access."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
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


R = load('service_return', HERE / 'a53-ram-return.py')
BASELINE = HERE.parent / '2026-09-05-owner-away-experiment-preparation/baseline/scripts'
C = load('return_runner', BASELINE / 'collect-baseline.py')
F = load('return_finish', BASELINE / 'finish-baseline.py')
PREVIOUS = '11111111-1111-4111-8111-111111111111'
MAINLINE = '22222222-2222-4222-8222-222222222222'
RETURNED = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'


def frame(boot=RETURNED):
    return ('__A53_GEMIAN_RETURN_BEGIN__\nboot_before=' + boot + '\n' +
            ''.join(key + '=' + value + '\n' for key, value in R.EXPECTED.items()) +
            'boot_after=' + boot + '\n__A53_GEMIAN_RETURN_END__\n').encode()


def process(raw, stderr=b'', **changes):
    return dict({'stdout_bytes': len(raw), 'stderr_bytes': len(stderr), 'exit_status': 0,
                 'reason': None, 'stdin_complete': True}, **changes)


class ReturnTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='a53-return-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root.chmod(0o700)
        self.key, self.trust = self.root / 'key', self.root / 'trust'
        C.write_new(self.key, b'inert fixture key\n')
        C.write_new(self.trust, b'inert fixture trust\n')
        self.trust_patch = patch.object(R, 'TRUST_SHA', R.sha(self.trust.read_bytes()))
        self.trust_patch.start()
        self.addCleanup(self.trust_patch.stop)
        self.now = 0.0
        self.calls = []
        self.clock = SimpleNamespace(monotonic=lambda: self.now, sleep=self.sleep)
        self.prepared = {'collector': C, 'finish': F, 'command': ['inert-transport'],
                         'key': self.key, 'key_sha256': R.sha(self.key.read_bytes()),
                         'trust': self.trust, 'previous': PREVIOUS, 'mainline': MAINLINE,
                         'output': self.root / 'return', 'binding': {'fixture': True}}

    def sleep(self, seconds):
        self.assertGreaterEqual(seconds, 0)
        self.now += seconds

    def collect(self, responses, change_credentials=False):
        def invoke(command, script, child, timeout, **limits):
            self.assertEqual(command, ['inert-transport'])
            self.assertEqual(script, R.PROBE)
            self.assertEqual(limits, {'stdout_limit': 4096, 'stderr_limit': 16384})
            self.calls.append((self.now, timeout))
            raw, err, status = responses[min(len(self.calls) - 1, len(responses) - 1)]
            C.write_new(child / 'stdout.txt', raw)
            C.write_new(child / 'stderr.txt', err)
            if change_credentials:
                self.key.write_bytes(b'replaced fixture key\n')
            return status
        with patch.object(R, 'time', self.clock), patch.object(C, 'run_once', invoke):
            return R.watch(self.prepared)

    def test_changed_boot_and_identity_refusals(self):
        raw = frame()
        self.assertTrue(R.classify(raw, b'', process(raw), PREVIOUS, MAINLINE)['recovery_confirmed'])
        rejected = [frame(boot) for boot in (PREVIOUS, MAINLINE, '0' * 8 + '-0000-0000-0000-000000000000',
                                            RETURNED.upper())]
        rejected += [raw[:-1], raw + b'extra\n', raw.replace(b'\n', b'\r\n'),
                     raw.replace(b'boot_after=' + RETURNED.encode(), b'boot_after=' + PREVIOUS.encode()),
                     raw.replace(b'pid1=systemd\n', b'pid1=systemd\npid1=systemd\n')]
        rejected += [raw.replace((key + '=' + value).encode(), (key + '=wrong').encode())
                     for key, value in R.EXPECTED.items()]
        for data in rejected:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    R.classify(data, b'', process(data), PREVIOUS, MAINLINE)
        for changes in ({'reason': 'outer-timeout'}, {'stdin_complete': False}, {'exit_status': 255},
                        {'stdout_bytes': len(raw) - 1}):
            with self.assertRaises(ValueError):
                R.classify(raw, b'', process(raw, **changes), PREVIOUS, MAINLINE)

    def test_only_pre_authentication_connect_failures_allow_waiting(self):
        for err in R.CONNECT_FAILURES:
            for reason in (None, 'stdin-closed'):
                result = R.classify(b'', err, process(b'', err, exit_status=255, reason=reason,
                                                     stdin_complete=False), PREVIOUS, MAINLINE)
                self.assertEqual(result['classification'], 'connection-unavailable')
        for err in (b'Permission denied (publickey).\n', b'Host key verification failed.\n', b'unknown\n'):
            with self.assertRaises(ValueError):
                R.classify(b'', err, process(b'', err, exit_status=255), PREVIOUS, MAINLINE)
        err = next(iter(R.CONNECT_FAILURES))
        for raw, reason in ((b'partial frame', None), (b'', 'outer-timeout'), (b'', 'interrupted')):
            with self.assertRaises(ValueError):
                R.classify(raw, err, process(raw, err, exit_status=255, reason=reason), PREVIOUS, MAINLINE)

    def test_delayed_return_preservation_and_no_second_window(self):
        err = next(iter(R.CONNECT_FAILURES))
        result = self.collect([(b'', err, process(b'', err, exit_status=255)),
                               (frame(), b'', process(frame()))])
        self.assertTrue(result['recovery_confirmed'])
        self.assertEqual(self.calls, [(0.0, 15), (15.0, 15)])
        output = self.prepared['output']
        self.assertEqual(json.loads((output / 'claim.json').read_text())['budget'], 'consumed')
        manifest = (output / 'SHA256SUMS').read_text()
        for line in manifest.splitlines():
            expected, name = line.split('  ', 1)
            self.assertEqual(R.sha(C.regular(output / name, 131072)), expected)
        self.assertIn('not-classified-by-return-collector', result['baseline_success'])
        with self.assertRaises(FileExistsError):
            self.collect([(frame(), b'', process(frame()))])
        self.assertEqual((output / 'SHA256SUMS').read_text(), manifest)

    def test_finite_window_and_unknown_failure_stop(self):
        err = next(iter(R.CONNECT_FAILURES))
        result = self.collect([(b'', err, process(b'', err, exit_status=255))])
        self.assertFalse(result['recovery_confirmed'])
        self.assertEqual(self.calls, [(15.0 * i, 15) for i in range(12)])
        self.assertLessEqual(result['elapsed_seconds'], 180)
        self.prepared['output'] = self.root / 'unknown-failure'
        self.calls = []
        err = b'Host key verification failed.\n'
        result = self.collect([(b'', err, process(b'', err, exit_status=255))])
        self.assertFalse(result['recovery_confirmed'])
        self.assertEqual(result['attempts'], 1)

    def test_credential_change_stops_before_next_connection(self):
        err = next(iter(R.CONNECT_FAILURES))
        result = self.collect([(b'', err, process(b'', err, exit_status=255))], change_credentials=True)
        self.assertFalse(result['recovery_confirmed'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result['reason'], 'Gemian credentials changed')

    def test_real_host_runner_with_inert_child_and_output_limit(self):
        raw = frame()
        for name, data in (('complete', raw), ('oversize', b'x' * 5000)):
            child = self.root / name
            child.mkdir(mode=0o700)
            command = [sys.executable, '-c', 'import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write(' + repr(data) + ')']
            status = C.run_once(command, R.PROBE, child, 5, stdout_limit=4096, stderr_limit=16384)
            saved = C.regular(child / 'stdout.txt', 4096)
            if name == 'complete':
                self.assertTrue(R.classify(saved, b'', status, PREVIOUS, MAINLINE)['recovery_confirmed'])
            else:
                self.assertEqual(len(saved), 4096)
                self.assertEqual(status['reason'], 'stdout-limit')
                with self.assertRaises(ValueError):
                    R.classify(saved, b'', status, PREVIOUS, MAINLINE)

    def test_probe_shell_and_existing_ssh_policy(self):
        script = self.root / 'probe.sh'
        C.write_new(script, R.PROBE)
        subprocess.run(['sh', '-n', str(script)], check=True, timeout=5)
        subprocess.run(['shellcheck', '--shell=sh', str(script)], check=True, timeout=10)
        command = F.known_good_command({'prepared': {'keys': self.root}})
        self.assertEqual(command[-2:], ['gemini@192.168.1.50', '/bin/sh -s'])
        for setting in ('StrictHostKeyChecking=yes', 'IdentitiesOnly=yes', 'IdentityAgent=none',
                        'ProxyCommand=none', 'ProxyJump=none', 'ClearAllForwardings=yes', 'ConnectionAttempts=1'):
            self.assertIn(setting, command)
        self.assertEqual(command[command.index('-F') + 1], '/dev/null')

    def test_probe_executes_against_fixture_files(self):
        files = {'/proc/sys/kernel/random/boot_id': (RETURNED + '\n').encode(),
                 '/proc/device-tree/model': b'MT6797X\0',
                 '/etc/os-release': b'ID="debian"\nVERSION_ID="9"\n',
                 '/proc/1/comm': b'systemd\n'}
        script = R.PROBE
        for index, (name, data) in enumerate(files.items()):
            path = self.root / ('input-%d' % index)
            C.write_new(path, data)
            script = script.replace(name.encode(), str(path).encode())
        for name, data in {
            'uname': b'#!/bin/sh\ncase "$1" in -r) echo 3.18.41+;; -m) echo aarch64;; *) exit 2;; esac\n',
            'systemctl': b'#!/bin/sh\n[ "$1" = is-system-running ] || exit 2\nif [ "$FIXTURE_STATE" = running-error ]; then echo running; exit 1; fi\necho "$FIXTURE_STATE"\n[ "$FIXTURE_STATE" = running ]\n'
        }.items():
            path = self.root / name
            C.write_new(path, data)
            path.chmod(0o700)
        for state in ('running', 'degraded', 'running-error'):
            status = subprocess.run(['/bin/sh', '-s'], input=script, capture_output=True, timeout=5,
                                    env={'PATH': str(self.root) + ':/usr/bin:/bin', 'LC_ALL': 'C', 'FIXTURE_STATE': state})
            if state == 'running':
                self.assertEqual(status.stdout, frame())
                self.assertEqual(status.returncode, 0, status.stderr)
            else:
                self.assertNotEqual(status.returncode, 0)
                self.assertNotIn(b'__A53_GEMIAN_RETURN_END__', status.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
