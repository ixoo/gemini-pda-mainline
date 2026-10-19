#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh P1 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-p1.json'
GLOBALS['MANIFEST_SHA'] = 'd4cb557f4022547bf49d2f4961c9d12a3142332ebb0d19444c2edcfac833b89d'
GLOBALS['CAPTURE'] = 'capture-ccmp-p1'
GLOBALS['SESSION'] = 'session-ccmp-p1'
GLOBALS['REVIEWED_JOIN_SCRIPT'] = HERE / 'join-ccmp-p1.sh'
if hashlib.sha256(GLOBALS['REVIEWED_JOIN_SCRIPT'].read_bytes()).hexdigest() != 'de6fe61312562e1c1dc429de92df48580c5ebeec6f307bf1488fccda64289a98':
    raise ValueError('reviewed P1 periodic leaf changed')

if __name__ == '__main__':
    BASE['main']()
