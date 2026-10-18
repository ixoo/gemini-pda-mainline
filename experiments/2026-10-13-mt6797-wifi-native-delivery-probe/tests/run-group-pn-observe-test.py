#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""C10 actual-source group metadata observation; no firmware or device effects."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('parent', type=Path)
ap.add_argument('child', type=Path)
a = ap.parse_args()
f = Path(__file__).resolve().parent
rel = Path('drivers/net/wireless/mediatek/mt6797')
p, c = a.parent.resolve() / rel, a.child.resolve() / rel
for n, want in {
    'mac.c': '9c436a627a5b23a416b9fc2a1401f349a10e971af4086464117bc6d50890ef88',
    'Kconfig': '61d2498088e43cd1496344b6f2d80a1117cda5cb66859113521ca189190a069a',
    'data-rx.h': '02179812099659607a99e0d092c58c031960375f64d502a566274c413106134a',
    'ccmp-rx.h': '35b581f1cd3abdda66e8b392b39bd538875975e2254e80488dc1cc8dbbec85a0',
}.items():
    assert hashlib.sha256((p/n).read_bytes()).hexdigest() == want, n
assert {x.name for x in p.iterdir()} == {x.name for x in c.iterdir()}
for x in p.iterdir():
    if x.is_file() and x.name not in {'mac.c', 'Kconfig'}:
        assert x.read_bytes() == (c/x.name).read_bytes(), x.name
assert (a.parent/'drivers/soc/mediatek/mt6797-consys.c').read_bytes() == (
    a.child/'drivers/soc/mediatek/mt6797-consys.c').read_bytes()
assert (c/'Kconfig').read_text().startswith((p/'Kconfig').read_text())
parent, child = (p/'mac.c').read_text(), (c/'mac.c').read_text()
option = 'CONFIG_MT6797_CCMP_GROUP_PN_OBSERVE'

def function(source, name):
    match = re.search(r'^static [^\n]+\b' + name + r'\(', source, re.M)
    assert match, name
    start = match.start()
    return source[start:source.index('\n}\n', start)+3]

observer = function(child, 'mt6797_ccmp_group_observe')
for forbidden in ['ieee80211_', 'ccmp_rx_check', 'dev_alloc', 'skb_', 'hif_', 'readl', 'writel', 'memcpy']:
    assert forbidden not in observer, forbidden
queue = function(child, 'mt6797_ccmp_queue_rx')
hook = '#ifdef '+option+'\n\tmt6797_ccmp_group_observe(mac, bytes);\n#endif\n'
assert queue.count(hook) == 1
assert queue.replace(hook, '') == function(parent, 'mt6797_ccmp_queue_rx')
assert queue.index('if (!mt6797_ccmp_rx_ready') < queue.index(hook) < queue.index('dev_alloc_skb')
assert child.count('one-shot WLAN group PN observation:') == 1
# Every key/crypto/lifetime/transport function outside the two named sites is
# unchanged after removing only the new option blocks (preprocessing below).
with tempfile.TemporaryDirectory(prefix='mt6797-group-pn-') as directory:
    tmp = Path(directory)
    reverse = tmp/'reverse'
    shutil.copytree(c, reverse/rel)
    patch = f.parents[2]/'patches/proposals/0201-wifi-mt6797-observe-initial-GTK-PN-metadata.patch'
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=reverse, check=True, timeout=30)
    for source in p.iterdir():
        if source.is_file():
            assert source.read_bytes() == (reverse/rel/source.name).read_bytes(), source.name
    (tmp/'group-observe.inc').write_text(observer)
    (tmp/'group-report.inc').write_text(function(child, 'mt6797_native_diag_rx_report'))
    common = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
              '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        common += ['-fno-pie', '-no-pie']
    binary = tmp/'test'
    subprocess.run(common + ['-D'+option, '-I', str(tmp), '-I', str(c),
                              str(f/'group-pn-observe-test.c'), '-o', str(binary)],
                   check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
    subprocess.run(common + ['-I', str(c), str(f/'ccmp-rx-test.c'), '-o', str(tmp/'ptk')],
                   check=True, timeout=30)
    subprocess.run([str(tmp/'ptk')], check=True, timeout=30)
    # Headers are already pinned/unchanged. Preprocess the entire actual MAC
    # body without include resolution; compare both normal and C10 option sets.
    for flags in [[], ['-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG',
                       '-DCONFIG_MT6797_CCMP_STABLE_EPOCH',
                       '-DCONFIG_MT6797_CCMP_MASK_CONTROL']]:
        outputs = []
        for label, source in [('parent', parent), ('child-off', child)]:
            path = tmp/(label+'.c')
            path.write_text(re.sub(r'^#include[^\n]*\n', '', source, flags=re.M))
            result = subprocess.run(['cc', '-E', '-P', '-DIS_ENABLED(x)=1', *flags, str(path)],
                                    check=True, capture_output=True, text=True, timeout=30)
            outputs.append(result.stdout)
        assert outputs[0] == outputs[1], 'option-off complete MAC changed'
print('PASS C10 pins; unchanged HIF/RX/crypto/key/lifetime inputs; complete option-off MAC parity')
print('Metadata availability only; no GTK admission, firmware integrity or key retirement proof')
