#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the actual connected-channel release step; no hardware access."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
p.add_argument('--parent', type=Path, required=True, help='frozen GTK7 source for option-off parity')
a = p.parse_args()
mac = (a.source / 'drivers/net/wireless/mediatek/mt6797/mac.c').read_text()
parent = (a.parent / 'drivers/net/wireless/mediatek/mt6797/mac.c').read_text()
configs = set(re.findall(r'CONFIG_[A-Z0-9_]+', parent))
for enabled in [set(), {'CONFIG_MT6797_CCMP_60S_WINDOW'}, configs]:
    outputs = []
    for source in [parent, mac]:
        source = re.sub(r'^#include[^\n]*', '', source, flags=re.M)
        result = subprocess.run(['cc', '-E', '-P', '-x', 'c', '-', '-DIS_ENABLED(x)=x',
                                 '-UCONFIG_MT6797_CCMP_CHANNEL_RELEASE',
                                 *['-D' + name for name in sorted(enabled)]],
                                input=source, text=True, capture_output=True, check=True, timeout=30)
        outputs.append(re.findall(r'\"(?:\\.|[^\"\\])*\"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]', result.stdout))
    assert outputs[0] == outputs[1], 'option-off preprocessed MAC changed'
print('channel-release option-off preprocessed MAC parity: 3 selections PASS')
start = mac.index('static int mt6797_ccmp_channel_release_step(')
end = mac.index('\n}\n', start) + 3
function = mac[start:end]
# Check the worker invokes the real step after reconciliation and before TX
# selection, while keeping receive processing reachable in a hold iteration.
worker = mac[mac.index('static void mt6797_mac_join_work('):]
assert worker.index('ret = mt6797_mac_join_guard(mac, deadline);') < worker.index(
    'ret = mt6797_ccmp_channel_release_step(mac, ktime_get_ns());') < worker.index(
    'select = !mac->join_inflight && !mac->join_page_debt;')
assert 'if (channel_release_holds_tx)\n\t\tselect = false;' in worker
assert '#ifdef CONFIG_MT6797_CCMP_CHANNEL_RELEASE\n\t/* Only this comparison' in mac
assert 'mac->ccmp_channel_release_at = grant_end;' in mac
assert 'mac->join_data_deadline = budget_end;' in mac
with tempfile.TemporaryDirectory(prefix='channel-release-') as d:
    directory = Path(d)
    (directory / 'actual-channel-release.inc').write_text(function)
    opening = mac.index('static int mt6797_mac_join_release_channel(')
    closing = mac.index('\n}\n', opening) + 3
    (directory / 'actual-open-data.inc').write_text(mac[opening:closing])
    grant_start = mac.index('\tif (mt6797_join_event(mac->join_packet, bytes, 0x10, 16)) {')
    grant_end = mac.index('\tif (mt6797_join_event(mac->join_packet, bytes, 0x0c, 8)) {', grant_start)
    (directory / 'actual-grant.inc').write_text(
        'static int actual_grant(struct mt6797_mac *mac) {\n'
        'unsigned int interval; int expected = 0; size_t bytes = 24;\n' +
        mac[grant_start:grant_end] + '\nreturn -EINVAL;\n}\n')
    binary = directory / 'test'
    flags = ['cc', '-DCONFIG_MT6797_CCMP_CHANNEL_RELEASE', '-DCONFIG_MT6797_CCMP_60S_WINDOW', '-std=c11', '-Wall', '-Wextra', '-Werror',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    subprocess.run([*flags, '-I', d,
                    str(Path(__file__).with_name('channel-release-test.c')),
                    '-o', str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
