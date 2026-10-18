#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse D1's actual-source CCMP fixtures with the bounded local observations."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D = load(HERE.parent / 'laptop-wifi-ssh-neighbor.py', 'neighbor_observer_test')
F = load(HERE / 'ssh-observation-test.py', 'existing_ssh_fixtures')


class NeighborTests(unittest.TestCase):
    def exercise(self, rc=0, query_timeout=False, query_error=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'observation'
            calls = []

            def runner(argv, **kwargs):
                calls.append((argv, kwargs))
                if argv[0] in ('/sbin/route', '/usr/sbin/arp'):
                    self.assertEqual(kwargs, {'stdout': subprocess.PIPE,
                                             'stderr': subprocess.STDOUT, 'timeout': 0.5})
                    self.assertEqual(argv[-1], '10.0.0.55')
                    if query_timeout:
                        raise subprocess.TimeoutExpired(argv, 0.5, output=b'partial')
                    if query_error:
                        raise FileNotFoundError('system tool absent')
                    return subprocess.CompletedProcess(argv, 0, stdout=b'fixture local state\n')
                if any(arg.startswith('HostKeyAlias=') for arg in argv):
                    self.assertEqual(argv, D.O.C.M.wifi_command(Path('/unused'), '10.0.0.55', 1))
                    if rc:
                        kwargs['stderr'].write(b'ssh: connect to host 10.0.0.55 port 22: Operation timed out\n')
                    return subprocess.CompletedProcess(argv, rc, stdout=F.SERVED if not rc else b'')
                self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
                return subprocess.CompletedProcess(argv, 0, stdout=F.PROBE)

            old = D.O.C.M.base_command
            mask = os.umask(0o077)
            try:
                D.O.C.M.base_command = lambda keys: (['ssh'], 'root@10.0.0.1')
                observed = D.O.observing_runner(root, runner=D.neighbor_runner(root, runner))
                result = D.O.C.run(Path('/unused'), F.BOOT, 1, 90, runner=observed)
            finally:
                D.O.C.M.base_command = old
                os.umask(mask)
            record = json.loads((root / 'local-queries.json').read_text())
            entries = record['queries']
            self.assertGreaterEqual(record['client_ended_ns'], record['client_started_ns'])
            self.assertLessEqual(record['client_timeout_s'], 25)
            self.assertEqual([e['label'] for e in entries], ['route-before', 'arp-before', 'arp-after'])
            self.assertEqual(len([a for a, _ in calls if a[0] == '/sbin/route']), 1)
            self.assertEqual(len([a for a, _ in calls if a[0] == '/usr/sbin/arp']), 2)
            self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in root.iterdir()))
            return result, entries, (root / 'stderr.bin').read_bytes(), calls

    def test_success_retains_three_queries_and_original_ack(self):
        result, entries, _, calls = self.exercise()
        self.assertTrue(result['all_pass'])
        self.assertTrue(all(e['exit'] == 0 and not e['timeout'] for e in entries))
        self.assertEqual(len(calls), 6)  # 3 local reads, original 3 SSH calls

    def test_tcp_error_retained_with_no_ack_and_after_snapshot(self):
        result, entries, error, calls = self.exercise(rc=255)
        self.assertFalse(result['all_pass'])
        self.assertFalse(result['cycles'][0]['ack_written'])
        self.assertIn(b'Operation timed out', error)
        self.assertEqual(len(entries), 3)
        self.assertEqual(len(calls), 5)

    def test_query_timeout_is_unknown_not_an_absent_neighbor(self):
        result, entries, _, _ = self.exercise(query_timeout=True)
        self.assertTrue(result['all_pass'])  # only original SSH proof can admit ACK
        self.assertTrue(all(e['exit'] is None and e['timeout'] and e['bytes'] == 7 for e in entries))

    def test_query_execution_error_is_unknown_and_does_not_change_ssh(self):
        result, entries, _, _ = self.exercise(query_error=True)
        self.assertTrue(result['all_pass'])
        self.assertTrue(all(e['error'] == 'FileNotFoundError' and e['exit'] is None for e in entries))


if __name__ == '__main__':
    unittest.main()
