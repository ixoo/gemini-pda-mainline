#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline gap bins, chunk isolation and refusal fixtures."""
from pathlib import Path
import runpy
import unittest

M = runpy.run_path(str(Path(__file__).resolve().parent.parent/'summarize-throughput-completion-gaps.py'))


class GapTests(unittest.TestCase):
    def test_bin_boundaries(self):
        result = M['histogram']([0, 999999, 1000000, 100000000])
        self.assertEqual([row['count'] for row in result['bins']], [2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0])
        self.assertEqual(result['maximum_gap_ns'], 100000000)
        self.assertIsNone(M['histogram']([])['maximum_gap_ns'])

    def test_chunk_gaps_are_excluded(self):
        raw, records, kmsg, directions = b'', [], b'', {}
        for label, offset in (('TX', 0), ('RX', 10_000_000_000)):
            for ordinal in range(1, 6):
                start = offset + ordinal * 1_100_000_000
                end = start + 1_000_000_000
                raw += f'TP2_PROGRESS direction={label} chunk={ordinal} phase=start ns={start}\n'.encode()
                raw += f'TP2_PROGRESS direction={label} chunk={ordinal} phase=end rc=0 bytes=1 ns={end}\n'.encode()
                records.extend({'class': 1, 'status': 0, 'observed_ns': start + delta}
                               for delta in (0, 1_000_000, 900_000_000))
                for delta in (0, 1_000_000, 900_000_000):
                    kmsg += f'6,1,{(start+delta)//1000},-;device: one-shot WLAN join TX done: pid=1 status=0 advanced=1 count=1\n'.encode()
            directions[label] = {'device_start_ns': offset + 1_100_000_000,
                                 'device_end_ns': end}
        result = {'verified_boot': 'fixture', 'ccmp_compatibility': {'pid_ownership': {
            'trace_valid': True, 'whole_after_cleanup': True, 'tx_completions': records,
            'ordinary_completions': len(records)},
            'throughput_measurement': {'directions': directions}}}
        value = M['summarize'](result, raw, kmsg)
        for direction in value['directions'].values():
            self.assertEqual(direction['within_chunks']['gap_count'], 10)
            self.assertEqual(direction['full_window_including_chunk_gaps']['gap_count'], 14)
        with self.assertRaises(ValueError):
            M['chunk_windows'](raw + raw, 'TX')
        with self.assertRaises(ValueError):
            M['chunk_windows'](b'', 'TX')
        with self.assertRaises(ValueError):
            M['summarize'](result, raw, b'\n'.join(reversed(kmsg.splitlines())))
        result['ccmp_compatibility']['pid_ownership']['trace_valid'] = False
        with self.assertRaises(ValueError):
            M['summarize'](result, raw, kmsg)


if __name__ == '__main__':
    unittest.main()
