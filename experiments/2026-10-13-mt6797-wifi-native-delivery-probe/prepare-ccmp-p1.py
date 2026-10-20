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
GLOBALS['MANIFEST_SHA'] = '71c581f0e4478e71009f2ff3d09b78be6951124a6d6c8ca09bd92cd2e78262ba'
GLOBALS['CAPTURE'] = 'capture-ccmp-p1'
GLOBALS['SESSION'] = 'session-ccmp-p1'
GLOBALS['REVIEWED_JOIN_SCRIPT'] = HERE / 'join-ccmp-p1.sh'
if hashlib.sha256(GLOBALS['REVIEWED_JOIN_SCRIPT'].read_bytes()).hexdigest() != '3188a0ddf8ead1c58affebff941a2659d21b26f343bb6fb732a037fe1828dd6e':
    raise ValueError('reviewed P1 periodic leaf changed')

if __name__ == '__main__':
    BASE['main']()
