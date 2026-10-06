#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject incomplete join evidence and unsafe private AP input."""

import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]
classify = runpy.run_path(str(HERE / 'classify-join.py'))['classify']
bind = runpy.run_path(str(HERE / 'bind-target.py'))['bind']


def log(accepted):
    lines = ['grant: channel=40 interval_ms=9000', 'peer: ready=1 sequence=8',
             'credit: pages=4 remaining=0', 'TX: subtype=11 pid=1 pages=1',
             'TX done: pid=1 status=0 advanced=0 count=0', 'RX: subtype=11 status=0',
             'TX: subtype=0 pid=2 pages=1', 'TX done: pid=2 status=0 advanced=0 count=0',
             'RX: subtype=1 status=' + ('0' if accepted else '31')]
    if accepted:
        lines += ['credit: pages=3 remaining=0', 'activation: sequence=9 state=3',
                  'TX: subtype=12 pid=3 pages=1', 'TX done: pid=3 status=0 advanced=0 count=0']
    lines += ['credit: pages=' + ('3' if accepted else '2') + ' remaining=0']
    for stage in range(3):
        lines += ['cleanup submission: stage=' + str(stage), 'credit: pages=1 remaining=0']
    lines += ['cleanup: stage=3 credits=returned slots=retired deauth=' + str(int(accepted))]
    return ''.join('one-shot WLAN join ' + line + '\n' for line in lines).encode()


class HostTests(unittest.TestCase):
    def test_accepted_and_refused_exchange(self):
        for accepted in (False, True):
            result = classify(log(accepted))
            self.assertTrue(result['bounded_join_pass'])
            self.assertEqual(result['associated_station_activation_demonstrated'], accepted)
            self.assertFalse(result['wifi_operational'])

    def test_incomplete_or_duplicate_evidence(self):
        raw = log(True)
        mutations = [raw.replace(b'status=0 advanced', b'status=1 advanced', 1),
                     raw.replace(b'activation: sequence=9 state=3', b'activation: sequence=9 state=1'),
                     raw.replace(b'credit: pages=3 remaining=0', b'credit: pages=2 remaining=0', 1),
                     raw + b'one-shot WLAN join TX: subtype=11 pid=1 pages=1\n',
                     raw + b'one-shot WLAN join stopped: status=-5\n',
                     raw.replace(b'cleanup: stage=3', b'cleanup: stage=2'),
                     raw.replace(b'pid=2 status=0', b'pid=3 status=0')]
        for mutation in mutations:
            self.assertFalse(classify(mutation)['bounded_join_pass'])
        self.assertFalse(classify(b'')['bounded_join_pass'])

    def test_target_shell_quoting_and_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target.json'
            source = Path(directory) / 'source.sh'
            source.write_text('printf %s "$TARGET_SSID"\n')
            value = {'ssid': "lab';$(exit 9)", 'bssid': '02:00:00:00:00:01',
                     'frequency_mhz': 5200, 'channel': 40}
            target.write_text(json.dumps(value))
            target.chmod(0o600)
            self.assertEqual(subprocess.check_output(['sh'], input=bind(target, source)), value['ssid'].encode())
            for key, bad in [('ssid', 'bad\nline'), ('bssid', 'ff:00:00:00:00:01'),
                             ('frequency_mhz', 5180), ('channel', 36)]:
                changed = dict(value, **{key: bad})
                target.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    bind(target, source)
            target.chmod(0o644)
            with self.assertRaises(ValueError):
                bind(target, source)


if __name__ == '__main__':
    unittest.main()
