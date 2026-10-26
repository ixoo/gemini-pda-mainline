#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Receive reorder window (0321): the actual window, its mac.c glue and the PN check; host behaviour only."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('child', type=Path, help='source tree with 0321')
a = p.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
here = Path(__file__).resolve().parent
driver = a.child.resolve() / rel
text = (driver / 'mac.c').read_text()
start = text.index('#ifdef CONFIG_MT6797_RX_AMPDU\n/* Drain a window')
end = text.index('\n#ifdef CONFIG_MT6797_CCMP_INITIAL_GTK\n/* Observe only', start)
baseline = (here / 'ccmp-rx-test.c').read_text().replace('int main(void)', 'static int ptk_baseline_tests(void)', 1)
baseline = baseline.replace('#include "../../2026-10-07', '#include "%s/../../2026-10-07' % here, 1)
flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
if sys.platform.startswith('linux'):
    flags += ['-fno-pie', '-no-pie']
with tempfile.TemporaryDirectory(prefix='rx-reorder-') as directory:
    tmp = Path(directory)
    (tmp / 'ptk-baseline.inc').write_text(baseline)
    (tmp / 'rx-reorder-glue.inc').write_text(text[start:end] + '\n')
    binary = tmp / 'rx-reorder'
    subprocess.run([*flags, '-I', str(tmp), '-I', str(here), '-I', str(driver),
                    str(here / 'rx-reorder-test.c'), '-o', str(binary)], check=True, timeout=60)
    subprocess.run([str(binary)], check=True, timeout=30)
print('PASS receive reorder window on the actual window, glue and PN check; no worker, firmware or air proof')
