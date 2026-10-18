#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP11 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-11.json'
GLOBALS['MANIFEST_SHA'] = '00eee0c5473a9f26ec8952096d2d992eab731050c2545301fc35443db8152144'
GLOBALS['CAPTURE'] = 'capture-ccmp11'
GLOBALS['SESSION'] = 'session-ccmp11'

if __name__ == '__main__':
    BASE['main']()
