#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native Phase-A capture binding: the reviewed phase-b capture-private.py with the
native identity (the ND2 candidate receipt and release, the native-delivery/capture-nd2
evidence root) and the baseline collector remapped to the private checkout. All capture
logic, the one-attempt claim and the gates live in the reviewed base; only the identity
is re-pointed. No device action beyond the public capture itself.

Environment: GEMINI_PRIVATE_REPO, GEMINI_RUNTIME_ROOT, GEMINI_JOIN_SCRIPT (as the base
requires). Root runs this once on the verified ND1 boot to produce
native-delivery/capture-nd2/phase-a-result.json before the native session.
"""
import importlib.util
import os
from pathlib import Path

os.environ['GEMINI_PHASE_B_SESSION'] = '33'  # satisfies the base _SID check; identity re-pointed below
HERE = Path(__file__).resolve().parent
PHASE_B = HERE.parent / '2026-10-07-mt6797-wifi-phase-b-join'
REPO = PHASE_B.parents[1]
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
SPEC = importlib.util.spec_from_file_location('wifi_phase_b_capture', PHASE_B / 'capture-private.py')
CAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAP)

NATIVE_RELEASE = '7.1.3-gemini-a53-wifi-native-delivery-diag'
# The native receipt (ND1) the capture verifies the booted kernel against.
NATIVE_MANIFEST_SHA = '9e8e008f2e8028aa26edfa9c6083b5edb09ba28aff75982187759cc8aa6f2898'
assert CAP.RELEASE == '7.1.3-gemini-a53-wifi-phase-b-compile', 'frozen capture release changed'
ROOT = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / 'native-delivery'

CAP.ROOT = CAP.WMT.ROOT = CAP.WMT.CAPTURE.ROOT = ROOT
CAP.RELEASE = CAP.WMT.RELEASE = CAP.WMT.CAPTURE.RELEASE = NATIVE_RELEASE
CAP.MANIFEST_SHA = CAP.WMT.CAPTURE.MANIFEST_SHA = NATIVE_MANIFEST_SHA
CAP.EXPERIMENT = 'mt6797-wifi-native-delivery'  # bind the native deployment experiment gate
CAP.WMT.CAPTURE_DIR = CAP.WMT.CAPTURE.CAPTURE = ROOT / 'capture-nd2'
CAP.WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-nd2/deployment-summary.txt'
CAP.WMT.CAPTURE.RECEIPT = HERE / 'results/native-delivery-candidate-2.json'


def remap(path):
    path = Path(path)
    if not path.is_relative_to(REPO):
        raise ValueError('path outside this checkout: ' + str(path))
    return PRIVATE_REPO / path.relative_to(REPO)


CAP.WMT.CAPTURE.BASELINE = remap(CAP.WMT.CAPTURE.BASELINE)

if __name__ == '__main__':
    raise SystemExit(CAP.main())
