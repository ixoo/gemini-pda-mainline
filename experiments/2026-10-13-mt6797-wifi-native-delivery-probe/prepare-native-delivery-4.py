#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare fresh ND4 evidence roots offline from the real committed receipt."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-native-delivery-2.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/native-delivery-candidate-4.json'
GLOBALS['CAPTURE'] = 'capture-nd4'
GLOBALS['SESSION'] = 'session-nd4'
MANIFEST_SHA = 'b7ca24a196fb416b25ce6e078770087b96d3ea240dd9928230d1e3156d7dd079'

if __name__ == '__main__':
    if hashlib.sha256(GLOBALS['RECEIPT'].read_bytes()).hexdigest() != MANIFEST_SHA:
        GLOBALS['refuse']('ND4 receipt changed')
    BASE['main']()
