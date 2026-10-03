#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test evidence accounting independently of chip reply semantics."""
from pathlib import Path
import runpy
import unittest

API = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'classify-capture.py'))
COMMAND = bytes.fromhex('8040140001081000020100010800008000000000ffff00000000')


def wire(name, raw):
    return b''.join(b'WMT identity capture ' + name + b': ' +
                    ('%08x: ' % n).encode() + raw[n:n+16].hex(' ').encode() + b'\n'
                    for n in range(0, len(raw), 16))


def log(raw=b'', status=-110, tx=26, services=3):
    return (('one-shot WMT identity capture: result=%d tx=%d rx=%d services=%d terminal=1 clocks-held=1\n' %
             (status, tx, len(raw), services)).encode() + wire(b'TX', COMMAND[:tx]) + wire(b'RX', raw))


class Evidence(unittest.TestCase):
    def test_raw_reply_never_accepts_identity(self):
        for value in range(256):
            result = API['classify'](log(bytes([value])*32))
            self.assertTrue(result['capture_complete'])
            self.assertFalse(result['identity_accepted'])
        self.assertTrue(API['classify'](log())['capture_complete'])

    def test_partial_tx_is_diagnostic_only(self):
        for tx in range(26):
            result = API['classify'](log(tx=tx))
            self.assertTrue(result['evidence_consistent'])
            self.assertFalse(result['capture_complete'])

    def test_refusals(self):
        valid = log(b'abc')
        bad = [valid+valid, valid.replace(b'rx=3', b'rx=4'),
               valid.replace(b'services=3', b'services=65'),
               valid.replace(b'clocks-held=1', b'clocks-held=0'),
               valid.replace(b'RX: 00000000', b'RX: 00000001'),
               valid.replace(b'RX:', b'unknown:'),
               valid.replace(b'80 40 14', b'81 40 14'),
               valid + b'one-shot WLAN start\n',
               valid + b'one-shot WMT negotiation: result=0\n',
               log(b'a'*33), log(status=0), log(services=0)]
        for sample in bad:
            self.assertFalse(API['classify'](sample)['capture_complete'])
        # Admitted CONN setup must not cause the earlier false positive.
        self.assertTrue(API['classify'](valid+b'one-shot CONN setup\n')['capture_complete'])


if __name__ == '__main__':
    unittest.main()
