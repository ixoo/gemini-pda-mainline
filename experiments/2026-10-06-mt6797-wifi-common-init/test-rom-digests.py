#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The driver's pinned ROM patch digests must equal the builder's pins.

Usage: test-rom-digests.py PREPARED_LINUX_SOURCE
The first Phase A boot failed because one C byte array was mistyped.
"""

import re
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
pins = runpy.run_path(str(HERE / 'build-candidate.py'))['ROM_PATCHES']
source = (Path(sys.argv[1]) / 'drivers/soc/mediatek/mt6797-consys.c').read_text()
start = source.index('mt6797_rom_patches[2] = {')
block = source[start:source.index('\n};', start)]
found = {name.rsplit('/', 1)[1]: bytes(int(x, 16) for x in re.findall(r'0x([0-9a-f]{2})', body))
         for name, body in re.findall(r'\{ "([^"]+)", \{([^}]*)\} \}', block)}
assert set(found) == set(pins), found.keys()
bad = [name for name, (digest, _) in pins.items() if found[name].hex() != digest]
for name in bad:
    print(name, 'driver', found[name].hex(), 'pinned', pins[name][0])
assert not bad, bad
print('rom patch digests: driver arrays match the pinned SHA-256 for both patches')
