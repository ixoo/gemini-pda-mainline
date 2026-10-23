#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline actual-client regression: observed D2 schedule, drift and no retry."""
from pathlib import Path
import runpy
import unittest

HERE = Path(__file__).resolve().parent
W = runpy.run_path(str(HERE.parent / 'disconnect-window.py'))
# Reuse the actual P2E custody fixture; no device or network calls.
f = (HERE / 'p2e-client-test.py').read_text().split('class EvidenceTests')[0]
state = {'__file__': str(HERE / 'p2e-client-test.py'), '__name__': 'window_fixture'}
exec(compile(f, str(HERE / 'p2e-client-test.py'), 'exec'), state)
S = state['S']
exec(compile(W['client'](), '<offline window client>', 'exec'), S.__dict__)


class WindowTests(unittest.TestCase):
    def test_d2_schedule_and_one_second_drift(self):
        end = 604_498_752_845
        lower, upper = W['disconnect_window'](end, 606_178_752_845)
        self.assertEqual((lower, upper), (end, end + 30_000_000_000))
        self.assertLess(608_548_752_845, upper)
        # Latest eligible precheck retains the entire bounded call plus drift.
        for drift in (1, 549_000_000, 1_000_000_000):
            precheck = upper - W['CONTROL_NS']
            self.assertLessEqual(precheck + drift, upper)
        for margin in (1, 549_000_000, 1_000_000_000, 16_000_000_000):
            with self.assertRaises(ValueError):
                W['disconnect_window'](end, end, margin_ns=margin)
        with self.assertRaises(ValueError):
            W['disconnect_window'](end, upper - W['CONTROL_NS'] + 1)

    def test_actual_client_accepts_dynamic_bounds_once(self):
        result, wifi, controls, _ = state['ConnectedClientTests']().exercise()
        self.assertTrue(result['p2_stream']['pass'])
        control = result['p2_core_disconnect']
        self.assertTrue(control['accepted'])
        self.assertEqual((wifi, controls), (1, 1))
        self.assertEqual(control['precheck_interval_ns'][0],
                         result['p2_stream']['pm_offsets_ns'][-1])
        self.assertEqual(control['request_interval_ns'][1] - control['request_interval_ns'][0],
                         W['MARGIN_NS'])
        self.assertEqual(control['request_interval_ns'][1] - control['precheck_interval_ns'][1],
                         W['CONTROL_NS'])

    def test_refusal_and_timeout_never_retry(self):
        for kwargs in ({'control_rc': 49}, {'control_timeout': True}):
            result, wifi, controls, _ = state['ConnectedClientTests']().exercise(**kwargs)
            self.assertFalse(result['p2_core_disconnect']['accepted'])
            self.assertEqual((wifi, controls), (1, 1))

    def test_remote_script_freezes_observed_bounds(self):
        lower, upper = W['disconnect_window'](604_498_752_845, 606_178_752_845)
        script = S.disconnect_argument(state['F'].BOOT, 1, bounds=(lower, upper))
        self.assertIn(f'[ "$o" -ge {lower} ] && [ "$o" -le {upper} ]', script)
        self.assertNotIn('608000000000', script)
        self.assertEqual(script.count('/bin/wpa_cli'), 2)  # identity + one call
        self.assertNotIn('sleep', script)


if __name__ == '__main__':
    unittest.main()
