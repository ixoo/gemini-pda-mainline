#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Positive wire paths and targeted refusal mutations for the actual classifier."""
from pathlib import Path
import runpy
import unittest

HERE = Path(__file__).resolve().parents[1]
classify = runpy.run_path(str(HERE / 'classify-negotiation.py'))['classify']
COMMAND = bytes.fromhex('874005cc01040100046cf3')
EVENT = bytes.fromhex('80400aca020406000004df0e680156f7')
EVENT_OLD_ACK = bytes.fromhex('87400ad1020406000004df0e680156f7')
ACK = bytes.fromhex('80000080')
OLD_ACK = bytes.fromhex('87000087')
WIRE = {'default TX': bytes.fromhex('8040050001040100040000'),
        'default RX': bytes.fromhex('80400a00020406000004110000000000'),
        'set TX': bytes.fromhex('804009000104050003df0e68010000'),
        'set RX': bytes.fromhex('804006000204020000030000'),
        'full TX': COMMAND, 'full ACK TX': ACK, 'full RX': EVENT}


def log(wire=None, frames=1):
    wire = WIRE if wire is None else wire
    lines = [b'one-shot WMT negotiation: result=0 phase=5 clocks-held=1',
             b'WMT negotiation mandatory: default-rx=16 default-irqs=2 set-tx=15 set-rx=12 set-services=3',
             ('WMT negotiation full: tx=15 rx=%d services=4 frames=%d tx-seq=1 rx-seq=1 peer-ack=0 local-ack=0' %
              (len(wire['full RX']), frames)).encode()]
    for name, raw in wire.items():
        for offset in range(0, len(raw), 16):
            lines.append(('WMT negotiation %s: %08x: %s' %
                          (name, offset, raw[offset:offset + 16].hex(' '))).encode())
    return b'\n'.join(lines) + b'\n'


class Classification(unittest.TestCase):
    def test_valid_credit_paths(self):
        for raw, frames in [(EVENT, 1), (ACK + EVENT, 2), (EVENT_OLD_ACK + ACK, 2),
                            (OLD_ACK * 6 + ACK + EVENT, 8)]:
            with self.subTest(raw_length=len(raw)):
                self.assertTrue(classify(log(WIRE | {'full RX': raw}, frames))['matched_response'])

    def test_mandatory_debug_header_is_not_full_sequence(self):
        for name in ['default RX', 'set RX']:
            raw = WIRE[name]
            self.assertTrue(classify(log(WIRE | {name: b'\xff' + raw[1:]}))['matched_response'])

    def test_terminal_and_count_refusals(self):
        good = log()
        for old, new in [(b'result=0', b'result=-110'), (b'phase=5', b'phase=4'),
                         (b'clocks-held=1', b'clocks-held=0'), (b'default-irqs=2', b'default-irqs=32'),
                         (b'set-services=3', b'set-services=33'), (b'services=4', b'services=513'),
                         (b'tx-seq=1', b'tx-seq=2'), (b'local-ack=0', b'local-ack=7'),
                         (b'frames=1', b'frames=2')]:
            with self.subTest(old=old):
                self.assertFalse(classify(good.replace(old, new))['matched_response'])
        self.assertFalse(classify(b'')['matched_response'])
        self.assertFalse(classify(good + good)['matched_response'])

    def test_wire_mutations_and_missing_evidence(self):
        for name, raw in WIRE.items():
            for changed in [b'', raw[:-1], raw[:-1] + bytes([raw[-1] ^ 1])]:
                with self.subTest(name=name, length=len(changed)):
                    self.assertFalse(classify(log(WIRE | {name: changed}))['matched_response'])
        for raw in [EVENT_OLD_ACK, EVENT + ACK, ACK, EVENT[:-1] + b'\x00',
                    EVENT + EVENT, OLD_ACK * 8 + EVENT]:
            self.assertFalse(classify(log(WIRE | {'full RX': raw}))['matched_response'])

    def test_log_corruption_and_continuation(self):
        good = log()
        for changed in [good.replace(b'00000000:', b'00000001:', 1),
                        good.replace(b'80 40 05', b'zz 40 05', 1),
                        good + b'one-shot WLAN started\n',
                        good + b'one-shot WMT negotiation: malformed\n',
                        good + b'WMT negotiation full ACK TX: 00000000: 80 00 00 80\n']:
            self.assertFalse(classify(changed)['matched_response'])

    def test_private_bytes_not_returned(self):
        result = classify(log())
        self.assertTrue(result['matched_response'])
        self.assertNotIn('wire', result)
        self.assertTrue(all(not isinstance(value, (bytes, bytearray)) for value in result.values()))


if __name__ == '__main__':
    unittest.main()
