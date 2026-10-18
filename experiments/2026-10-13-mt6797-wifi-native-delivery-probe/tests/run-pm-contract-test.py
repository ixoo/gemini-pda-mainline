#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Focused actual-source PM metadata/encoder/ledger fixture, no hardware."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('kernel_tree', type=Path)
p.add_argument('--deauth-retire', action='store_true')
p.add_argument('--gtk7', action='store_true')
a = p.parse_args()
a.deauth_retire = a.deauth_retire or a.gtk7
driver = a.kernel_tree.resolve() / 'drivers/net/wireless/mediatek/mt6797'
with tempfile.TemporaryDirectory(prefix='pm-contract-') as d:
    binary = Path(d) / 'test'
    flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if a.deauth_retire:
        flags += ['-DTEST_DEAUTH_RETIRE']
    if a.gtk7:
        flags += ['-DTEST_GTK7']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    subprocess.run([*flags, '-DCONFIG_MT6797_CCMP_INITIAL_GTK', '-I', str(driver),
                    str(Path(__file__).with_name('pm-contract-test.c')), '-o', str(binary)],
                   check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)

    compat = Path(__file__).resolve().parents[2] / '2026-10-01-mt6797-normal-sets/tests'
    subprocess.run([*flags, '-DCONFIG_MT6797_CCMP_INITIAL_GTK', '-DIS_ENABLED(x)=0',
                    '-I', str(compat), '-I', str(driver),
                    str(Path(__file__).with_name('pm-hif-test.c')), '-o', str(binary)],
                   check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
