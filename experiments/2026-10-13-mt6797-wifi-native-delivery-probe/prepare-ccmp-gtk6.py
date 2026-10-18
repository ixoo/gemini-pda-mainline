#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh GTK6 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-gtk6.json'
GLOBALS['MANIFEST_SHA'] = 'bde064c5a5804353fe9605b4481995abf683ef4a6d6754071b29445795151add'
GLOBALS['CAPTURE'] = 'capture-ccmp-gtk6'
GLOBALS['SESSION'] = 'session-ccmp-gtk6'

if __name__ == '__main__':
    BASE['main']()
