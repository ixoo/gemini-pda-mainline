#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh I50 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-i50.json'
GLOBALS['MANIFEST_SHA'] = '544ba48aa0b2a773d8400ce1db68bf190ff90fc6529fcb4254daef4de232fb87'
GLOBALS['CAPTURE'] = 'capture-ccmp-i50'
GLOBALS['SESSION'] = 'session-ccmp-i50'
GLOBALS['REVIEWED_JOIN_SCRIPT'] = HERE / 'join-ccmp-i50.sh'
if hashlib.sha256(GLOBALS['REVIEWED_JOIN_SCRIPT'].read_bytes()).hexdigest() != '48e782530ba35c1a8344c622093c50605c1d252086416e5cce4a227a3cd04bc6':
    raise ValueError('reviewed I50 periodic leaf changed')

if __name__ == '__main__':
    BASE['main']()
