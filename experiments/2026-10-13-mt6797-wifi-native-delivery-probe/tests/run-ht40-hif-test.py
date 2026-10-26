#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""HT40 join commands (0323): the actual hif.c channel and BSS commands; host behaviour only."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('kernel_tree', type=Path)
a = p.parse_args()
driver = a.kernel_tree.resolve() / 'drivers/net/wireless/mediatek/mt6797'
here = Path(__file__).resolve().parent
compat = here.parents[1] / '2026-10-01-mt6797-normal-sets/tests'
ht40 = 'config MT6797_HT40' in (driver / 'Kconfig').read_text()
pie = ['-fno-pie', '-no-pie'] if sys.platform.startswith('linux') else []
with tempfile.TemporaryDirectory(prefix='mt6797-ht40-') as directory:
    for defines in ([], ['-DCONFIG_MT6797_HT40'])[:2 if ht40 else 1]:
        binary = Path(directory) / ('test-ht40' if defines else 'test')
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-DIS_ENABLED(x)=0',
                        '-DCONFIG_MT6797_WMM_QOS_DATA', *defines, '-fsanitize=address,undefined',
                        *pie, '-I', str(compat), '-I', str(driver), str(here / 'ht40-hif-test.c'),
                        '-o', str(binary)], check=True, timeout=120)
        subprocess.run([str(binary)], check=True, timeout=10)
print('PASS HT40 join commands on the actual hif.c%s; mac80211 admission and the air are not proved here'
      % (', with and without the option' if ht40 else ''))
