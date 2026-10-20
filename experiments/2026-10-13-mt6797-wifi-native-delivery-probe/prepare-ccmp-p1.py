#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh P1 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-p1.json'
GLOBALS['MANIFEST_SHA'] = '1184f7305aad6c33cb727dcc8f4780da03a982c1718daad6875ea95e849e92e5'
GLOBALS['CAPTURE'] = 'capture-ccmp-p1'
GLOBALS['SESSION'] = 'session-ccmp-p1'
GLOBALS['REVIEWED_JOIN_SCRIPT'] = HERE / 'join-ccmp-p1.sh'
if hashlib.sha256(GLOBALS['REVIEWED_JOIN_SCRIPT'].read_bytes()).hexdigest() != 'd7959108e8a51d26c14c23493d199ff9dd35f786e5dd3b0d39c59f131b5722a0':
    raise ValueError('reviewed P1 periodic leaf changed')

if __name__ == '__main__':
    BASE['main']()
