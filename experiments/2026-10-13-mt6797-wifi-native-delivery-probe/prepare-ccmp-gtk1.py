#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh GTK1 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-gtk1.json'
GLOBALS['MANIFEST_SHA'] = 'ef1cf412c6bfe1b2d43fd98069c9cd2f29d059d6533e9cceef0e45aaebe66385'
GLOBALS['CAPTURE'] = 'capture-ccmp-gtk1'
GLOBALS['SESSION'] = 'session-ccmp-gtk1'

if __name__ == '__main__':
    BASE['main']()
