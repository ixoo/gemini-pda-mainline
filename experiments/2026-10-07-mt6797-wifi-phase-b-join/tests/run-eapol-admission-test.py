#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check actual decoder reasons and unchanged admission against retained source."""
from pathlib import Path
import argparse, subprocess, tempfile
p=argparse.ArgumentParser()
p.add_argument('kernel_tree',type=Path)
p.add_argument('before_header',type=Path)
a=p.parse_args()
d=a.kernel_tree/'drivers/net/wireless/mediatek/mt6797'
with tempfile.TemporaryDirectory(prefix='eapol-admission-') as tmp:
 t=Path(tmp);(t/'eapol-before.h').write_bytes(a.before_header.read_bytes())
 out=t/'test'
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                 '-fno-omit-frame-pointer','-fno-pie','-no-pie','-I',str(t),'-I',str(d),
                 str(Path(__file__).with_name('eapol-admission-test.c')),'-o',str(out)],check=True,timeout=30)
 subprocess.run([str(out)],check=True,timeout=30)
s=(d/'mac.c').read_text()
trace=s.split('static void mt6797_mac_eapol_trace(',1)[1].split('static void mt6797_mac_join_work(',1)[0]
assert 'u8 header[32] = {0}' in trace
assert 'min_t(size_t, descriptor, sizeof(header)) : 16' in trace
assert 'memcpy(header, p, copied)' in trace and 'copied, (int)sizeof(header), header' in trace
assert 'join_eapol_trace > 64' in trace and 'trace suppressed: limit=64' in trace
assert 'mac->join_eapol_seen < 2' in s and '"delivery-cap"' in s
print('Actual logger wiring: descriptor-only bytes, explicit suppression and unchanged caller cap: PASS')
