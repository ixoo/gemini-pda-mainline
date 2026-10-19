#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual connected-lifetime fences, native budget and worker poll guard."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
p.add_argument('--parent', type=Path, required=True)
a = p.parse_args()
sub = Path('drivers/net/wireless/mediatek/mt6797')
mac = (a.source / sub / 'mac.c').read_text()
parent = (a.parent / sub / 'mac.c').read_text()
configs = set(re.findall(r'CONFIG_[A-Z0-9_]+', parent))
for file in ['mac.c', 'native-diag.h']:
    for enabled in [set(), {'CONFIG_MT6797_CCMP_60S_WINDOW'}, configs]:
        results = []
        for root in [a.parent, a.source]:
            text = re.sub(r'^#include[^\n]*', '', (root / sub / file).read_text(), flags=re.M)
            out = subprocess.run(['cc', '-E', '-P', '-x', 'c', '-', '-DIS_ENABLED(x)=x',
                                  '-UCONFIG_MT6797_CCMP_CONNECTED_LIFETIME',
                                  *['-D' + name for name in sorted(enabled)]],
                                 input=text, text=True, capture_output=True, check=True, timeout=30)
            results.append(re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]', out.stdout))
        assert results[0] == results[1], (file, 'option-off parity changed')
print('connected-lifetime option-off MAC/native budget parity: six selections PASS')


def function(name):
    start = mac.index(name)
    return mac[start:mac.index('\n}\n', start) + 3]


# Extract executable expressions/blocks, rather than duplicating the decisions.
worker = mac[mac.index('static void mt6797_mac_join_work('):]
start = worker.index('\tif (mac->scan_active || mac->first_error || mac->closing ||')
end = worker.index(') {', start)
guard = 'static bool actual_poll_guard(struct mt6797_mac *mac, u64 now) {\nreturn ' + worker[start + 4:end + 1] + ';\n}\n'
start = mac.index('\tif (prev != MT6797_ND_ACTIVE && mac->native_diag_state == MT6797_ND_ACTIVE) {')
end = mac.index('\n\t}\n', start) + 4
entry = 'static void actual_mode_entry(struct mt6797_mac *mac, u64 now, unsigned char prev) {\n' + mac[start:end] + '\n}\n'
# Pre-data fence, all fault/stop calls and stable-epoch re-arm refusal unchanged.
assert 'mac->join_deadline = ktime_get_ns() + 10 * NSEC_PER_SEC;' in mac
rearm = r'!ccmp_stable_epoch &&\n#endif\n\t    mac->join_lifetimes < 2'
assert re.findall(rearm, parent) and re.findall(rearm, mac) == re.findall(rearm, parent)
for name in ['mt6797_mac_join_fail_stop', 'mt6797_ccmp_disable_key']:
    prefix = ('static int ' if name.endswith(('fail_stop', 'disable_key')) else '') + name + '('
    assert function(prefix) in parent, name
assert '#ifdef CONFIG_MT6797_CCMP_CONNECTED_LIFETIME' in entry
with tempfile.TemporaryDirectory(prefix='connected-lifetime-') as d:
    out = Path(d)
    for name, text in {
        'actual-open.inc': function('static int mt6797_mac_join_release_channel('),
        'actual-end.inc': function('static void mt6797_mac_join_end_data(struct mt6797_mac *mac, const char *reason)\n{'),
        'actual-pre-read.inc': function('static int mt6797_native_diag_pre_read('),
        'actual-poll.inc': guard,
        'actual-entry.inc': entry,
    }.items():
        (out / name).write_text(text)
    flags = ['cc', '-DCONFIG_MT6797_CCMP_CONNECTED_LIFETIME',
             '-DCONFIG_MT6797_CCMP_CHANNEL_RELEASE', '-DCONFIG_MT6797_CCMP_60S_WINDOW',
             '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
             '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    subprocess.run([*flags, '-I', d, '-I', str(a.source / sub),
                    str(Path(__file__).with_name('connected-lifetime-test.c')),
                    '-o', str(out / 'test')], check=True, timeout=30)
    subprocess.run([str(out / 'test')], check=True, timeout=30)
