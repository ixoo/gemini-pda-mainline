#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP8 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-8.json'
GLOBALS['MANIFEST_SHA'] = '2f67ae1087fc3b967af527718f7edbc1cdd83e76e111679f3e4ea5a5fcaea98c'
GLOBALS['CAPTURE'] = 'capture-ccmp8'
GLOBALS['SESSION'] = 'session-ccmp8'

if __name__ == '__main__':
    BASE['main']()
