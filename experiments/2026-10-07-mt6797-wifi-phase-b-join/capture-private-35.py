#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Runtime35 capture identity with unchanged Phase-A one-attempt gates."""
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
os.environ['GEMINI_PHASE_B_SESSION'] = '33'
BASE = runpy.run_path(str(HERE / 'capture-private.py'))
GLOBALS = BASE['main'].__globals__
WMT = GLOBALS['WMT']
ROOT = GLOBALS['ROOT']
MANIFEST_SHA = '8505a4867cdaaa20d2e9bd687f40958f8ec900ceb7467588e51a7e214cf5b3b3'
GLOBALS['_CANDIDATE'] = 'candidate-34'
GLOBALS['MANIFEST_SHA'] = WMT.CAPTURE.MANIFEST_SHA = MANIFEST_SHA
WMT.CAPTURE_DIR = WMT.CAPTURE.CAPTURE = ROOT / 'capture-35'
WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-35/deployment-summary.txt'
WMT.CAPTURE.RECEIPT = HERE / 'results/candidate-34.json'
REPO = HERE.parents[1]
if WMT.CAPTURE.BASELINE.is_relative_to(REPO):
    WMT.CAPTURE.BASELINE = GLOBALS['PRIVATE_REPO'] / WMT.CAPTURE.BASELINE.relative_to(REPO)

if __name__ == '__main__':
    raise SystemExit(BASE['main']())
