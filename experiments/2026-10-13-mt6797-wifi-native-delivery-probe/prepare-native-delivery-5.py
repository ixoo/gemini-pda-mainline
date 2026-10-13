#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare fresh ND5 evidence roots offline from the real committed receipt."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-native-delivery-2.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/native-delivery-candidate-5.json'
GLOBALS['CAPTURE'] = 'capture-nd5'
GLOBALS['SESSION'] = 'session-nd5'
MANIFEST_SHA = '25893fa2bf4b67364e0821e635c0105c212f110d37156748d8e5a9338a612ef8'

if __name__ == '__main__':
    if hashlib.sha256(GLOBALS['RECEIPT'].read_bytes()).hexdigest() != MANIFEST_SHA:
        GLOBALS['refuse']('ND5 receipt changed')
    BASE['main']()
