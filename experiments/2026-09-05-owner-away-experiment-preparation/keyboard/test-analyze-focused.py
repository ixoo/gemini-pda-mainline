#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic stream checks for repeat-aware inspection; no runtime witnesses."""
from pathlib import Path
import runpy
import unittest

HERE = Path(__file__).resolve().parent
MODULE = runpy.run_path(str(HERE/'analyze-focused.py'))


def capture(*, repeat=True, wrong_vt=False, missing_digit=False):
    lines = ['keyboard-diagnostic version=1',
             'repeat delay_ms=250 period_ms=33 planned_events=974 limit=1024',
             'device event=event0 major=13 minor=64 name=keyboard-matrix',
             'window elapsed_ms=2000 events=0 bytes=0 held=0',
             'preflight state=pass vt=1 unicode=1 held=0 functions=exact']
    for index, (edges, vt) in enumerate(MODULE['EXPECTED']):
        lines.append(f'step begin index={index}')
        events = []
        for code, value in edges:
            if missing_digit and index == 1 and code == 2:
                continue
            events += [(4, 4, MODULE['V1']['SCANS'][code]), (1, code, value), (0, 0, 0)]
            if repeat and index == 1 and code == 125 and value == 1:
                events += [(1, 125, 2), (0, 0, 1)] * 80
        lines += [f'event {i} {kind} {code} {value}' for i, (kind, code, value) in enumerate(events)]
        actual_vt = '61' if wrong_vt and index == 1 else vt
        lines += ['tty hex=' + actual_vt,
                  f'window elapsed_ms=15000 events={len(events)} bytes={len(actual_vt)//2} held=0',
                  f'step end index={index}']
    return ('\n'.join(lines + ['complete steps=2 restored=1']) + '\n').encode()


class AnalysisTests(unittest.TestCase):
    def test_repeat_is_not_an_extra_physical_press(self):
        result = MODULE['analyze'](capture())
        self.assertEqual(result['outcome'], 'observations-complete')
        self.assertEqual(result['cases'][1], {'index': 1, 'input': 'match', 'vt': 'match',
                                            'physical_edges': 8, 'repeat_events': 80})
        self.assertFalse(result['hardware_claim'])
        self.assertFalse(result['session_receipt_verified'])

    def test_no_repeats(self):
        self.assertEqual(MODULE['analyze'](capture(repeat=False))['cases'][1]['repeat_events'], 0)

    def test_input_and_vt_mismatches_are_separate(self):
        vt = MODULE['analyze'](capture(wrong_vt=True))['cases'][1]
        self.assertEqual((vt['input'], vt['vt']), ('match', 'mismatch'))
        edges = MODULE['analyze'](capture(missing_digit=True))['cases'][1]
        self.assertEqual((edges['input'], edges['vt']), ('mismatch', 'match'))

    def test_incomplete_or_malformed_streams_refuse(self):
        good = capture()
        changes = [
            (b'period_ms=33', b'period_ms=0'),
            (b'planned_events=974', b'planned_events=973'),
            (b'elapsed_ms=2000', b'elapsed_ms=1999'),
            (b'event 0 4 4 0', b'event 15000 4 4 0'),
            (b'event 1 1 2 1', b'event 0 1 2 0'),
            (b'event 1 1 2 1', b'event 1 1 2 2'),
            (b'event 2 0 0 0', b'event 2 0 3 0'),
            (b'event 2 0 0 0', b'event 2 0 0 1'),
            (b'event 2 0 0 0', b'event 0 0 0 0'),
            (b'event 4 1 2 0', b'event 4 1 2 1'),
            (b'event 4 1 2 0', b'event 4 1 3 0'),
            (b'events=6 bytes=1', b'events=5 bytes=1'),
            (b'elapsed_ms=15000', b'elapsed_ms=14999'),
            (b'tty hex=31', b'tty hex=3'),
            (b'tty hex=31', b'tty hex=' + b'31' * 129),
            (b'complete steps=2 restored=1', b'complete steps=2 restored=0'),
            (b'event 1 1 2 1', b'overflow 1 1 2 1'),
        ]
        for old, new in changes:
            with self.subTest(old=old, new=new):
                self.assertIn(old, good)
                self.assertEqual(MODULE['analyze'](good.replace(old, new, 1))['outcome'], 'inconclusive')
        for bad in [good[:-1], good + b'trailing\n', b'x' * 98305, good.replace(b'event 1', b'event \xff', 1)]:
            self.assertEqual(MODULE['analyze'](bad)['outcome'], 'inconclusive')


if __name__ == '__main__':
    unittest.main()
