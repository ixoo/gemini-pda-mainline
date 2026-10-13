#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose ND4 from the reviewed RX/HIF metadata package; no device action.

Reuse the frozen ND3/ND2 composition gates and private C32 parent, changing
only exact validated kernel/package/image pins. The custodian returns the
real receipt before any ND4 runtime or installer binding is published.
"""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'build-native-candidate-2.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['__doc__'] = __doc__
GLOBALS['COMMIT'] = '258c88b1dff36b04e2dc9546c8e14d8d021aa86e'
GLOBALS['PACKAGE'] = '178cf67da473b49e9a665fa503395e27f8538d06e5f5d9b2ddaa88ba0d026f2a'
GLOBALS['NEW_IMAGE_SHA256'] = '4d7120b9b3305fc60d8b931f40ae139482f5af48baad68388d1f49aef2ae853b'

if __name__ == '__main__':
    BASE['main']()
