#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline preparation for real C34/R35; ND3 device queue first, no device action."""
import hashlib
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'prepare-runtime-34.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['RECEIPT'] = HERE / 'results/candidate-34.json'
GLOBALS['COMMIT'] = '1edcbfb315f1464e3319aff0be1133b4e948f8e5'
GLOBALS['PACKAGE'] = '074414c5744a6a45023c136ac3537321c5738b118d4a5a4935b4ad81d613d59e'
GLOBALS['CAPTURE'], GLOBALS['SESSION'] = 'capture-35', 'session-35'
MANIFEST_SHA = '8505a4867cdaaa20d2e9bd687f40958f8ec900ceb7467588e51a7e214cf5b3b3'


def refuse(reason):
    sys.exit('prepare-runtime 35 refused: ' + reason)


GLOBALS['refuse'] = refuse

if __name__ == '__main__':
    if hashlib.sha256(GLOBALS['RECEIPT'].read_bytes()).hexdigest() != MANIFEST_SHA:
        refuse('real C34 receipt changed')
    BASE['main']()
