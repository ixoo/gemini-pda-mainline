#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh GTK5 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-gtk5.json'
GLOBALS['MANIFEST_SHA'] = '615b96f6a0ff95509463485c913e42c05395fba97881067dfe370fcffc9dafb7'
GLOBALS['CAPTURE'] = 'capture-ccmp-gtk5'
GLOBALS['SESSION'] = 'session-ccmp-gtk5'

if __name__ == '__main__':
    BASE['main']()
