#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP7 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-7.json'
GLOBALS['MANIFEST_SHA'] = '734b236535fe1f0f3309795c16892c42bf4a4c8f87bd95a83da778c81d85a40a'
GLOBALS['CAPTURE'] = 'capture-ccmp7'
GLOBALS['SESSION'] = 'session-ccmp7'

if __name__ == '__main__':
    BASE['main']()
