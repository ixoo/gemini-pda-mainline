#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh CCMP6 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-6.json'
GLOBALS['MANIFEST_SHA'] = 'd12ea43d7ddc4e0f9b836bcc7d9db081a06dc640a091b087cdaba8c5fd4865c2'
GLOBALS['CAPTURE'] = 'capture-ccmp6'
GLOBALS['SESSION'] = 'session-ccmp6'

if __name__ == '__main__':
    BASE['main']()
