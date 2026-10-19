#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual owned-loss handoff and station beacon-filter declaration; host only."""
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
mac = (a.source/sub/'mac.c').read_text()
parent = (a.parent/sub/'mac.c').read_text()
configs = set(re.findall(r'CONFIG_[A-Z0-9_]+', parent)) - {'CONFIG_MT6797_CCMP_CONNECTED_LIFETIME'}
for enabled in [set(), {'CONFIG_MT6797_CCMP_60S_WINDOW'}, configs]:
    results = []
    for text in [parent, mac]:
        text = re.sub(r'^#include[^\n]*', '', text, flags=re.M)
        out = subprocess.run(['cc', '-E', '-P', '-x', 'c', '-', '-DIS_ENABLED(x)=x',
                              '-UCONFIG_MT6797_CCMP_CONNECTED_LIFETIME',
                              *['-D'+n for n in sorted(enabled)]], input=text, text=True,
                             capture_output=True, check=True, timeout=30)
        results.append(re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]', out.stdout))
    assert results[0] == results[1], 'connected-monitor option-off MAC changed'


def function(prefix):
    start = mac.rindex(prefix)
    return mac[start:mac.index('\n}\n', start)+3]


for prefix in ['static int mt6797_mac_join_control_event(', 'static int mt6797_mac_join_fail_stop(',
               'static void mt6797_ccmp_timeout_observe(', 'static void mt6797_ccmp_connection_lost(']:
    assert function(prefix) in parent, prefix
worker = mac[mac.index('static void mt6797_mac_join_work('):]
assert worker.index('ret = mt6797_mac_join_control_event(mac, rx.logical_bytes);') < worker.index(
    'mt6797_ccmp_owned_loss(mac, rx.logical_bytes))') < worker.index(
    'mt6797_ccmp_timeout_observe(mac, rx.logical_bytes);')
with tempfile.TemporaryDirectory(prefix='connected-monitor-') as d:
    out = Path(d)
    for name, prefix in {
        'ready': 'static bool mt6797_ccmp_rx_ready(',
        'observe': 'static void mt6797_ccmp_timeout_observe(',
        'end': 'static void mt6797_mac_join_end_data(struct mt6797_mac *mac, const char *reason)\n{',
        'lost': 'static void mt6797_ccmp_connection_lost(',
        'owned': 'static bool mt6797_ccmp_owned_loss(',
        'add': 'static int mt6797_mac_add_interface(',
        'remove': 'static void mt6797_mac_remove_interface(',
    }.items():
        (out/('actual-'+name+'.inc')).write_text(function(prefix))
    flags = ['cc', '-DCONFIG_MT6797_CCMP_CONNECTED_LIFETIME', '-DCONFIG_MT6797_CCMP_INITIAL_GTK',
             '-DCONFIG_MT6797_PASSIVE_SCAN=1', '-std=c11', '-Wall', '-Wextra', '-Werror',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    subprocess.run([*flags, '-I', d, '-I', str(a.source/sub),
                    str(Path(__file__).with_name('connected-monitor-test.c')), '-o', str(out/'test')], check=True, timeout=30)
    subprocess.run([str(out/'test')], check=True, timeout=30)
print('connected-monitor option-off parity/unchanged fatal dispatcher and actual callback ordering PASS')
