#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual 50-second constants/opening; inherited release/resource path parity."""
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
configs = set(re.findall(r'CONFIG_[A-Z0-9_]+', (a.parent / sub / 'mac.c').read_text()))
for name in ['mac.c', 'native-diag.h']:
    for selected in [set(), configs, configs | {'CONFIG_MT6797_CCMP_CHANNEL_RELEASE'}]:
        results = []
        for root in [a.parent, a.source]:
            source = re.sub(r'^#include[^\n]*', '', (root / sub / name).read_text(), flags=re.M)
            out = subprocess.run(['cc', '-E', '-P', '-x', 'c', '-', '-DIS_ENABLED(x)=x',
                                  '-UCONFIG_MT6797_CCMP_50S_IDLE',
                                  *['-D' + symbol for symbol in sorted(selected)]],
                                 input=source, text=True, capture_output=True, check=True, timeout=30)
            results.append(re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]', out.stdout))
        assert results[0] == results[1], name
print('50s option-off MAC/native parity: six selections PASS')
# Actual whole MAC differs only in one conditional constant definition.
old = (a.parent / sub / 'mac.c').read_text()
assert mac.replace('#ifdef CONFIG_MT6797_CCMP_50S_IDLE\n#define MT6797_JOIN_DATA_BUDGET_MS 50000U\n#else\n#define MT6797_JOIN_DATA_BUDGET_MS 60000U\n#endif',
                   '#define MT6797_JOIN_DATA_BUDGET_MS 60000U') == old
h = (a.source / sub / 'native-diag.h').read_text()
assert h.replace('#ifdef CONFIG_MT6797_CCMP_50S_IDLE\n#define MT6797_NATIVE_DIAG_WALL_MS    50000U\n#else\n#define MT6797_NATIVE_DIAG_WALL_MS    60000U\n#endif',
                 '#define MT6797_NATIVE_DIAG_WALL_MS    60000U') == (a.parent / sub / 'native-diag.h').read_text()
with tempfile.TemporaryDirectory(prefix='50s-idle-') as d:
    out = Path(d)
    for fname, signature in [('actual-channel-release.inc', 'static int mt6797_ccmp_channel_release_step('),
                             ('actual-open-data.inc', 'static int mt6797_mac_join_release_channel(')]:
        start = mac.index(signature)
        (out / fname).write_text(mac[start:mac.index('\n}\n', start) + 3])
    start = mac.index('\tif (mt6797_join_event(mac->join_packet, bytes, 0x10, 16)) {')
    end = mac.index('\tif (mt6797_join_event(mac->join_packet, bytes, 0x0c, 8)) {', start)
    (out / 'actual-grant.inc').write_text('static int actual_grant(struct mt6797_mac *mac) {\nunsigned int interval; int expected = 0; size_t bytes = 24;\n' + mac[start:end] + '\nreturn -EINVAL;\n}\n')
    # Reuse the established actual-source release/grant fixture with only its
    # selected constant and expected 50-second endpoint changed.
    fixture = Path(__file__).with_name('channel-release-test.c').read_text()
    fixture = fixture.replace('#define MT6797_JOIN_DATA_BUDGET_MS 60000U',
                              mac[mac.index('#ifdef CONFIG_MT6797_CCMP_50S_IDLE\n'):mac.index('#define MT6797_JOIN_TEARDOWN_MARGIN_MS')].strip())
    assert fixture.count('test_now + 60000000000ULL') == 1
    fixture = fixture.replace('test_now + 60000000000ULL', 'test_now + 50000000000ULL')
    (out / 'test.c').write_text(fixture)
    flags = ['cc', '-DCONFIG_MT6797_CCMP_50S_IDLE', '-DCONFIG_MT6797_CCMP_CHANNEL_RELEASE',
             '-DCONFIG_MT6797_CCMP_60S_WINDOW', '-std=c11', '-Wall', '-Wextra', '-Werror',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    subprocess.run([*flags, '-I', d, str(out / 'test.c'), '-o', str(out / 'test')], check=True, timeout=30)
    subprocess.run([str(out / 'test')], check=True, timeout=30)
    flags_header = '\n'.join('#define RX_FLAG_' + s + ' 0U' for s in
                             ['DECRYPTED', 'IV_STRIPPED', 'PN_VALIDATED', 'MMIC_STRIPPED',
                              'MIC_STRIPPED', 'ALLOW_SAME_PN', 'NO_SIGNAL_VAL'])
    (out / 'budget.c').write_text('#include <assert.h>\n#include <stddef.h>\n' + flags_header + '\n#include "native-diag.h"\nint main(void) {\nstruct mt6797_native_diag_budget b = { .elapsed_ms = 49999 };\nassert(MT6797_NATIVE_DIAG_WALL_MS == 50000U);\nassert(mt6797_ccmp_diag_budget_step(&b) == MT6797_NATIVE_DIAG_CONTINUE);\nb.elapsed_ms++; assert(mt6797_ccmp_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP);\nb.elapsed_ms++; assert(mt6797_ccmp_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP);\nassert(MT6797_CCMP_DIAG_RX_MAX == 4096 && MT6797_CCMP_DIAG_CHECKED_MAX == 1024 && MT6797_CCMP_DIAG_BYTES_MAX == 2097152);\nreturn 0; }\n')
    subprocess.run([*flags, '-I', str(a.source / sub), str(out / 'budget.c'), '-o', str(out / 'budget')], check=True, timeout=30)
    subprocess.run([str(out / 'budget')], check=True, timeout=30)
print('50s actual-source opening, budget +/-1 ms, unchanged caps and release cases PASS')
