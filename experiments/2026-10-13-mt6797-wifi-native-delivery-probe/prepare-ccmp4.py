#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP4 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-4.json'
GLOBALS['MANIFEST_SHA'] = '1e8efbeaf49ac08f6fea3d76d3e4949d8473b2d1586c964a67a0b4677449598c'
GLOBALS['CAPTURE'] = 'capture-ccmp4'
GLOBALS['SESSION'] = 'session-ccmp4'

if __name__ == '__main__':
    BASE['main']()
