#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ND3 Phase-A capture identity; preserve the frozen one-attempt capture gates."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-capture-native-2.py'))
CAP = BASE['CAP']
ROOT = BASE['ROOT']
NATIVE_MANIFEST_SHA = 'f00de1e3bcc40e912ba65f7ebbe3ad15bbc159b230f3e84af3b45dd8cebe7e10'
CAP.MANIFEST_SHA = CAP.WMT.CAPTURE.MANIFEST_SHA = NATIVE_MANIFEST_SHA
CAP.WMT.CAPTURE_DIR = CAP.WMT.CAPTURE.CAPTURE = ROOT / 'capture-nd3'
CAP.WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-nd3/deployment-summary.txt'
CAP.WMT.CAPTURE.RECEIPT = HERE / 'results/native-delivery-candidate-3.json'

if __name__ == '__main__':
    raise SystemExit(CAP.main())
