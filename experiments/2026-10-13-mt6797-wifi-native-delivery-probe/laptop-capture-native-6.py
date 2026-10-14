#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ND6 Phase-A capture identity; preserve frozen one-attempt capture gates."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-capture-native-5.py'))
CAP = BASE['CAP']
ROOT = BASE['ROOT']
NATIVE_MANIFEST_SHA = 'a8e76bedb11e5b2c0023731611c11934bb431ef0764cb42df8d76975af8a26ee'
CAP.MANIFEST_SHA = CAP.WMT.CAPTURE.MANIFEST_SHA = NATIVE_MANIFEST_SHA
CAP.WMT.CAPTURE_DIR = CAP.WMT.CAPTURE.CAPTURE = ROOT / 'capture-nd6'
CAP.WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-nd6/deployment-summary.txt'
CAP.WMT.CAPTURE.RECEIPT = HERE / 'results/native-delivery-candidate-6.json'

if __name__ == '__main__':
    raise SystemExit(CAP.main())
