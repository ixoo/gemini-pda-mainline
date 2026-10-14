#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP2 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-2.json'
GLOBALS['MANIFEST_SHA'] = 'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d'
GLOBALS['CAPTURE'] = 'capture-ccmp2'
GLOBALS['SESSION'] = 'session-ccmp2'

if __name__ == '__main__':
    BASE['main']()
