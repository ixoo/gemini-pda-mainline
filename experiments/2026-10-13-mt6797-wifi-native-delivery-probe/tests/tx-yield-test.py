#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual yield helper and exact worker-only delta; hardware-free sanitizer test."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('tree', type=Path)
parser.add_argument('parent_mac', type=Path)
args = parser.parse_args()
driver = args.tree/'drivers/net/wireless/mediatek/mt6797'
source = (driver/'mac.c').read_text()
parent = args.parent_mac.read_text()
normalized = source
for inserted in (
    '#ifdef CONFIG_MT6797_CCMP_TX_PUMP\n\tbool pump_progress = false;\n#endif\n',
    '#ifdef CONFIG_MT6797_CCMP_TX_PUMP\n\t\t\tpump_progress = true;\n#endif\n',
    '#ifdef CONFIG_MT6797_CCMP_TX_PUMP\n\t\t\t\tpump_progress = true;\n#endif\n',
):
    assert normalized.count(inserted) == 1
    normalized = normalized.replace(inserted, '')
assert normalized.count('pending, pump_progress);') == 1
normalized = normalized.replace('pending, pump_progress);', 'pending);')
assert normalized == parent, 'MAC changes extend beyond the reviewed pump delta'
kconfig = (driver/'Kconfig').read_text()
new_help = ('\t  After at most 32 iterations without TX progress, request a 1 ms\n'
            '\t  yield. Idle polls retain 20 ms. This changes scheduling only, not\n')
old_help = ('\t  After at most 32 immediate iterations, yield for the existing 20 ms\n'
            '\t  interval. Idle polls retain 20 ms. This changes scheduling only, not\n')
assert kconfig.count(new_help) == 1
assert kconfig.replace(new_help, old_help) == (args.parent_mac.parent/'Kconfig').read_text()
assert source.index('submitted:\n') < source.index('\t\t\tpump_progress = true;') < source.index('mt6797_data_put(&mac->data_slots')
assert source.index('!mt6797_join_tx_done(') < source.index('!mt6797_join_pid_complete(') < source.index('\t\t\t\tpump_progress = true;') < source.index('completed = mac->join_inflight;')
assert 'snapshot_delay = msecs_to_jiffies(delay_ms);' in source
pending = re.findall(r'\t\tbool pending = [^;]+;', source)
assert len(pending) == 1
assert pending[0].count('!skb_queue_empty(&mac->join_queue)') == 1
pending = pending[0].replace('!skb_queue_empty(&mac->join_queue)', 'queue_not_empty')
with tempfile.TemporaryDirectory(prefix='tx-yield-') as directory:
    temporary = Path(directory)
    (temporary/'pending-source.inc').write_text('''
struct fixture_mac {
    void *join_inflight;
    struct { unsigned int count; } data_slots;
    bool join_credit_pending;
    unsigned int join_page_debt, join_data_page_debt;
};
static bool fixture_pending(bool queue_not_empty, const struct fixture_mac *mac)
{
''' + pending + '''
    return pending;
}
''')
    binary = temporary/'fixture'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-I', str(driver), '-I', str(temporary),
                    str(Path(__file__).with_suffix('.c')), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('progress resets guard; pending no-progress: 32 immediate turns then 1 ms request; idle: 20 ms PASS')
print('finite burst/stuck pending and all six actual pending terms PASS; other MAC code unchanged')
print('worker retains msecs_to_jiffies: at HZ=250 a 1 ms request rounds to one 4 ms jiffy')
