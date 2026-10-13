#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the reviewed 0184 station-step candidate, independently of ND3.

Reuse frozen successor composition gates: only kernel bytes change from C32;
configuration, board DT and private 64-member RAM root remain byte-identical.
No device action. Device queue remains ND3 first.
"""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'build-successor-candidate.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['__doc__'] = __doc__
GLOBALS['COMMIT'] = '1edcbfb315f1464e3319aff0be1133b4e948f8e5'
GLOBALS['PACKAGE'] = '074414c5744a6a45023c136ac3537321c5738b118d4a5a4935b4ad81d613d59e'
GLOBALS['NEW_IMAGE_SHA256'] = '28b1f4c88a931f015d14f350d2ab51ee631f58f76d33850ba24d33b0d726caa4'

if __name__ == '__main__':
    BASE['main']()
