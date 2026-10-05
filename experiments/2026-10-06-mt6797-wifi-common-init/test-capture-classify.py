#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Phase A log classifier on synthetic logs; no private data."""

import importlib.util
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as private:
    os.environ['GEMINI_PRIVATE_REPO'] = private
    spec = importlib.util.spec_from_file_location('phase_a_capture', HERE / 'capture-private.py')
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)

DEV = b'[   60.1] mt6797-consys 10001340.consys: '
GOOD = b'\n'.join([
    DEV + b'one-shot WMT negotiation: result=0 phase=5 clocks-held=1',
    DEV + b'one-shot WMT common init: result=0 completed=285/285 bt-rail=0 wifi-rail=0 link=3/7/2/6',
    b'[   60.2] WMT common init calibration RX: 00000000: 02 14 02 00 00 01',
    DEV + b'WMT common init complete; continuing to WLAN HIF',
    DEV + b'one-shot WLAN private record prepare: status=0',
    DEV + b'one-shot WLAN regulatory configuration: status=0',
    DEV + b'one-shot WLAN TC4 reconciliation: snapshot=2 status=0 released=1 free=2 pending_cpu=0 pending_ffa=0',
]) + b'\n'

r = capture.classify(GOOD)
assert r['ready_for_scan'] and r['common_init_passed'] and r['calibration_status_vendor_expected']
assert r['calibration_reply_bytes'] == 6

# Failure at step 40: no continuation, no WLAN lines, scan refused.
fail = GOOD.replace(b'result=0 completed=285/285 bt-rail=0',
                    b'result=-110 completed=40/285 bt-rail=0')
fail = b'\n'.join(l for l in fail.split(b'\n') if b'continuing' not in l and b'WLAN' not in l)
r = capture.classify(fail)
assert not r['ready_for_scan'] and r['common_init_result'] == -110 and r['common_init_completed'] == 40

# Unexpected calibration status is recorded, not fatal by itself.
odd = GOOD.replace(b'02 14 02 00 00 01', b'02 14 02 00 00 07')
r = capture.classify(odd)
assert r['ready_for_scan'] and not r['calibration_status_vendor_expected']

# Rails left on, a stopped firmware or a BT H1 line refuse the scan.
for bad in (GOOD.replace(b'bt-rail=0 wifi-rail=0', b'bt-rail=1 wifi-rail=0'),
            GOOD + DEV + b'one-shot WLAN firmware stopped (-5); ordinary=1/2 start=-5, state retained\n',
            GOOD + DEV + b'one-shot BT H1: result=0 completed=5/5\n',
            GOOD.replace(b'snapshot=2 status=0', b'snapshot=2 status=-5'),
            GOOD + DEV + b'one-shot WMT common init: result=0 completed=285/285 bt-rail=0 wifi-rail=0 link=3/7/2/6\n'):
    assert not capture.classify(bad)['ready_for_scan']
print('phase-a classifier: pass, step failure, odd calibration, rails, stop, BT, duplicates')
