#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Standard client retention/default dispatch; no network or device in fixtures."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = load('standard_retention_test', HERE.parent / 'laptop-wifi-ssh-retain.py')
F = load('standard_retained_fixtures', HERE / 'ssh-observation-test.py')


class StandardTests(unittest.TestCase):
    def exercise(self, rc=0, route_rc=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'observed'
            calls = []

            def runner(argv, **kwargs):
                calls.append(argv)
                if argv[0] == '/usr/sbin/netstat':
                    self.assertEqual(argv, ['/usr/sbin/netstat', '-rn', '-f', 'inet'])
                    self.assertEqual(kwargs['timeout'], 0.5)
                    return subprocess.CompletedProcess(argv, route_rc, stdout=b'Internet:\nfixture routes\n')
                if argv[0] == '/usr/sbin/arp':
                    self.assertEqual(argv[-1], '10.0.0.55')
                    return subprocess.CompletedProcess(argv, 0, stdout=b'fixture neighbor\n')
                self.assertNotEqual(argv[0], '/sbin/route')
                if any(a.startswith('HostKeyAlias=') for a in argv):
                    self.assertEqual(argv, S.D.O.C.M.wifi_command(Path('/unused'), '10.0.0.55', 1))
                    if rc:
                        kwargs['stderr'].write(b'ssh: connect to host fixture port 22: Operation timed out\n')
                    return subprocess.CompletedProcess(argv, rc, stdout=F.SERVED if not rc else b'partial')
                return subprocess.CompletedProcess(argv, 0, stdout=F.PROBE)

            old = S.D.O.C.M.base_command
            umask = os.umask(0o077)
            try:
                S.D.O.C.M.base_command = lambda keys: (['ssh'], 'root@10.0.0.1')
                result = S.run(root, Path('/unused'), F.BOOT, 1, 90, runner)
            finally:
                S.D.O.C.M.base_command = old
                os.umask(umask)
            self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in root.iterdir()))
            return result, calls, (root / 'stderr.bin').read_bytes(), \
                json.loads((root / 'local-queries.json').read_bytes())

    def test_standard_success_retains_stdout_stderr_and_netstat(self):
        result, calls, error, _ = self.exercise()
        self.assertTrue(result['all_pass'] and result['client_retention_enabled'])
        self.assertTrue(result['client_observation_created'])
        self.assertEqual(error, b'')
        self.assertEqual(sum(a[0] == '/usr/sbin/netstat' for a in calls), 1)

    def test_standard_failure_retains_full_error_without_ack(self):
        result, _, error, _ = self.exercise(rc=255)
        self.assertFalse(result['all_pass'])
        self.assertFalse(result['cycles'][0]['ack_written'])
        self.assertEqual(error, b'ssh: connect to host fixture port 22: Operation timed out\n')

    def test_failed_route_snapshot_stays_unknown_and_does_not_replace_ssh(self):
        result, _, _, observations = self.exercise(route_rc=71)
        self.assertTrue(result['all_pass'])
        self.assertEqual(observations['queries'][0]['exit'], 71)

    def test_actual_standard_host_launch_selects_retention_once(self):
        source = (HERE.parent / 'passive-host-ccmp.py').read_text()
        tree = ast.parse(source)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'NativeWifiHelper')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'start')
        namespace = {'sys': sys, 'HERE': HERE.parent}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'actual-standard-start', 'exec'), namespace)
        calls = []
        helper = types.SimpleNamespace(enabled=lambda: True, record={'started': False},
                   keys=Path('/fixture'), boot=F.BOOT, receipt_path=Path('/fixture/receipt'), poll=90,
                   spawn=lambda argv, **kwargs: calls.append((argv, kwargs)) or types.SimpleNamespace(pid=123))
        namespace['start'](helper); namespace['start'](helper)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][1], str(HERE.parent / 'laptop-wifi-ssh-retain.py'))
        self.assertTrue(calls[0][1]['start_new_session'])

    def test_standard_cli_accepts_owned_gtk_namespace(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary).resolve(); keys = runtime / 'keys'; keys.mkdir()
            (keys / 'admin').touch(); (keys / 'known_hosts').touch()
            receipt = runtime / 'ccmp-stable-monitor/session-ccmp-gtk1/wifi-ssh-receipt.json'
            receipt.parent.mkdir(parents=True)
            result = {'boot_id': F.BOOT, 'cycles_expected': 1, 'cycles': [], 'all_pass': False}
            original = S.D.O.C.M.run
            try:
                with patch.object(S.sys, 'platform', 'darwin'), \
                     patch.object(S.sys, 'argv', ['standard', str(keys), F.BOOT, '--cycles', '1',
                                                 '--receipt', str(receipt)]), \
                     patch.dict(os.environ, {'GEMINI_RUNTIME_ROOT': str(runtime)}), \
                     patch.object(S, 'run', return_value=result) as run:
                    self.assertEqual(S.main(), 1)
                    run.assert_called_once_with(receipt.parent / 'ssh-client-observation',
                                                keys, F.BOOT, 1, 90)
                self.assertEqual(json.loads(receipt.read_text()), result)
            finally:
                S.D.O.C.M.run = original


if __name__ == '__main__':
    unittest.main()
