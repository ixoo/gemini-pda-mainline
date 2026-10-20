#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh P2 identity binding to the REAL composed receipt, no device."""
from pathlib import Path
import runpy
import hashlib

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-ccmp.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/ccmp-stable-monitor-candidate-p2.json'
GLOBALS['MANIFEST_SHA'] = 'fa2b5ef7c55aafdb9f1dc5e7c196e344e719bc1ba605ca83c4d12bda9e522287'
GLOBALS['CAPTURE'] = 'capture-ccmp-p2'
GLOBALS['SESSION'] = 'session-ccmp-p2'
GLOBALS['REVIEWED_JOIN_SCRIPT'] = HERE / 'join-ccmp-p2.sh'
if hashlib.sha256(GLOBALS['REVIEWED_JOIN_SCRIPT'].read_bytes()).hexdigest() != 'a9f9ad2bc15da3b5eb7bb75093b1622f6f7cecf847b3043493910edfe4547799':
    raise ValueError('reviewed P2 periodic leaf changed')

if __name__ == '__main__':
    BASE['main']()
