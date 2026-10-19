#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual connected observation caps; no larger queues or longer transactions."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path)
p.add_argument('--parent',type=Path,required=True)
a=p.parse_args()
sub=Path('drivers/net/wireless/mediatek/mt6797')
for name in ['mac.c','native-diag.h']:
    old=(a.parent/sub/name).read_text()
    configs=set(re.findall(r'CONFIG_[A-Z0-9_]+',old))-{'CONFIG_MT6797_CCMP_CONNECTED_LIFETIME'}
    for enabled in [set(),{'CONFIG_MT6797_CCMP_60S_WINDOW'},configs]:
        results=[]
        for root in [a.parent,a.source]:
            text=re.sub(r'^#include[^\n]*','',(root/sub/name).read_text(),flags=re.M)
            out=subprocess.run(['cc','-E','-P','-x','c','-','-DIS_ENABLED(x)=x',
                                '-UCONFIG_MT6797_CCMP_CONNECTED_LIFETIME',
                                *['-D'+n for n in sorted(enabled)]],input=text,text=True,
                               capture_output=True,check=True,timeout=30)
            results.append(re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]',out.stdout))
        assert results[0]==results[1],name
mac=(a.source/sub/'mac.c').read_text()
for definition in ['MT6797_JOIN_DATA_TX_QUEUE 8U','MT6797_JOIN_DATA_TX_QUEUE_BYTES (8U * 1550U)',
                   'MT6797_JOIN_TEARDOWN_MARGIN_MS 5000U','MT6797_JOIN_MAX_POLLS 4096U',
                   'MT6797_JOIN_GRANT_TAIL_MS 2500U']:
    assert '#define '+definition in mac
h=(a.source/sub/'native-diag.h').read_text()
for definition in ['MT6797_NATIVE_DIAG_RETIRE_READS 64U','MT6797_NATIVE_DIAG_RETIRE_BYTES (256U * 1024U)',
                   'MT6797_NATIVE_DIAG_RETIRE_MS    750U']:
    assert '#define '+definition in h
with tempfile.TemporaryDirectory(prefix='connected-capacity-') as d:
    out=Path(d)
    start=mac.index('#ifdef CONFIG_MT6797_CCMP_CONNECTED_LIFETIME\n/* Covers the connected observation')
    end=mac.index('#endif',start)+len('#endif')
    (out/'actual-packet-cap.inc').write_text(mac[start:end])
    flags=['cc','-DCONFIG_MT6797_CCMP_CONNECTED_LIFETIME','-DCONFIG_MT6797_CCMP_60S_WINDOW',
           '-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags+=['-fno-pie','-no-pie']
    subprocess.run([*flags,'-I',d,'-I',str(a.source/sub),
                    str(Path(__file__).with_name('connected-capacity-test.c')),'-o',str(out/'test')],
                   check=True,timeout=30)
    subprocess.run([str(out/'test')],check=True,timeout=30)
print('connected capacity actual constants/limits +/-1 and six option-off parity selections PASS')
