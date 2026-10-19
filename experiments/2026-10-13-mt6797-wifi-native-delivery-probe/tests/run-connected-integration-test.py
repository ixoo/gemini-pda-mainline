#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Final connected tree: unchanged crypto/key/HIF sources and actual PTK/GTK fixtures."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
p.add_argument('--parent', type=Path, required=True, help='frozen I50 source')
a = p.parse_args()
sub = Path('drivers/net/wireless/mediatek/mt6797')
fixtures = Path(__file__).resolve().parent
for name in ['ccmp-rx.h', 'ccmp-gtk-rx.h', 'data-rx.h', 'join-events.h',
             'hif.c', 'hif.h', 'normal_command.h', 'join-command-submit.h', 'join-commands.h']:
    assert (a.source/sub/name).read_bytes() == (a.parent/sub/name).read_bytes(), name
old, new = ((root/sub/'mac.c').read_text() for root in [a.parent, a.source])


def function(text, name):
    match = re.search(r'\b'+re.escape(name)+r'\([^;]*?\)\n\{', text)
    assert match, name
    return text[match.start():text.index('\n}\n', match.start())+2]


for name in ['mt6797_ccmp_withdraw', 'mt6797_ccmp_rx_ready', 'mt6797_ccmp_queue_rx',
             'mt6797_ccmp_receive', 'mt6797_ccmp_disable_key', 'mt6797_mac_set_key',
             'mt6797_mac_sta_state', 'mt6797_mac_sta_set_decap_offload',
             'mt6797_mac_join_associate', 'mt6797_ccmp_connection_lost']:
    assert function(old, name) == function(new, name), name
for name, digest in {'ccmp-rx-test.c': '8a34df09b1d89644952de95e363fadec170f569fd5b39f75239d8a87606ba96b',
                     'ccmp-gtk-rx-test.c': 'fbf7cf5e170ab301289f695f680e0902375427b288f88164cd61aeeed265f763'}.items():
    assert hashlib.sha256((fixtures/name).read_bytes()).hexdigest() == digest
with tempfile.TemporaryDirectory(prefix='connected-integration-') as directory:
    out = Path(directory)
    baseline = (fixtures/'ccmp-rx-test.c').read_text().replace(
        '"../../2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c"',
        '"'+str(fixtures.parents[1]/'2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c')+'"')
    (out/'ptk-baseline.inc').write_text(baseline.replace('int main(void)', 'int ptk_baseline_tests(void)'))
    flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    subprocess.run([*flags, '-I', directory, '-I', str(a.source/sub),
                    str(fixtures/'ccmp-gtk-rx-test.c'), '-o', str(out/'test')], check=True, timeout=30)
    subprocess.run([str(out/'test')], check=True, timeout=30)
print('connected integration: ten key/queue/callback functions and nine crypto/HIF headers/files byte-identical; actual PTK/GTK tests PASS')
