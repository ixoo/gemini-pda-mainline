#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose ND6 from the reviewed reported-index metadata package; no device action.

Reuse frozen ND5/ND2 composition gates and the private C32 parent, changing
only validated kernel/package/image pins. The custodian returns the real
receipt before fresh ND6 runtime or installer bindings are published.
"""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'build-native-candidate-2.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['__doc__'] = __doc__
GLOBALS['COMMIT'] = '6e29f38a0b8ba314f08331906c4d0703579a3343'
GLOBALS['PACKAGE'] = 'ace5aad38afdc9374f2a26964bd68b02c130dd07f9ba84597654d7fc22acab7e'
GLOBALS['NEW_IMAGE_SHA256'] = '7f73a6202a8cb7faf5136d7079e179ee877e3798e3d40a136a70cb33d197dc9b'

if __name__ == '__main__':
    BASE['main']()
