#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline preparation for the isolated 0184 successor; ND3 device queue first.

Refuses until the laptop compositor's real candidate-34 receipt is published.
Does not invent candidate/deployment hashes or operate the device.
"""
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


def refuse(reason):
    sys.exit('prepare-runtime 35 refused: ' + reason)


GLOBALS['refuse'] = refuse

if __name__ == '__main__':
    BASE['main']()
