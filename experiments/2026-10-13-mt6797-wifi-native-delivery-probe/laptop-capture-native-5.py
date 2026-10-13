#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ND5 Phase-A capture identity; preserve frozen one-attempt capture gates."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-capture-native-4.py'))
CAP = BASE['CAP']
ROOT = BASE['ROOT']
NATIVE_MANIFEST_SHA = '25893fa2bf4b67364e0821e635c0105c212f110d37156748d8e5a9338a612ef8'
CAP.MANIFEST_SHA = CAP.WMT.CAPTURE.MANIFEST_SHA = NATIVE_MANIFEST_SHA
CAP.WMT.CAPTURE_DIR = CAP.WMT.CAPTURE.CAPTURE = ROOT / 'capture-nd5'
CAP.WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-nd5/deployment-summary.txt'
CAP.WMT.CAPTURE.RECEIPT = HERE / 'results/native-delivery-candidate-5.json'

if __name__ == '__main__':
    raise SystemExit(CAP.main())
