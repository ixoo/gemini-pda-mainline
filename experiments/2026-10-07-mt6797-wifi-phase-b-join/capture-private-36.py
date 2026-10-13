#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Real C35/R36 capture identity; unchanged one-attempt/source/private gates."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'capture-private-35.py'))
GLOBALS = BASE['GLOBALS']
WMT, ROOT = BASE['WMT'], BASE['ROOT']
MANIFEST_SHA = 'dcb3db4be44f8fbd6df9ea231de62ec8e6a6c9709dd8e12cb26a6c3c903638a2'
GLOBALS['_CANDIDATE'] = 'candidate-35'
GLOBALS['MANIFEST_SHA'] = WMT.CAPTURE.MANIFEST_SHA = MANIFEST_SHA
WMT.CAPTURE_DIR = WMT.CAPTURE.CAPTURE = ROOT / 'capture-36'
WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-36/deployment-summary.txt'
WMT.CAPTURE.RECEIPT = HERE / 'results/candidate-35.json'

if __name__ == '__main__':
    raise SystemExit(GLOBALS['main']())
