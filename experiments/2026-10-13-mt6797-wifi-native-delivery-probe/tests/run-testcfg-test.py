#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Per-join test schedule (CONFIG_MT6797_WIFI_TESTCONFIG) and the data rate mapping: the actual testcfg-parse.h and tx-rate.h; host behaviour only."""
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
pie = ['-fno-pie', '-no-pie'] if sys.platform.startswith('linux') else []
with tempfile.TemporaryDirectory(prefix='mt6797-testcfg-') as directory:
    binary = Path(directory) / 'testcfg'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    *pie, '-I', str(driver), str(here / 'testcfg-parse-test.c'), '-o', str(binary)],
                   check=True, timeout=120)
    subprocess.run([str(binary)], check=True, timeout=10)
    binary = Path(directory) / 'tx-rate'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    *pie, '-I', str(driver), str(here / 'tx-rate-test.c'), '-o', str(binary)],
                   check=True, timeout=120)
    subprocess.run([str(binary)], check=True, timeout=10)
    # testcfg.c over stubs of the kernel calls it makes; empty kernel headers.
    stub = Path(directory) / 'include'
    (stub / 'linux').mkdir(parents=True)
    for h in ('debugfs', 'err', 'fs', 'kernel', 'mutex', 'slab', 'string', 'uaccess', 'types'):
        (stub / 'linux' / (h + '.h')).write_text('')
    binary = Path(directory) / 'testcfg-state'
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-fsanitize=address,undefined', *pie, '-I', str(stub), '-I', str(driver),
                    str(here / 'testcfg-state-test.c'), '-o', str(binary)], check=True, timeout=120)
    subprocess.run([str(binary)], check=True, timeout=10)
print('PASS the per-join schedule parser, testcfg.c through its file operations and the data rate mapping; the join, the rate control and the air are not proved here')
