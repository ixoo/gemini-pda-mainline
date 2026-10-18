#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh GTK4 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-gtk4.json'
GLOBALS['MANIFEST_SHA'] = 'bd6d0dc4c0c17b89dc92d750bd3d9c7ecb802f0067e0e476b3859bf557535bd4'
GLOBALS['CAPTURE'] = 'capture-ccmp-gtk4'
GLOBALS['SESSION'] = 'session-ccmp-gtk4'

if __name__ == '__main__':
    BASE['main']()
