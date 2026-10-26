#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Early M1 (0305): the actual EAPOL-Key receive admission and refusal name; host behaviour only."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('parent', type=Path, help='source tree before 0305')
p.add_argument('child', type=Path, help='source tree with 0305')
a = p.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
fixtures = Path(__file__).resolve().parent


def extract(text):
    start = text.index('\t\t\tif (eapol_gate == MT6797_EAPOL_OK &&') + len('\t\t\tif ')
    end = text.index(') {\n\t\t\t\tmt6797_mac_eapol_trace(mac, rx.logical_bytes, "admitted"', start) + 1
    gate = text[start:end]
    start = text.index('\t\t\t\teapol_gate != MT6797_EAPOL_OK ? mt6797_eapol_gate_name(eapol_gate) :')
    end = text.index('"bss-interval",', start) + len('"bss-interval"')
    name = text[start:end]
    return ('static bool admitted(struct mt6797_mac *mac, int eapol_gate, struct mt6797_eapol eapol)\n'
            '{\n\treturn ' + gate + ';\n}\n\n'
            'static const char *refusal(struct mt6797_mac *mac, int eapol_gate)\n'
            '{\n\treturn\n' + name + ';\n}\n')


flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
if sys.platform.startswith('linux'):
    flags += ['-fno-pie', '-no-pie']
for label, tree, child in [('parent', a.parent, False), ('child', a.child, True)]:
    with tempfile.TemporaryDirectory(prefix='early-m1-') as directory:
        tmp = Path(directory)
        text = (tree.resolve() / rel / 'mac.c').read_text()
        (tmp / 'early-m1-functions.inc').write_text(extract(text))
        binary = tmp / label
        subprocess.run([*flags, *([] if child else ['-DPARENT']), '-I', str(tmp),
                        str(fixtures / 'early-m1-test.c'), '-o', str(binary)], check=True, timeout=60)
        subprocess.run([str(binary)], check=True, timeout=30)
print('PASS early M1 on the actual receive admission; the access point and supplicant timing are not proved here')
