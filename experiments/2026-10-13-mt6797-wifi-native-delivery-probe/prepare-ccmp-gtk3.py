#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh GTK3 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-gtk3.json'
GLOBALS['MANIFEST_SHA'] = 'b86f3a5bd362768dd292c11b19f70a9a4cec762fcc21fd62deb237ec1e8b7472'
GLOBALS['CAPTURE'] = 'capture-ccmp-gtk3'
GLOBALS['SESSION'] = 'session-ccmp-gtk3'

if __name__ == '__main__':
    BASE['main']()
