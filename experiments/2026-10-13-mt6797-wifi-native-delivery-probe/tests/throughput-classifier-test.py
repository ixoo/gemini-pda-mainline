#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Cleanup suffix compatibility without changing the retained classifier."""
from pathlib import Path
import os
import runpy
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
PREFIX = b'6,1,100,-;device: one-shot WLAN join cleanup: '
TERMINAL = PREFIX + b'stage=3 credits=returned slots=retired deauth=1'
NATIVE = (b'6,1,90,-;device: one-shot WLAN native-diag: state=1 act=1 total=0 native=0 bytes=0\n'
          b'6,1,95,-;device: one-shot WLAN native-diag: state=3 act=2 total=45705 native=0 bytes=56223004\n')
RETIRE = (b'6,1,96,-;device: one-shot WLAN join data phase end: reason=disconnect elapsed_ms=43303 rx_delivered=1 '
          b'tx_queued=4 tx_done=4 tx_failed=0 tx_credits=8\n'
          b'6,1,97,-;device: one-shot WLAN join data credit retire end: retired=51117 expired=0 pid_faults=0 '
          b'wait_avg_us=4263 wait_max_us=22469 left_pages=0 inflight_max=8 samples=811 reports=811\n')


class ClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Exercise the public adapter independently of ignored private cohorts.
        # The stub represents the retained classifier's unrelated verdicts.
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'experiments'/HERE.name
            source.mkdir(parents=True)
            (source/'classify-ccmp-connected-p2.py').write_text(
                "read_protocol = None\n"
                "def classify(kmsg, receipt, verified_boot, protocol=None):\n"
                "    return {'healthy_cleanup': False, 'counts_ok': True,\n"
                "            'sequence_ok': True, 'gtk_counters_consistent': True,\n"
                "            'fault': bool((protocol or {}).get('fault'))}\n")
            with patch.dict(os.environ, TP_SOURCE_ROOT=directory):
                cls.module = runpy.run_path(str(HERE/'classify-throughput.py'))

    def test_legacy_and_current_cleanup_grammars(self):
        cleanup = self.module['cleanup_record']
        self.assertEqual(cleanup(TERMINAL), (True, None))
        for delivery in ('transmitted', 'flushed', 'missing', 'unclassified'):
            self.assertEqual(cleanup(TERMINAL+b' delivery='+delivery.encode()),
                             (True, delivery))

    def test_malformed_or_ambiguous_cleanup_refuses(self):
        cleanup = self.module['cleanup_record']
        for raw in (b'', TERMINAL+b' delivery=acked',
                    TERMINAL+b' delivery=transmitted trailing=1',
                    TERMINAL.replace(b'stage=3', b'stage=2'),
                    TERMINAL.replace(b'credits=returned', b'credits=owed'),
                    TERMINAL.replace(b'deauth=1', b'deauth=2'),
                    TERMINAL+b'\n'+TERMINAL,
                    TERMINAL+b'\n'+PREFIX+b'malformed'):
            self.assertEqual(cleanup(raw), (False, None))

    def test_measurement_still_requires_receipt_timing_identity_and_no_fault(self):
        receipt = {'all_pass': True, 'throughput_measurement': {'directions': {
            label: {'completed': True, 'chunks': [{'elapsed_ns': 1_000_000_000}]*5}
            for label in ('TX', 'RX')}}}
        classify = self.module['classify']
        raw = NATIVE+TERMINAL+b' delivery=transmitted'
        value = classify(raw, receipt, True)
        self.assertTrue(value['throughput_baseline_pass'])
        self.assertEqual(value['cleanup_delivery'], 'transmitted')
        self.assertFalse(value['maintained_wifi_support'])
        self.assertFalse(value['ten_minute_ssh_proven'])
        self.assertFalse(classify(raw, receipt, False)['throughput_baseline_pass'])
        self.assertFalse(classify(raw, receipt, True, {'fault': True})['throughput_baseline_pass'])
        self.assertFalse(classify(raw, None, True)['throughput_baseline_pass'])
        receipt['throughput_measurement']['directions']['RX']['chunks'][0] = {'elapsed_ns': 2_000_000_000}
        self.assertFalse(classify(raw, receipt, True)['throughput_baseline_pass'])

    def test_depth_four_out_of_order_owners_and_count_summary(self):
        origin = HERE/'classify-ccmp-connected.py'
        namespace = runpy.run_path(str(origin))
        decode = self.module['depth_decoder'](origin.read_text(), namespace)
        rows = [b'one-shot WLAN PM credit clock: ns=1000000000']
        for ordinal in range(1, 5):
            rows.append(f'one-shot WLAN TX slot allocation: pid={ordinal} ordinal={ordinal} reserved=0 wraps=0'.encode())
        rows.append(b'one-shot WLAN TX slot summary: phase=window allocations=4 completions=0 pending=4 wraps=0 unowned=0')
        for completed, ordinal in enumerate((3, 1, 4, 2), 1):
            rows.extend([
                f'one-shot WLAN TX slot completion: pid={ordinal} ordinal={completed} wraps=0'.encode(),
                f'one-shot WLAN TX completion timing: pid={ordinal} status=0 class=1 observed_ns=2000000000 pm_offset_ns=1000000000'.encode()])
        rows.extend([
            b'one-shot WLAN join data phase end: reason=disconnect elapsed_ms=1000 rx_unicast=0 rx_group=0 rx_dropped=0 tx_queued=4 tx_done=4 tx_failed=0 tx_credits=8',
            b'one-shot WLAN TX slot allocation: pid=127 ordinal=0 reserved=1 wraps=0',
            b'one-shot WLAN TX completion timing: pid=127 status=0 class=2 observed_ns=2000000000 pm_offset_ns=1000000000',
            b'one-shot WLAN TX slot summary: phase=cleanup allocations=4 completions=4 pending=0 wraps=0 unowned=0'])
        raw = b'\n'.join(rows)
        trace = decode(raw)
        self.assertTrue(trace['trace_valid'], trace['errors'])
        self.assertTrue(trace['whole_after_cleanup'])
        self.assertEqual([t['ordinal'] for t in trace['tx_completions'][:4]], [3, 1, 4, 2])
        self.assertFalse(namespace['pid_trace'](raw)['trace_valid'])
        for broken in (
            raw.replace(b'pending=4', b'pending=1'),
            raw.replace(b'pid=3 ordinal=1 wraps=0', b'pid=5 ordinal=1 wraps=0'),
            raw.replace(b'pid=3 ordinal=1 wraps=0', b'pid=3 ordinal=2 wraps=0'),
            raw.replace(b'phase=cleanup allocations=4 completions=4', b'phase=cleanup allocations=4 completions=3'),
            raw.replace(rows[6], b''),
            raw.replace(rows[4], rows[4]+b'\none-shot WLAN TX slot allocation: pid=5 ordinal=5 reserved=0 wraps=0'),
        ):
            self.assertFalse(decode(broken)['whole_after_cleanup'])
        with self.assertRaises(ValueError):
            self.module['depth_decoder'](origin.read_text().replace('pending=timing=None', 'pending=None'), namespace)

    def test_depth_four_verdict_requires_whole_trace(self):
        # A missing ownership trace cannot pass the depth-specific verdict.
        receipt = {'all_pass': True, 'throughput_measurement': {'directions': {
            label: {'completed': True, 'chunks': [{'elapsed_ns': 1_000_000_000}]*5}
            for label in ('TX', 'RX')}}}
        with patch.dict(os.environ, TP_SOURCE_ROOT=str(HERE.parents[1])):
            for valid, whole, expected in ((True, True, True), (True, False, False), (False, True, False)):
                with patch.dict(self.module['classify'].__globals__,
                                depth_decoder=lambda source, namespace: lambda raw: {
                                    'trace_valid': valid, 'whole_after_cleanup': whole}):
                    value = self.module['classify'](NATIVE+TERMINAL, receipt, True, data_depth=4)
                    self.assertEqual(value['throughput_baseline_pass'], expected)
        with self.assertRaises(ValueError):
            self.module['classify'](TERMINAL, None, True, data_depth=2)

    def test_steady_state_credit_retire_verdict(self):
        # Boot K's shape: 3 s chunks inside the device's 6 s bound, credit retire, no PID trace.
        receipt = {'all_pass': True, 'throughput_measurement': {
            'device_bound_seconds': 6, 'directions': {
                label: {'completed': True, 'chunks': [{'elapsed_ns': 3_820_000_000}]*5}
                for label in ('TX', 'RX')}}}
        classify = self.module['classify']
        raw = NATIVE+RETIRE+TERMINAL
        value = classify(raw, receipt, True, data_depth=8)
        self.assertTrue(value['throughput_baseline_pass'], value['verdict_gates'])
        self.assertTrue(value['credit_retire_ownership']['whole'])
        self.assertEqual(value['retained_not_gated'], ['counts_ok', 'gtk_counters_consistent', 'queued_count_ok'])
        for broken in (raw.replace(b'expired=0', b'expired=1'), raw.replace(b'pid_faults=0', b'pid_faults=2'),
                       raw.replace(b'left_pages=0', b'left_pages=13'), raw.replace(b'tx_failed=0', b'tx_failed=1'),
                       raw.replace(b'total=45705 native=0', b'total=45705 native=1'),
                       raw.replace(b'total=45705', b'total=0').replace(b'bytes=56223004', b'bytes=0').replace(b'total=0 native=0 bytes=0\n6', b'total=9 native=0 bytes=9\n6', 1),
                       RETIRE+TERMINAL):
            self.assertFalse(classify(broken, receipt, True, data_depth=8)['throughput_baseline_pass'])
        receipt['throughput_measurement']['directions']['RX']['chunks'][0] = {'elapsed_ns': 6_600_000_000}
        self.assertFalse(classify(raw, receipt, True, data_depth=8)['throughput_baseline_pass'])


if __name__ == '__main__':
    unittest.main()
