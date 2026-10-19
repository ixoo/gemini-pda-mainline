#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""S1 fresh namespaces, unchanged GTK8 kernel receipt and exact periodic leaf."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp-gtk8.py'))
GLOBALS = BASE['GLOBALS']
GLOBALS['CAPTURE'] = 'capture-ccmp-gtk8-s1'
GLOBALS['SESSION'] = 'session-ccmp-gtk8-s1'

if __name__ == '__main__':
    BASE['BASE']['main']()
