#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose ND3 from the reviewed deadline-fix package; no device action.

Reuse the frozen ND2 compositor's complete parent, configuration, RAM-root,
container and inventory validation, changing only exact kernel/package pins.
The laptop custodian supplies private C32 parent inputs and returns the real
receipt. ND2 code, candidate and runtime identities remain untouched.
"""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'build-native-candidate-2.py'))
GLOBALS = BASE['main'].__globals__
GLOBALS['__doc__'] = __doc__
GLOBALS['COMMIT'] = '985744adb169ea543d5a8963cf710878c4dc9125'
GLOBALS['PACKAGE'] = 'fd232eaf39f501db4e6c6c81c40953acfce95dadded1dd3f29275c5ef994d4a2'
GLOBALS['NEW_IMAGE_SHA256'] = 'dd56fddd5d5647d0439f79725d8176a63238d82db7d8af76265809111595bcc0'

if __name__ == '__main__':
    BASE['main']()
