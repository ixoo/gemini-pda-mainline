#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the reviewed 0186 terminal-fence successor, without device action.

Reuse the frozen C32 successor composition gates with exact validated inputs.
ND3 and C34/R35 remain immutable evidence; this does not reorder device tests.
"""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'build-successor-candidate.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['__doc__'] = __doc__
GLOBALS['COMMIT'] = '868ef7217d131daa469e8e866c0f442d77a0c1b5'
GLOBALS['PACKAGE'] = 'ce431869bcaaba805eb4b46bbbb455b3627c07d083123b28bed1bf646e88235c'
GLOBALS['NEW_IMAGE_SHA256'] = '9f97039a9874d93545d04a07cee6c1542ef73586aeffc506dc6e25ebb857a853'

if __name__ == '__main__':
    BASE['main']()
