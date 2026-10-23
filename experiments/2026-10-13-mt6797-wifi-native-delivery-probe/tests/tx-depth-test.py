#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile actual depth/PID code and check MAC ownership wiring; no hardware."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def function(source, name):
    start = source.index(name + '(')
    start = source.rfind('\nstatic ', 0, start) + 1
    # Kernel function terminators are unindented; preprocessor alternatives
    # can contain mutually exclusive opening braces, so do not count braces.
    end = source.index('\n}\n', start) + len('\n}')
    return source[start:end]


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('tree', type=Path)
parser.add_argument('parent_mac', type=Path)
args = parser.parse_args()
driver = args.tree/'drivers/net/wireless/mediatek/mt6797'
source = (driver/'mac.c').read_text()
parent = args.parent_mac.read_text()
assert (driver/'join-tx.h').read_bytes() == (args.parent_mac.parent/'join-tx.h').read_bytes()
assert function(source, 'mt6797_mac_join_guard') == function(parent, 'mt6797_mac_join_guard')
start = source.index('#ifdef CONFIG_MT6797_CCMP_TX_PID_REUSE\n')
end = source.index('#endif\n', start)
pid_code = source[start + len('#ifdef CONFIG_MT6797_CCMP_TX_PID_REUSE\n'):end]
assert 'struct mt6797_join_pid_pool {' in pid_code
assert 'mt6797_join_pid_complete(' in pid_code
assert '#if' not in pid_code

# These are the actual MAC handoff, queue preflight, retirement and teardown
# sites. Dynamic fixture coverage below exercises the helpers they call.
for fragment in (
    'mac->join_data_page_debt += pages;',
    'mt6797_data_put(&mac->data_slots, mac->join_pid,\n\t\t\t\t\t\t     mac->join_inflight, mac->join_frame_deadline)',
    'owner = mt6797_data_find(&mac->data_slots, mac->join_packet[8]);',
    'mac->join_frame_deadline = owner->deadline;',
    'mac->join_inflight = mt6797_data_take(&mac->data_slots, owner->pid);',
    'while ((skb = mt6797_data_pop(&mac->data_slots)))',
    'while ((owned = mt6797_data_pop(&mac->data_slots)))',
    'mt6797_data_expired(&mac->data_slots, now)',
    'mac->ccmp_pid_pool.used[pid] && !mac->ccmp_pid_pool.completed[pid]',
    'ledger.locked ? 0 : ledger.tc1_free',
    'mac->ccmp_reserved_pid_used || mac->ccmp_pid_pool.pending',
):
    assert ' '.join(fragment.split()) in ' '.join(source.split()), fragment
assert source.index('if (!mt6797_ccmp_data_room(mac, walk->len))') < source.index('\t\t\t\t__skb_unlink(walk, &mac->join_queue);\n\t\t\t\tskb = walk;')
deadline = 'mac->join_frame_deadline = ktime_get_ns() + 750 * NSEC_PER_MSEC;'
assert source.count(deadline) == parent.count(deadline) == 3
quiescent = re.findall(r'\tc\.quiescent = [^;]+;', source)
assert len(quiescent) == 1 and '!mac->data_slots.count' in quiescent[0]

with tempfile.TemporaryDirectory(prefix='tx-depth-') as directory:
    temporary = Path(directory)
    (temporary/'pid-source.inc').write_text(pid_code)
    (temporary/'prepare-data-source.inc').write_text(
        function((driver/'join-submit.h').read_text(), 'mt6797_join_prepare_data') + '\n')
    (temporary/'room-source.inc').write_text('''
#define MT6797_JOIN_TX_DESC_BYTES 28U
struct mt6797_hif_ledger { bool locked; unsigned int tc1_free; };
struct mt6797_mac {
    struct mt6797_hif_ledger *hif;
    struct mt6797_join_pid_pool ccmp_pid_pool;
    struct mt6797_data_slots data_slots;
};
static void mt6797_hif_normal_ledger(struct mt6797_hif_ledger *hif,
                                    struct mt6797_hif_ledger *ledger)
{ *ledger = *hif; }
''' + function(source, 'mt6797_ccmp_data_room') + '\n')
    (temporary/'quiescence-source.inc').write_text('''
static bool fixture_quiescent(const struct mt6797_data_slots *slots,
                             bool credit, unsigned int debt, void *inflight)
{
    struct { bool join_credit_pending; unsigned int join_page_debt;
             void *join_inflight; struct mt6797_data_slots data_slots; }
        state = {credit, debt, inflight, *slots}, *mac = &state;
    struct { bool quiescent; } c;
''' + quiescent[0] + '''
    return c.quiescent;
}
''')
    for depth in (1, 4):
        binary = temporary/('fixture-' + str(depth))
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-DCONFIG_MT6797_CCMP_TX_DEPTH=' + str(depth),
                        '-I', str(driver), '-I', str(temporary),
                        str(Path(__file__).with_suffix('.c')), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
        print('depth=' + str(depth) + ': actual PID/slot ownership, deadlines, credit refusal and quiescence PASS')
        credit_binary = temporary/('credit-' + str(depth))
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-DCONFIG_MT6797_CCMP_TX_DEPTH=' + str(depth),
                        '-I', str(temporary), str(Path(__file__).with_name('tx-depth-credit-test.c')),
                        '-o', str(credit_binary)], check=True)
        subprocess.run([str(credit_binary)], check=True)
        print('depth=' + str(depth) + ': actual prepare-data partial-TC1 gate, exact charge and ENOSPC ledger preservation PASS')
print('MAC queue/completion/teardown wiring; unchanged guard accounting and TX descriptors PASS')
