#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Source-bounded 60-second delta; no firmware timing or channel proof."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('parent', type=Path)
p.add_argument('child', type=Path)
a = p.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
parent, child = a.parent.resolve() / rel, a.child.resolve() / rel
fixtures = Path(__file__).resolve().parent
allowed = {'mac.c', 'native-diag.h', 'join-commands.h'}
assert {x.name for x in parent.iterdir()} == {x.name for x in child.iterdir()}
for path in parent.iterdir():
    if path.is_file() and path.name not in allowed:
        assert path.read_bytes() == (child / path.name).read_bytes(), path.name


def hooks(root):
    mac = (root / 'mac.c').read_text()
    start = mac.index('static int mt6797_mac_join_release_channel(')
    end = mac.index('\n}\n', start) + 3
    request = mac.index('\tmac->join_requested_ms = 9000;')
    if '#ifdef CONFIG_MT6797_CCMP_FIXED_RX_FORMAT\n\tmac->join_requested_ms = 65000;' in mac:
        begin = mac.rindex('#ifdef CONFIG_MT6797_CCMP_FIXED_RX_FORMAT', 0, request)
        assignment = mac[begin:mac.index('#endif', request) + len('#endif')]
    else:
        assignment = '\tmac->join_requested_ms = 9000;'
    request_hook = assignment.replace('mac->join_requested_ms = ', 'return ')
    return ('\n'.join(line for line in mac.splitlines() if line.startswith('#define MT6797_JOIN_')) +
            '\n' + mac[start:end] + '\nstatic unsigned int requested_interval(void) {\n' +
            request_hook + '\n}\n')


with tempfile.TemporaryDirectory(prefix='fixed-window-') as directory:
    tmp = Path(directory)
    reverse = tmp / 'reverse'
    shutil.copytree(child, reverse / rel)
    patch = fixtures.parents[2] / 'patches/proposals/0203-wifi-mt6797-bound-first-fixed-format-window-to-60s.patch'
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=reverse, check=True)
    for path in parent.iterdir():
        if path.is_file():
            assert path.read_bytes() == (reverse / rel / path.name).read_bytes(), path.name
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    (tmp / 'window-functions.inc').write_text(hooks(child))
    binary = tmp / 'window'
    subprocess.run(['cc', *flags, '-DCONFIG_MT6797_CCMP_FIXED_RX_FORMAT', '-DCONFIG_MT6797_CCMP_STABLE_EPOCH',
                    '-I', str(child), '-I', str(tmp), str(fixtures / 'fixed-window-test.c'),
                    '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=30)
    off = []
    for root in (parent, child):
        (tmp / 'window-functions.inc').write_text(hooks(root))
        result = subprocess.run(['cc', '-E', '-P', '-I', str(root), '-I', str(tmp),
                                 str(fixtures / 'fixed-window-test.c')],
                                check=True, capture_output=True)
        off.append(result.stdout)
    assert off[0] == off[1], 'option-off encoder/budget/opening/request changed'
print('PASS actual-source window boundaries and option-off parity; firmware grant remains unproved')
