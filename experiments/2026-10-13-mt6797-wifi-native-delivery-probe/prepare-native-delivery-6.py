#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare fresh ND6 evidence roots offline from the real committed receipt."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-native-delivery-2.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/native-delivery-candidate-6.json'
GLOBALS['CAPTURE'] = 'capture-nd6'
GLOBALS['SESSION'] = 'session-nd6'
MANIFEST_SHA = 'a8e76bedb11e5b2c0023731611c11934bb431ef0764cb42df8d76975af8a26ee'

if __name__ == '__main__':
    if hashlib.sha256(GLOBALS['RECEIPT'].read_bytes()).hexdigest() != MANIFEST_SHA:
        GLOBALS['refuse']('ND6 receipt changed')
    BASE['main']()
