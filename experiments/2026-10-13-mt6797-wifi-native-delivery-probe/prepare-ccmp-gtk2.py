#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh GTK2 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-gtk2.json'
GLOBALS['MANIFEST_SHA'] = 'a557a7b7c5c53ddbff10948e9e79119d656016c65e4cf5ca7f3cea29de08ecac'
GLOBALS['CAPTURE'] = 'capture-ccmp-gtk2'
GLOBALS['SESSION'] = 'session-ccmp-gtk2'

if __name__ == '__main__':
    BASE['main']()
