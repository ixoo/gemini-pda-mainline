#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Block-ack sub-frame status (0319): the actual pairwise receive check; host behaviour only."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('parent', type=Path, help='source tree before 0319')
p.add_argument('child', type=Path, help='source tree with 0319')
a = p.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
here = Path(__file__).resolve().parent
baseline = (here / 'ccmp-rx-test.c').read_text().replace('int main(void)', 'static int ptk_baseline_tests(void)', 1)
baseline = baseline.replace('#include "../../2026-10-07', '#include "%s/../../2026-10-07' % here, 1)
flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
if sys.platform.startswith('linux'):
    flags += ['-fno-pie', '-no-pie']
runs = [('parent', a.parent, [], 0), ('child-off', a.child, [], 0),
        ('child-on', a.child, ['-DCONFIG_MT6797_RX_AMPDU'], 1)]
with tempfile.TemporaryDirectory(prefix='ccmp-ba-') as directory:
    tmp = Path(directory)
    (tmp / 'ptk-baseline.inc').write_text(baseline)
    for label, tree, defines, admitted in runs:
        binary = tmp / label
        subprocess.run([*flags, *defines, '-DBA_ADMITTED=%d' % admitted, '-I', str(tmp), '-I', str(here),
                        '-I', str(tree.resolve() / rel), str(here / 'ccmp-ba-status-test.c'), '-o', str(binary)],
                       check=True, timeout=60)
        subprocess.run([str(binary)], check=True, timeout=30)
print('PASS block-ack sub-frame status on the actual pairwise receive check; no firmware or air proof')
