#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline fresh runtime36 preparation; refuses until real C35 receipt exists.

No fabricated candidate/deployment receipt and no device action. Exact remaining
runtime/installer pins require actual composition and device-queue predecessor.
"""
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-runtime-34.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/candidate-35.json'
GLOBALS['COMMIT'] = '868ef7217d131daa469e8e866c0f442d77a0c1b5'
GLOBALS['PACKAGE'] = 'ce431869bcaaba805eb4b46bbbb455b3627c07d083123b28bed1bf646e88235c'
GLOBALS['CAPTURE'], GLOBALS['SESSION'] = 'capture-36', 'session-36'


def refuse(reason):
    sys.exit('prepare-runtime 36 refused: ' + reason)


GLOBALS['refuse'] = refuse

if __name__ == '__main__':
    BASE['main']()
