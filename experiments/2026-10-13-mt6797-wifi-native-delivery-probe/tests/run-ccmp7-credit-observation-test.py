#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Reuse the actual C6 helpers' fixture for C7; preserve every timeout gate."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('parent', type=Path)
parser.add_argument('child', type=Path)
args = parser.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
parent, child = args.parent / rel, args.child / rel
fixtures = Path(__file__).resolve().parent
repo = fixtures.parents[2]
assert hashlib.sha256((parent / 'mac.c').read_bytes()).hexdigest() == (
    '216b899cc84f56a55698fc3b7688a5e7d526e068711bdc90eeffe76916ec14ed')
assert {p.name for p in parent.iterdir()} == {p.name for p in child.iterdir()}
for p in parent.iterdir():
    if p.is_file() and p.name != 'mac.c':
        assert p.read_bytes() == (child / p.name).read_bytes(), p.name
assert (args.parent / 'drivers/soc/mediatek/mt6797-consys.c').read_bytes() == (
    args.child / 'drivers/soc/mediatek/mt6797-consys.c').read_bytes()
old, mac = (parent / 'mac.c').read_text(), (child / 'mac.c').read_text()


def braced(text, marker):
    start = text.index(marker)
    opening = text.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def gate(text):
    start = text.index('\tnow = ktime_get_ns();\n\tbranch = 1;')
    end = text.index('\tbranch = 2;', start)
    return text[start:end]


new_gate, tags = re.subn(
    r'^#ifdef CONFIG_MT6797_CCMP_STABLE_EPOCH\n\t+mac->ccmp_observation.branch1_site = [123];\n#endif\n',
    '', gate(mac), flags=re.M)
assert tags == 3 and new_gate == gate(old), 'condition/order/short-circuit/deadline changed'
names = ('mt6797_ccmp_observe_rx', 'mt6797_ccmp_observe_guard', 'mt6797_ccmp_observe_terminal')
functions = [braced(mac, 'static void ' + n + '(') for n in names]
assert functions[0] == braced(old, 'static void ' + names[0] + '(')
for body in functions:
    assert 'hif_read' not in body and 'hif_write' not in body
    assert 'normal_reconcile' not in body and 'join_packet' not in body
assert mac.count('mt6797_ccmp_observe_terminal(mac);') == 2

fixture = (fixtures / 'ccmp-completion-observation-test.c').read_text()
fixture = fixture.replace('output[3][1024]', 'output[4][1024]').replace('lines < 3', 'lines < 4').replace('lines == 3', 'lines == 4')
fixture = fixture.replace('struct mt6797_hif_tx_status { u32 whcr, whisr; };', '''
struct mt6797_hif_tx_status { u32 whcr, whisr, wtqcr[8]; };
struct mt6797_normal_release {
    unsigned int released_pages, tc4_free, pending_cpu, pending_ffa;
    unsigned int tc1_released, tc1_free, pending_ac1;
};''')
fixture = fixture.replace('u64 join_frame_deadline;', '''u64 join_frame_deadline;
    u64 join_credit_deadline, join_deadline;
    unsigned int join_polls;
    bool join_credit_pending, scan_active, closing;
    int first_error;
    unsigned char native_diag_state;''')
fixture = fixture.replace('struct mt6797_hif_tx_status guard = { .whcr = 0x1234, .whisr = 5 };', '''
struct mt6797_hif_tx_status guard = { .whcr = 0x1234, .whisr = 5, .wtqcr = { [7] = 0x10000 } };
    struct mt6797_normal_release account = { .tc4_free = 25, .pending_cpu = 1, .tc1_free = 16 };''')
fixture = fixture.replace('mt6797_ccmp_observe_guard(o, &guard);', 'mt6797_ccmp_observe_guard(o, &guard, &account);')
fixture = fixture.replace('mac.join_frame_deadline = 750000100;', '''mac.join_frame_deadline = 750000100;
    mac.native_diag_state = 3;
    mac.join_credit_pending = true;
    mac.join_credit_deadline = 120;
    mac.join_deadline = 5000;
    mac.join_polls = 42;
    o->branch1_site = 3;''')
fixture = fixture.replace('/* Terminal state is frozen,', '''assert(strstr(output[3], "site=3 native_state=3 pending=1 credit_deadline_ns=120 lifetime_deadline_ns=5000 polls=42"));
    assert(strstr(output[3], "wtqcr7=0x00010000 tc4_free=25 cpu_pending=1 ffa_pending=0 tc1_free=16"));
    /* Terminal state is frozen,''')
fixture = fixture.replace('puts("CCMP completion observation: pass");', '''
    memset(&mac, 0, sizeof(mac));
    o->active = true;
    guard.wtqcr[7] = 1;
    account.pending_cpu = 0;
    account.pending_ffa = 1;
    mt6797_ccmp_observe_guard(o, &guard, &account);
    assert(o->wtqcr7 == 1 && o->credit.pending_cpu == 0 && o->credit.pending_ffa == 1);
    guard.wtqcr[7] = 0;
    mt6797_ccmp_observe_guard(o, &guard, &account);
    assert(o->wtqcr7 == 0 && o->credit.pending_ffa == 1);
    assert(account.tc4_free == 25 && account.pending_ffa == 1);
    puts("C7 credit observation: pass (raw versus accumulated CPU/FFA, no refund)");''')

with tempfile.TemporaryDirectory(prefix='ccmp7-credit-') as directory:
    tmp = Path(directory)
    (tmp / 'observation-struct.h').write_text(braced(mac, 'struct mt6797_ccmp_observation {') + ';\n')
    (tmp / 'observation-functions.h').write_text('\n\n'.join(functions) + '\n')
    (tmp / 'fixture.c').write_text(fixture)
    path = tmp / rel / 'mac.c'
    path.parent.mkdir(parents=True)
    path.write_text(mac)
    patch = repo / 'patches/proposals/0197-wifi-mt6797-retain-terminal-credit-pairing-and-timeout-site.patch'
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=tmp, check=True)
    assert path.read_bytes() == (parent / 'mac.c').read_bytes()
    binary = tmp / 'test'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-I', str(tmp), str(tmp / 'fixture.c'), '-o', str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
print('C7 unchanged timeout gates, HIF/ledger/boot files, RX helper and exact MAC reversal: pass')
