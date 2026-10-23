#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Test the actual scheduling helper and unchanged ownership/accounting source."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('tree',type=Path)
p.add_argument('parent_mac',type=Path)
a=p.parse_args()
driver=a.tree/'drivers/net/wireless/mediatek/mt6797'
source=(driver/'mac.c').read_text()
parent=a.parent_mac.read_text()
assert 'depends on MT6797_CCMP_CONNECTED_LIFETIME && MT6797_CCMP_TX_PID_REUSE' in (driver/'Kconfig').read_text()
assert '\tdefault n\n' in (driver/'Kconfig').read_text().split('config MT6797_CCMP_TX_PUMP\n')[1]
# The only worker-body change must be the bounded scheduling choice. All TX
# selection, completion attribution, credit reconciliation and teardown remain.
include='#ifdef CONFIG_MT6797_CCMP_TX_PUMP\n#include "join-pump.h"\n#endif\n'
field='#ifdef CONFIG_MT6797_CCMP_TX_PUMP\n\tunsigned int join_pump_zero_runs;\n#endif\n'
start=source.index('#ifdef CONFIG_MT6797_CCMP_TX_PUMP\n\tif (ccmp_stable_epoch')
end=source.index('#endif\n',start)+len('#endif\n')
schedule=source[start:end]
for term in ('!skb_queue_empty(&mac->join_queue)','mac->join_inflight',
             'mac->join_credit_pending','mac->join_page_debt','mac->join_data_page_debt'):
    assert term in schedule
assert source[:start].replace(include,'').replace(field,'')+source[end:]==parent
with tempfile.TemporaryDirectory(prefix='tx-pump-') as directory:
    binary=Path(directory)/'fixture'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                    '-I',str(driver),str(Path(__file__).with_suffix('.c')),
                    '-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
print('pending=0ms; idle=20ms; bounded immediate guard PASS; accounting/PID/admission source unchanged')
