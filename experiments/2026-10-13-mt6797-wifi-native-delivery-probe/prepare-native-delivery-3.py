#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare fresh ND3 evidence roots offline from the real committed receipt."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-native-delivery-2.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/native-delivery-candidate-3.json'
GLOBALS['CAPTURE'] = 'capture-nd3'
GLOBALS['SESSION'] = 'session-nd3'
MANIFEST_SHA = 'f00de1e3bcc40e912ba65f7ebbe3ad15bbc159b230f3e84af3b45dd8cebe7e10'

if __name__ == '__main__':
    if hashlib.sha256(GLOBALS['RECEIPT'].read_bytes()).hexdigest() != MANIFEST_SHA:
        GLOBALS['refuse']('ND3 receipt changed')
    BASE['main']()
