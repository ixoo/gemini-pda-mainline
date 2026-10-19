#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual one-inflight PID pool, MAC allocation and completion ownership."""
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
for enabled in [set(), {'CONFIG_MT6797_CCMP_60S_WINDOW'}, configs]:
    outputs = []
    for text in [parent, mac]:
        text = re.sub(r'^#include[^\n]*', '', text, flags=re.M)
        out = subprocess.run(['cc', '-E', '-P', '-x', 'c', '-', '-DIS_ENABLED(x)=x',
                              '-UCONFIG_MT6797_CCMP_TX_PID_REUSE',
                              *['-D'+n for n in sorted(enabled)]], input=text, text=True,
                             capture_output=True, check=True, timeout=30)
        outputs.append(re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]', out.stdout))
    assert outputs[0] == outputs[1], 'PID option-off MAC changed'
print('completed-PID option-off MAC parity: three selections PASS')
start = mac.index('static int mt6797_ccmp_assign_pid(')
allocate = mac[start:mac.index('\n}\n', start)+3]
worker = mac[mac.index('static void mt6797_mac_join_work('):]
start = worker.index('\t\t\tif (mt6797_join_event(mac->join_packet, rx.logical_bytes, 0x0f, 16)) {')
end = worker.index('\n#ifdef CONFIG_MT6797_NATIVE_DELIVERY_DIAG', start)
block = worker[start:end]
# Use the exact new unowned and validated retirement blocks. The old owned
# decoder/status predicate is extracted too; its errors must precede retirement.
u0 = block.index('#ifdef CONFIG_MT6797_CCMP_TX_PID_REUSE')
u1 = block.index('#endif', u0)+len('#endif')
unowned = block[u0:u1].replace('continue;', 'return 1;')
o0 = block.index('\t\t\t\tif (!mac->join_inflight ||', u1)
o1 = block.index('\n#ifdef CONFIG_MT6797_CCMP_TX_PID_REUSE', o0)
owned = block[o0:o1]
r0 = o1+1
r1 = block.index('#endif', r0)+len('#endif')
retire = block[r0:r1]
assert block.index('mt6797_join_tx_done(') < block.index('mt6797_join_pid_complete(') < block.index('mac->join_inflight = NULL;')
assert mac.count('ret = mt6797_ccmp_assign_pid(') == 2
assert 'mac->ccmp_pid_pool.next = 1;' in mac
# No timeout/re-arm change; an uncompleted ordinary slot has no release path.
for prefix in ['static bool mt6797_ccmp_deauth_retire(', 'static int mt6797_mac_join_fail_stop(']:
    # fail_stop also has a forward declaration; select its definition.
    matches = [m.start() for m in re.finditer(re.escape(prefix), mac)]
    start = matches[-1]
    text = mac[start:mac.index('\n}\n', start)+3]
    assert text in parent, prefix
with tempfile.TemporaryDirectory(prefix='completed-pid-') as d:
    out = Path(d)
    pool_start = mac.index('/* One initial station/key epoch, one frame in flight.')
    pool_end = mac.index('\n#endif', pool_start)
    (out/'actual-pid-pool.inc').write_text(mac[pool_start:pool_end])
    (out/'actual-assign.inc').write_text(allocate)
    (out/'actual-complete.inc').write_text('static int actual_complete(struct mt6797_mac *mac, size_t bytes) {\nstruct mt6797_join_tx_result result; int ret=0;\nif (!mt6797_join_event(mac->join_packet, bytes, 0x0f, 16)) return -EPROTO;\n' + unowned + '\n' + owned + '\n' + retire + '\nreturn 0;\nfailed: return ret;\n}\n')
    flags = ['cc', '-DCONFIG_MT6797_CCMP_TX_PID_REUSE', '-std=c11', '-Wall', '-Wextra', '-Werror',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    subprocess.run([*flags, '-I', d, '-I', str(a.source/sub),
                    str(Path(__file__).with_name('completed-pid-test.c')), '-o', str(out/'test')], check=True, timeout=30)
    subprocess.run([str(out/'test')], check=True, timeout=30)
