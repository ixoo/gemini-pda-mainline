#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Bounded join retry (0304): the actual prepare, admission and validator code; host behaviour only."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('parent', type=Path, help='source tree before 0304')
p.add_argument('child', type=Path, help='source tree with 0304')
a = p.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
fixtures = Path(__file__).resolve().parent


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start) + 3]


def span(text, first, last):
    start = text.index(first)
    return text[start:text.index(last, start) + len(last)]


def queue(text):
    """mac_tx's management admission, as a function of the hw and the frame."""
    tx = text.index('static void mt6797_mac_tx(struct ieee80211_hw *hw,')
    start = text.index('\tif (skb->len >= 24 && skb->len <= 2304 &&\n'
                       '\t    !skb_copy_bits(skb, 0, header, 24)) {', tx)
    end = text.index('\n\tif (accepted)\n\t\treturn;', start)
    return ('static bool queue(struct ieee80211_hw *hw, struct sk_buff *skb)\n{\n'
            '\tstruct mt6797_mac *mac = hw->priv;\n\tu8 header[24];\n'
            '\tunsigned long flags;\n\tunsigned int fc, subtype;\n'
            '\tbool accepted = false;\n\n' + text[start:end] + '\n\treturn accepted;\n}\n')


def extract(text, child):
    parts = [span(text, 'static const u8 mt6797_join_rsn_body[18] = {', '\n};\n'),
             function(text, 'static bool mt6797_join_rsn_capabilities('),
             span(text, '#define MT6797_HT_CAP_INFO', '\n'),
             span(text, '#define MT6797_HT_AMPDU_PARAMS', 'SHIFT))\n'),
             function(text, 'static bool mt6797_join_ht_cap_ok(')]
    if child:
        parts += [span(text, '#define MT6797_JOIN_ATTEMPTS', '\n'),
                  function(text, 'static bool mt6797_join_attempt_open('),
                  function(text, 'static void mt6797_join_attempt_note(')]
    else:
        assert 'MT6797_JOIN_ATTEMPTS' not in text
    parts += [function(text, 'static bool mt6797_mac_join_frame('),
              function(text, 'static void mt6797_mac_mgd_prepare_tx('), queue(text)]
    return '\n'.join(parts)


flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
         '-DCONFIG_MT6797_STATION_JOIN', '-DCONFIG_MT6797_WMM_QOS_DATA',
         '-DCONFIG_MT6797_HT_CAPABILITY']
if sys.platform.startswith('linux'):
    flags += ['-fno-pie', '-no-pie']
for label, tree, child in [('parent', a.parent, False), ('child', a.child, True)]:
    driver = tree.resolve() / rel
    with tempfile.TemporaryDirectory(prefix='join-attempt-') as directory:
        tmp = Path(directory)
        (tmp / 'join-attempt-functions.inc').write_text(extract((driver / 'mac.c').read_text(), child))
        binary = tmp / label
        subprocess.run([*flags, *([] if child else ['-DPARENT']), '-I', str(driver), '-I', str(tmp),
                        str(fixtures / 'join-attempt-test.c'), '-o', str(binary)],
                       check=True, timeout=60)
        subprocess.run([str(binary)], check=True, timeout=30)
print('PASS bounded join retry on the actual prepare, admission and validator; no firmware or air proof')
