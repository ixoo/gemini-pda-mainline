#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP5 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-5.json'
GLOBALS['MANIFEST_SHA'] = '1b1d668c15754b75e36fac6d24d4a31a3bc21eda042ead307a198c560e58597d'
GLOBALS['CAPTURE'] = 'capture-ccmp5'
GLOBALS['SESSION'] = 'session-ccmp5'

if __name__ == '__main__':
    BASE['main']()
