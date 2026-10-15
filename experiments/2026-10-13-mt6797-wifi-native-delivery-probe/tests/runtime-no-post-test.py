#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compare actual C4 and runtime-no-post HIF; synthetic transport, no hardware."""
import argparse
import ast
import hashlib
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('parent', type=Path)
parser.add_argument('child', type=Path)
parser.add_argument('prepared_c4', type=Path)
args = parser.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
parent, child = args.parent / rel, args.child / rel
fixtures = Path(__file__).resolve().parent
repo = fixtures.parents[2]
pins = {
    'hif.c': 'cfe0e11348fefecad039a605402a9b93ab70c312cf91ccf12e2e7d521f292f76',
    'hif.h': '68c2a2428c44db91b8a76e6f238f84b9f1dbf72ddf0951291a628fbc2f7238da',
    'mac.c': 'e3ee7a910491673b8b61d444199622120c1a4ce33623b28d267372e680bf11ba',
}
for name, pin in pins.items():
    assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == pin, name
    assert (parent / name).read_bytes() == (args.prepared_c4 / rel / name).read_bytes()
old = {p.name: p.read_text() for p in parent.iterdir() if p.is_file()}
new = {p.name: p.read_text() for p in child.iterdir() if p.is_file()}
assert old.keys() == new.keys()
for name in old.keys() - {'hif.c', 'hif.h', 'mac.c'}:
    assert old[name] == new[name], name
assert new['mac.c'].count('mt6797_hif_receive_runtime_packet(') == 2
restored_mac = new['mac.c'].replace('mt6797_hif_receive_runtime_packet(',
                                  'mt6797_hif_receive_packet(')
restored_mac = restored_mac.replace(
    '\t' * 8 + 'mac->join_packet,\n' + '\t' * 8 + 'sizeof(mac->join_packet), &rx);',
    '\t' * 4 + ' mac->join_packet, sizeof(mac->join_packet), &rx);')
restored_mac = restored_mac.replace('\t' * 8 + 'mac->scan_packet,',
                                    '\t' * 7 + 'mac->scan_packet,').replace(
    '\t' * 8 + 'sizeof(mac->scan_packet), &rx);',
    '\t' * 7 + 'sizeof(mac->scan_packet), &rx);')
assert restored_mac == old['mac.c']
# Only the refusal formatter mentions post fields in MAC. It runs on failures,
# whose acquisition order is unchanged; no success-path post metadata consumer.
assert old['mac.c'].count('rx.post_valid') == old['mac.c'].count('rx.post_wrplr') == 1
begin = new['hif.h'].index('/* MAC runtime comparison:')
assert new['hif.h'][:begin] + '#endif\n' == old['hif.h']
helper = new['hif.c'].split('\nint mt6797_hif_receive_packet(')[0]
helper = helper.replace(
    'static int mt6797_hif_receive(struct mt6797_hif *hif, unsigned int port,\n'
    '\t\t\t      u64 deadline_ns, u8 *buffer, size_t capacity,\n'
    '\t\t\t      struct mt6797_hif_rx_result *result, bool post_read)',
    'int mt6797_hif_receive_packet(struct mt6797_hif *hif, unsigned int port,\n'
    '\t\t\t      u64 deadline_ns, u8 *buffer, size_t capacity,\n'
    '\t\t\t      struct mt6797_hif_rx_result *result)')
block = ('\terror = mt6797_hif_read32_locked(hif, 0x90, &lengths);\n'
         '\tif (error)\n\t\tgoto poison;\n'
         '\tresult->post_valid = true;\n\tresult->post_wrplr = lengths;\n')
conditional = '\tif (post_read) {\n' + ''.join('\t' + s for s in block.splitlines(True)) + '\t}\n'
assert helper.replace(conditional, block).rstrip() + '\n' == old['hif.c']
assert new['hif.c'].count('result, true);') == 1
assert new['hif.c'].count('result, false);') == 1
consys = args.prepared_c4 / 'drivers/soc/mediatek/mt6797-consys.c'
assert hashlib.sha256(consys.read_bytes()).hexdigest() == (
    '76e114641b11c2e0ff5ca72be7b36cadbbe51dec1f92a2abd6b45268deab8053')
boot = consys.read_text()
assert 'mt6797_hif_receive_runtime_packet' not in boot
assert boot.count('mt6797_hif_receive_packet(') == 1
assert 'last = rx.post_wrplr;' in boot
assert 'if (!last)\n\t\t\tbreak;' in boot
assert 'if (last >> 16)' in boot

# Use the existing actual-source compiler, not a second transport implementation.
source = fixtures / 'run-native-metadata-test.py'
tree = ast.parse(source.read_text())
definitions = [n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == 'run']
namespace = {'fixtures': fixtures, 'repo': repo, 'subprocess': subprocess}
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(source), 'exec'), namespace)
with tempfile.TemporaryDirectory(prefix='runtime-no-post-', dir='/tmp/opencode') as directory:
    namespace.update(tmp=Path(directory), errors={})
    tables = {}
    for label, driver in (('parent', parent), ('child', child)):
        flags = ['-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG', '-DIS_ENABLED(x)=1']
        if label == 'child':
            flags.append('-DRUNTIME_CHILD')
        text = namespace['run']('runtime-no-post-hif-test.c', driver, label, flags)
        assert text.splitlines()[0] == 'bounded PIO RX: pass'
        rows = [list(map(int, line.split())) for line in text.splitlines()[1:]]
        tables[label] = {tuple(row[:6]): row[6:] for row in rows}
        assert len(tables[label]) == len(rows)
    omitted = 0
    successes = failures = 0
    for key, value in tables['parent'].items():
        mode, port, length, capacity, delta, fail = key
        actual = tables['child'].get(key)
        if mode and fail and actual is None:
            # Only the two deleted post-read operations are now unreachable.
            success = tables['parent'][(mode, port, length, capacity, delta, 0)]
            assert fail in (success[1] - 1, success[1])
            omitted += 1
            continue
        assert actual is not None
        expected = value.copy()
        if mode and value[0] == 0:
            expected[1] -= 2
            expected[5] = 0  # post_valid, unread rather than measured empty
            successes += 1
        elif mode:
            failures += 1
        assert actual == expected, (key, value, actual)
    assert tables['child'].keys() <= tables['parent'].keys()
    assert omitted == 20 and successes == 10
    print(f'PASS boot API/table unchanged; runtime successes={successes}, common failures={failures}')
    print('PASS exactly two fewer transport operations on runtime success (one logical register acquisition)')
    print('PASS both ports, every reachable I/O fault, equality/refusal hint, no-copy/poison/no-second-I/O')
    print('PASS exact delta reversal; both MAC calls only; unchanged boot drain post-metadata dependency')
    print('ASan/UBSan; synthetic only: no queue-advance semantics or hardware support proved')
