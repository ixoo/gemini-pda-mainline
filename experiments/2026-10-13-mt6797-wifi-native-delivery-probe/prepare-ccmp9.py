#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP9 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-9.json'
GLOBALS['MANIFEST_SHA'] = 'a8f83b101371f8fb81f93c94777bf551d95140c5dba408d463f00475397a81c8'
GLOBALS['CAPTURE'] = 'capture-ccmp9'
GLOBALS['SESSION'] = 'session-ccmp9'

if __name__ == '__main__':
    BASE['main']()
