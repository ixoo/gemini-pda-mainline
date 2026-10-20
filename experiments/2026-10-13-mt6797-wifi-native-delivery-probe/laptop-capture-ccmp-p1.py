#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ROOT-only Phase-A capture with real P1 receipt/release and fresh roots.

Reuse unchanged one-attempt capture and private-source remapping. Environment:
GEMINI_PRIVATE_REPO, GEMINI_RUNTIME_ROOT, GEMINI_JOIN_SCRIPT. Execute only once on
the verified new CCMP boot; source/build success is not live boot identity.
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

NATIVE_RELEASE = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'
NATIVE_MANIFEST_SHA = '71c581f0e4478e71009f2ff3d09b78be6951124a6d6c8ca09bd92cd2e78262ba'
assert CAP.RELEASE == '7.1.3-gemini-a53-wifi-phase-b-compile', 'frozen capture release changed'
ROOT = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / 'ccmp-stable-monitor'

CAP.ROOT = CAP.WMT.ROOT = CAP.WMT.CAPTURE.ROOT = ROOT
CAP.RELEASE = CAP.WMT.RELEASE = CAP.WMT.CAPTURE.RELEASE = NATIVE_RELEASE
CAP.MANIFEST_SHA = CAP.WMT.CAPTURE.MANIFEST_SHA = NATIVE_MANIFEST_SHA
CAP.EXPERIMENT = 'mt6797-wifi-ccmp-stable-monitor'
CAP.WMT.CAPTURE_DIR = CAP.WMT.CAPTURE.CAPTURE = ROOT / 'capture-ccmp-p1'
CAP.WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-ccmp-p1/deployment-summary.txt'
CAP.WMT.CAPTURE.RECEIPT = HERE / 'results/ccmp-stable-monitor-candidate-p1.json'


def remap(path):
    path = Path(path)
    if not path.is_relative_to(REPO):
        raise ValueError('path outside this checkout: ' + str(path))
    return PRIVATE_REPO / path.relative_to(REPO)


CAP.WMT.CAPTURE.BASELINE = remap(CAP.WMT.CAPTURE.BASELINE)

if __name__ == '__main__':
    raise SystemExit(CAP.main())
