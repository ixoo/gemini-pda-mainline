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
    lines = ['credit: pages=1 remaining=0', 'credit: pages=1 remaining=0',
             'grant: channel=40 interval_ms=9000', 'credit: pages=2 remaining=0',
             'peer: ready=1 sequence=8', 'TX: subtype=11 pid=1 pages=1',
             'credit: pages=1 remaining=0',
             'TX done: pid=1 status=0 advanced=0 count=0', 'RX: subtype=11 status=0',
             'TX: subtype=0 pid=2 pages=1', 'credit: pages=1 remaining=0',
             'TX done: pid=2 status=0 advanced=0 count=0',
             'RX: subtype=1 status=' + ('0' if accepted else '31')]
    if accepted:
        lines += ['credit: pages=1 remaining=0', 'credit: pages=2 remaining=0',
                  'activation: sequence=9 state=3',
                  'TX: subtype=12 pid=3 pages=1', 'credit: pages=1 remaining=0',
                  'TX done: pid=3 status=0 advanced=0 count=0']
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
                     raw.replace(b'credit: pages=2 remaining=0', b'credit: pages=1 remaining=0', 1),
                     raw + b'one-shot WLAN join TX: subtype=11 pid=1 pages=1\n',
                     raw + b'one-shot WLAN join stopped: status=-5\n',
                     raw.replace(b'cleanup: stage=3', b'cleanup: stage=2'),
                     raw.replace(b'pid=2 status=0', b'pid=3 status=0')]
        for mutation in mutations:
            self.assertFalse(classify(mutation)['bounded_join_pass'])
        self.assertFalse(classify(b'')['bounded_join_pass'])

    def test_diagnostic_records_are_recognized_not_malformed(self):
        raw = log(False)
        # The runtime-7 shape: cleanup submissions returned, then a refused control
        # event and the footer; no stage-3 line. Diagnostics are recognized, the
        # join is not healthy, and nothing is flagged malformed.
        cut = raw.index(b'one-shot WLAN join cleanup: stage=3')
        tail = (b'one-shot WLAN join control event refused: status=-71 bytes=12 type=0xe000 id=0x11 seq=0\n'
                b'one-shot WLAN join stopped: status=-71 first=0 submitted=0x801 debt=0 cleanup=3 branch=6\n')
        result = classify(raw[:cut] + tail)
        self.assertFalse(result['malformed_stage_record'])
        self.assertEqual(result['diagnostic_records'], ['control event refused'])
        self.assertTrue(result['management_exchange_demonstrated'])
        self.assertFalse(result['healthy_cleanup_demonstrated'])
        self.assertFalse(result['bounded_join_pass'])
        for line in (b'one-shot WLAN join frame refused: bytes=3 type=0x10000 allowed=0x1400\n',
                     b'one-shot WLAN join cleanup refused: stage=3 phase=5 free=25 limit=26 pending_cpu=1 pending_ffa=0 sequences=1 locked=0\n',
                     b'one-shot WLAN join credit overflow: pages=1 debt=0\n',
                     b'one-shot WLAN join bss absence: bss=0 absent=1 quota=0 reserved=0\n'):
            self.assertFalse(classify(raw[:cut] + line + tail)['malformed_stage_record'])
        # A healthy log with an unknown record kind is still malformed, and so is a
        # known diagnostic prefix with the wrong grammar: arbitrary text, a foreign
        # BSS slot, a non-boolean flag, or an extra suffix.
        self.assertTrue(classify(raw + b'one-shot WLAN join mystery: x=1\n')['malformed_stage_record'])
        for bad in (b'one-shot WLAN join bss absence: anything goes\n',
                    b'one-shot WLAN join bss absence: bss=1 absent=1 quota=0 reserved=0\n',
                    b'one-shot WLAN join bss absence: bss=0 absent=2 quota=0 reserved=0\n',
                    b'one-shot WLAN join bss absence: bss=0 absent=1 quota=0 reserved=0 extra=1\n',
                    b'one-shot WLAN join control event refused: status=-71 bytes=12 type=0xe000 id=0x11\n',
                    b'one-shot WLAN join cleanup refused: stage=9 phase=5 free=25 limit=26 pending_cpu=1 pending_ffa=0 sequences=1 locked=0\n'):
            self.assertTrue(classify(raw + bad)['malformed_stage_record'], bad)
        # An admitted indication is recorded as a diagnostic and is not malformed;
        # the stage grammar decides health, so the accepted log stays as classified.
        recorded = classify(log(True) + b'one-shot WLAN join bss absence: bss=0 absent=1 quota=0 reserved=0\n')
        self.assertFalse(recorded['malformed_stage_record'])
        self.assertEqual(recorded['diagnostic_records'], ['bss absence'])

    def test_credit_and_completion_cannot_move_across_stage_fences(self):
        raw = log(True)
        credit = b'one-shot WLAN join credit: pages=2 remaining=0\n'
        late_credit = raw.replace(credit, b'', 1) + credit
        self.assertFalse(classify(late_credit)['bounded_join_pass'])
        done = b'one-shot WLAN join TX done: pid=1 status=0 advanced=0 count=0\n'
        late_done = raw.replace(done, b'') + done
        self.assertFalse(classify(late_done)['bounded_join_pass'])
        stage = b'one-shot WLAN join cleanup submission: stage=1\n'
        self.assertFalse(classify(stage + raw.replace(stage, b''))['bounded_join_pass'])
        # Firmware RX may arrive before the asynchronous completion event.
        response = b'one-shot WLAN join RX: subtype=11 status=0\n'
        early_response = raw.replace(done + response, response + done)
        self.assertTrue(classify(early_response)['bounded_join_pass'])

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
