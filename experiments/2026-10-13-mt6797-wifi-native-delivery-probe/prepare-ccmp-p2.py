#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh P2 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-p2.json'
GLOBALS['MANIFEST_SHA'] = 'bf73a14d7cfe6f2ddd528025da6c0c2cb01a24e69e9669146ecc39a75ecb4073'
GLOBALS['CAPTURE'] = 'capture-ccmp-p2'
GLOBALS['SESSION'] = 'session-ccmp-p2'
GLOBALS['REVIEWED_JOIN_SCRIPT'] = HERE / 'join-ccmp-p2.sh'
if hashlib.sha256(GLOBALS['REVIEWED_JOIN_SCRIPT'].read_bytes()).hexdigest() != '8415967974a673d44d4255a2476347b539f76a62e38acb1394183aa1cd21a1fe':
    raise ValueError('reviewed P2 periodic leaf changed')

if __name__ == '__main__':
    BASE['main']()
