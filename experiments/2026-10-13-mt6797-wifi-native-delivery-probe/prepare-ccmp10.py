#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP10 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-10.json'
GLOBALS['MANIFEST_SHA'] = '807c8fb9f886ce0209688740f67193626a86311b76e02d198a66b7d749b2b11c'
GLOBALS['CAPTURE'] = 'capture-ccmp10'
GLOBALS['SESSION'] = 'session-ccmp10'

if __name__ == '__main__':
    BASE['main']()
