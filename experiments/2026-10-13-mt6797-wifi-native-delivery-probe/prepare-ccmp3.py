#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP3 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-3.json'
GLOBALS['MANIFEST_SHA'] = '84722412ea250d86c0772b57e0d0fd39ccfd9335a555c42702037b6d6cae3919'
GLOBALS['CAPTURE'] = 'capture-ccmp3'
GLOBALS['SESSION'] = 'session-ccmp3'

if __name__ == '__main__':
    BASE['main']()
