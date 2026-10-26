#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""HT40 join commands (0323) and the HT station record: the actual hif.c commands; host behaviour only."""
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
kconfig = (driver / 'Kconfig').read_text()
ht40 = 'config MT6797_HT40\n' in kconfig
ht40_tx = 'config MT6797_HT40_TX' in kconfig
sgi_tx = 'config MT6797_HT_SGI_TX' in kconfig
sta_full = 'config MT6797_HT_STA_RECORD_FULL' in kconfig
pie = ['-fno-pie', '-no-pie'] if sys.platform.startswith('linux') else []
with tempfile.TemporaryDirectory(prefix='mt6797-ht40-') as directory:
    runs = [[]] + ([['-DCONFIG_MT6797_HT40']] if ht40 else []) + \
        ([['-DCONFIG_MT6797_HT40', '-DCONFIG_MT6797_HT40_TX']] if ht40_tx else []) + \
        ([['-DCONFIG_MT6797_HT40', '-DCONFIG_MT6797_HT40_TX', '-DCONFIG_MT6797_HT_SGI_TX',
           '-DCONFIG_MT6797_DATA_FIXED_RATE_CODE=0x85'],
          ['-DCONFIG_MT6797_HT40', '-DCONFIG_MT6797_HT40_TX', '-DCONFIG_MT6797_HT_SGI_TX']]
         if sgi_tx else [])
    runs += [['-DCONFIG_MT6797_HT_STA_RECORD_FULL']] if sta_full else []
    for defines in runs:
        binary = Path(directory) / ('test-%d' % runs.index(defines))
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-DIS_ENABLED(x)=0',
                        '-DCONFIG_MT6797_WMM_QOS_DATA', *defines, '-fsanitize=address,undefined',
                        *pie, '-I', str(compat), '-I', str(driver), str(here / 'ht40-hif-test.c'),
                        '-o', str(binary)], check=True, timeout=120)
        subprocess.run([str(binary)], check=True, timeout=10)
print('PASS HT40 join commands on the actual hif.c (%d builds); mac80211 admission and the air are not proved here'
      % len(runs))
