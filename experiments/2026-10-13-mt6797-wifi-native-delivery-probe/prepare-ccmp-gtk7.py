#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh GTK7 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-gtk7.json'
GLOBALS['MANIFEST_SHA'] = 'e7e4821e7d1f68529806d0dae872d2f1eba07a3690fd4eabb9c6b9ac5f5d68c7'
GLOBALS['CAPTURE'] = 'capture-ccmp-gtk7'
GLOBALS['SESSION'] = 'session-ccmp-gtk7'
GLOBALS['REVIEWED_JOIN_SCRIPT'] = HERE / 'join-ccmp-gtk7.sh'
if hashlib.sha256(GLOBALS['REVIEWED_JOIN_SCRIPT'].read_bytes()).hexdigest() != '55d15ff3499ed23eb41d10853955ce7634836b5040484c714126d31d558bd87f':
    raise ValueError('reviewed GTK7 periodic leaf changed')

if __name__ == '__main__':
    BASE['main']()
