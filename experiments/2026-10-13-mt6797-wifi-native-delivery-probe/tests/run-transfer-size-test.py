#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""DMA receive rounding (0310): the actual transfer-size helper; host behaviour only."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('parent', type=Path, help='source tree before 0310')
p.add_argument('child', type=Path, help='source tree with 0310')
a = p.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
fixtures = Path(__file__).resolve().parent
flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
if sys.platform.startswith('linux'):
    flags += ['-fno-pie', '-no-pie']
for label, tree, child in [('parent', a.parent, False), ('child', a.child, True)]:
    with tempfile.TemporaryDirectory(prefix='transfer-size-') as directory:
        binary = Path(directory) / label
        subprocess.run([*flags, *([] if child else ['-DPARENT']), '-I', str(tree.resolve() / rel),
                        str(fixtures / 'transfer-size-test.c'), '-o', str(binary)], check=True, timeout=60)
        subprocess.run([str(binary)], check=True, timeout=60)
print('PASS DMA receive rounding on the actual transfer-size helper; no bus proof')
