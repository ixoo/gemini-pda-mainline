#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise retained grant event and data opening together; host behavior only."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('parent', type=Path, help='frozen GTK1 source')
p.add_argument('child', type=Path, help='grant-horizon successor')
a = p.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
parent, child = a.parent.resolve() / rel, a.child.resolve() / rel
fixtures = Path(__file__).resolve().parent
assert {x.name for x in parent.iterdir()} == {x.name for x in child.iterdir()}
for x in parent.iterdir():
    if x.is_file() and x.name != 'mac.c':
        assert x.read_bytes() == (child / x.name).read_bytes(), x.name
old, new = (parent / 'mac.c').read_text(), (child / 'mac.c').read_text()


def function(text, name):
    start = text.index('static int ' + name + '(')
    return text[start:text.index('\n}\n', start) + 2]


def grant(text, name):
    control = function(text, 'mt6797_mac_join_control_event')
    start = control.index('\tstruct mt6797_join_channel expected = {')
    end = control.index('\n\t};', start) + len('\n\t};')
    declaration = control[start:end]
    start = control.index('\tif (mt6797_join_event(mac->join_packet, bytes, 0x10, 16))')
    end = control.index('\n\tif (mt6797_join_event(mac->join_packet, bytes, 0x0c', start)
    return ('static int ' + name + '(struct mt6797_mac *mac, size_t bytes)\n{\n' +
            declaration + '\n\tu32 interval;\n' + control[start:end] + '\n\treturn -EPROTO;\n}\n')


release = function(new, 'mt6797_mac_join_release_channel')
assert release == function(old, 'mt6797_mac_join_release_channel'), 'late guard changed'
with tempfile.TemporaryDirectory(prefix='grant-horizon-') as directory:
    tmp = Path(directory)
    recovered = tmp / 'reverse'
    shutil.copytree(child, recovered / rel)
    patch = fixtures.parents[2] / 'patches/proposals/0205-wifi-mt6797-retain-the-validated-channel-grant-horizon.patch'
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=recovered, check=True)
    for x in parent.iterdir():
        if x.is_file():
            assert x.read_bytes() == (recovered / rel / x.name).read_bytes(), x.name
    definitions = '\n'.join(x for x in new.splitlines() if x.startswith('#define MT6797_JOIN_'))
    (tmp / 'grant-horizon-functions.inc').write_text(
        definitions + '\n' + grant(old, 'parent_grant_event') + '\n' +
        grant(new, 'successor_grant_event') + '\n' + release + '\n')
    flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    binary = tmp / 'grant'
    subprocess.run([*flags, '-DCONFIG_MT6797_CCMP_60S_WINDOW',
        '-DCONFIG_MT6797_CCMP_STABLE_EPOCH', '-I', str(child), '-I', str(tmp),
        str(fixtures / 'grant-horizon-test.c'), '-o', str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
    for options in [[], ['-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG',
                       '-DCONFIG_MT6797_CCMP_STABLE_EPOCH', '-DCONFIG_MT6797_CCMP_MASK_CONTROL']]:
        outputs = []
        for label, text in [('parent', old), ('off', new)]:
            path = tmp / (label + '.c')
            path.write_text(re.sub(r'^#include[^\n]*\n', '', text, flags=re.M))
            outputs.append(subprocess.run(['cc', '-E', '-P', '-DIS_ENABLED(x)=1', *options, str(path)],
                                          check=True, capture_output=True).stdout)
        assert outputs[0] == outputs[1], 'option-off full MAC changed'
print('PASS actual grant-event/data-opening integration and option-off MAC parity; no firmware ownership proof')
