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
    # ACK frame, then a task-4 data frame header announcing a 382-byte event.
    b'[   60.2] WMT common init calibration RX: 00000000: 80 00 00 80 80 41 7e 3f',
    DEV + b'WMT common init complete; continuing to WLAN HIF',
    DEV + b'one-shot WLAN private record prepare: status=0',
    DEV + b'one-shot WLAN regulatory configuration: status=0',
    DEV + b'one-shot WLAN TC4 reconciliation: snapshot=2 status=0 released=1 free=2 pending_cpu=0 pending_ffa=0',
]) + b'\n'

r = capture.classify(GOOD)
assert r['ready_for_scan'] and r['common_init_passed']
assert (r['calibration_capture_bytes'], r['calibration_ack_frames'],
        r['calibration_event_task'], r['calibration_reply_bytes']) == (8, 1, 4, 382)

# Failure at step 40: no continuation, no WLAN lines, scan refused.
fail = GOOD.replace(b'result=0 completed=285/285 bt-rail=0',
                    b'result=-110 completed=40/285 bt-rail=0')
fail = b'\n'.join(l for l in fail.split(b'\n') if b'continuing' not in l and b'WLAN' not in l)
r = capture.classify(fail)
assert not r['ready_for_scan'] and r['common_init_result'] == -110 and r['common_init_completed'] == 40

# A dump split over several lines is joined; offsets must be contiguous.
split = GOOD.replace(
    b'00000000: 80 00 00 80 80 41 7e 3f',
    b'00000000: 80 00 00 80\n[   60.2] WMT common init calibration RX: 00000004: 80 41 7e 3f')
r = capture.classify(split)
assert (r['calibration_capture_bytes'], r['calibration_reply_bytes']) == (8, 382)
gap = split.replace(b'RX: 00000004:', b'RX: 00000005:')
assert capture.classify(gap)['calibration_reply_bytes'] is None
# The vendor's short form without a leading ACK, and unparseable framing.
r = capture.classify(GOOD.replace(b'80 00 00 80 80 41 7e 3f', b'80 40 06 c6 02 14 02 00'))
assert (r['calibration_ack_frames'], r['calibration_reply_bytes']) == (0, 6)
r = capture.classify(GOOD.replace(b'80 00 00 80 80 41 7e 3f', b'80 00 00 81 80 41 7e 3f'))
assert r['calibration_reply_bytes'] is None
# Calibration metadata is recorded, never a scan gate.
assert r['ready_for_scan']
assert capture.classify(b'\n'.join(l for l in GOOD.split(b'\n')
                                   if b'calibration RX' not in l))['ready_for_scan']

# Rails left on, a stopped firmware or a BT H1 line refuse the scan.
for bad in (GOOD.replace(b'bt-rail=0 wifi-rail=0', b'bt-rail=1 wifi-rail=0'),
            GOOD + DEV + b'one-shot WLAN firmware stopped (-5); ordinary=1/2 start=-5, state retained\n',
            GOOD + DEV + b'one-shot BT H1: result=0 completed=5/5\n',
            GOOD.replace(b'snapshot=2 status=0', b'snapshot=2 status=-5'),
            GOOD + DEV + b'one-shot WMT common init: result=0 completed=285/285 bt-rail=0 wifi-rail=0 link=3/7/2/6\n'):
    assert not capture.classify(bad)['ready_for_scan']
# Every line present but out of protocol order is refused.
lines = GOOD.rstrip(b'\n').split(b'\n')
for i, j in ((0, 1), (1, 3), (3, 4), (4, 6)):
    swapped = list(lines)
    swapped[i], swapped[j] = swapped[j], swapped[i]
    r = capture.classify(b'\n'.join(swapped) + b'\n')
    assert not r['prerequisites_in_order'] and not r['ready_for_scan'], (i, j)
assert capture.classify(GOOD)['prerequisites_in_order']
print('phase-a classifier: pass, step failure, odd calibration, rails, stop, BT, duplicates, order')
