#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose ND5 from the reviewed native-beacon package; no device action.

Reuse frozen ND4/ND2 composition gates and the private C32 parent, changing
only validated kernel/package/image pins. The custodian returns the real
receipt before fresh ND5 runtime or installer bindings are published.
"""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'build-native-candidate-2.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['__doc__'] = __doc__
GLOBALS['COMMIT'] = 'eaafab2fa0d6f886768c7d0aa6f5c586d1f163cf'
GLOBALS['PACKAGE'] = '3f6754e02895ea3b12094d8520c79e8eac743180e454a89d64a3ef483a39d919'
GLOBALS['NEW_IMAGE_SHA256'] = '759f12a22a9a6ea7927437eeff05cddc256f03dea46df3c7773e6fe4d137550e'

if __name__ == '__main__':
    BASE['main']()
