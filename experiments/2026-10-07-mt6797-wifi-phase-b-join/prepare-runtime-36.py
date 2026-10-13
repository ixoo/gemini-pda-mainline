#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare fresh R36 roots from the exact real C35 receipt; no device action."""
import hashlib
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
MANIFEST_SHA = 'dcb3db4be44f8fbd6df9ea231de62ec8e6a6c9709dd8e12cb26a6c3c903638a2'


def refuse(reason):
    sys.exit('prepare-runtime 36 refused: ' + reason)


GLOBALS['refuse'] = refuse

def main():
    receipt = GLOBALS['RECEIPT']
    if not receipt.is_file() or receipt.is_symlink():
        refuse('real C35 receipt absent or unsafe')
    if hashlib.sha256(receipt.read_bytes()).hexdigest() != MANIFEST_SHA:
        refuse('real C35 receipt changed')
    BASE['main']()


if __name__ == '__main__':
    main()
