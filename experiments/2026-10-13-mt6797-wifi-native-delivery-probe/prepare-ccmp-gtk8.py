#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh GTK8 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-gtk8.json'
GLOBALS['MANIFEST_SHA'] = 'dd6fff6ee66b68bc0b77daca07e77df29de4f2dbf6189ad272a36b72de6c9273'
GLOBALS['CAPTURE'] = 'capture-ccmp-gtk8'
GLOBALS['SESSION'] = 'session-ccmp-gtk8'
GLOBALS['REVIEWED_JOIN_SCRIPT'] = HERE / 'join-ccmp-gtk7.sh'
if hashlib.sha256(GLOBALS['REVIEWED_JOIN_SCRIPT'].read_bytes()).hexdigest() != '55d15ff3499ed23eb41d10853955ce7634836b5040484c714126d31d558bd87f':
    raise ValueError('reviewed GTK8 periodic leaf changed')

if __name__ == '__main__':
    BASE['main']()
