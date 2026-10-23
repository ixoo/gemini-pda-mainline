#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile dormant actual-source helpers; prove no admission consumer was added."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('tree', type=Path)
p.add_argument('parent_mac', type=Path)
a = p.parse_args()
driver = a.tree.resolve() / 'drivers/net/wireless/mediatek/mt6797'
mac = (driver / 'mac.c').read_text()
parent = a.parent_mac.read_text()
assert mac.replace('#include "lifetime-fence.h"\n', '').replace('#include "pn-epoch.h"\n', '') == parent
config = (driver / 'Kconfig').read_text().split('config MT6797_CCMP_LIFETIME_PREREQUISITES\n')[1]
assert '\tdefault n\n' in config
for name in ('lifetime-fence.h', 'pn-epoch.h'):
    assert '#ifdef CONFIG_MT6797_CCMP_LIFETIME_PREREQUISITES' in (driver / name).read_text()
with tempfile.TemporaryDirectory(prefix='dormant-lifetime-') as d:
    binary = Path(d) / 'test'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-DCONFIG_MT6797_CCMP_LIFETIME_PREREQUISITES', '-I', str(driver),
                    str(Path(__file__).with_suffix('.c')), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    off = subprocess.check_output(['cc', '-E', '-P', '-x', 'c', '-I', str(driver), '-'],
                                  input=b'#include "lifetime-fence.h"\n#include "pn-epoch.h"\n')
    assert not off.strip(), off
print('default-off preprocessing empty; MAC identical except unconsumed includes; admission unchanged PASS')
