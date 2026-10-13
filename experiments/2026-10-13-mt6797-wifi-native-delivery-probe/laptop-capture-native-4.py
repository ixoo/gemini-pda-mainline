#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ND4 Phase-A capture identity; preserve the frozen one-attempt capture gates."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-capture-native-3.py'))
CAP = BASE['CAP']
ROOT = BASE['ROOT']
NATIVE_MANIFEST_SHA = 'b7ca24a196fb416b25ce6e078770087b96d3ea240dd9928230d1e3156d7dd079'
CAP.MANIFEST_SHA = CAP.WMT.CAPTURE.MANIFEST_SHA = NATIVE_MANIFEST_SHA
CAP.WMT.CAPTURE_DIR = CAP.WMT.CAPTURE.CAPTURE = ROOT / 'capture-nd4'
CAP.WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-nd4/deployment-summary.txt'
CAP.WMT.CAPTURE.RECEIPT = HERE / 'results/native-delivery-candidate-4.json'

if __name__ == '__main__':
    raise SystemExit(CAP.main())
