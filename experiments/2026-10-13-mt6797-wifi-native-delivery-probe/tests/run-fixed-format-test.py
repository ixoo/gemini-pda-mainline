#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual-source fixed-format initialization, local window and option-off parity."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument('parent', type=Path)
p.add_argument('child', type=Path)
a = p.parse_args()
f = Path(__file__).resolve().parent
rel = Path('drivers/net/wireless/mediatek/mt6797')
parent, child = a.parent.resolve() / rel, a.child.resolve() / rel
pins = {'Kconfig': '61d2498088e43cd1496344b6f2d80a1117cda5cb66859113521ca189190a069a', 'normal_command.h': '483b579060c33c6ef7c53e2d2c41dd7e592908b69f9b7ac15aebd4e267f79a46', 'hif.c': '1d5b6b636a027536ef7115b03cf25a96ce1da5fb36b644876e26310037c0ad3f', 'hif.h': 'ee16fbc5557bb217403ffb718036020846c6c2420eb067a5e08572c563aca913', 'mac.c': '9c436a627a5b23a416b9fc2a1401f349a10e971af4086464117bc6d50890ef88', 'mac.h': '3d92a29c93ebe80be3452aaec5fe19744344f20554fed15863dea5ea9f23c36d', 'native-diag.h': '905b6763ac1a15cbdca1ef0643db70585dfa443d2fdd36af223b349d157ccae0'}
for name, digest in pins.items():
    assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == digest, name
changed = {'Kconfig', 'normal_command.h', 'join-command-submit.h', 'hif.c', 'hif.h', 'mac.c', 'mac.h', 'native-diag.h'}
assert {x.name for x in parent.iterdir()} == {x.name for x in child.iterdir()}
for path in parent.iterdir():
    if path.is_file() and path.name not in changed:
        assert path.read_bytes() == (child / path.name).read_bytes(), path.name
for header in ['ccmp-rx.h', 'eapol-rx.h', 'data-rx.h', 'group-data.h']:
    assert (parent / header).read_bytes() == (child / header).read_bytes()


def function(source, signature):
    start = source.index(signature)
    end = source.index('\n}\n', start) + 3
    return source[start:end]


mac = (child / 'mac.c').read_text()
assert function((parent / 'hif.c').read_text(), 'static int mt6797_hif_receive(') == function((child / 'hif.c').read_text(), 'static int mt6797_hif_receive(')
assert function((parent / 'mac.c').read_text(), 'static int mt6797_mac_join_release_channel(') == function(mac, 'static int mt6797_mac_join_release_channel(')

marker = '/* Preserve the strict directed management path without'
def fallback(text):
    start = text.index(marker)
    return text[start:text.index('#endif', start)]
assert fallback(mac) == fallback((parent / 'mac.c').read_text())

work = function(mac, 'static void mt6797_mac_join_work(')
assert work.index('mt6797_native_diag_step(mac)') < work.index('if (mac->first_error || mac->closing)') < work.index('select =')
consys = (a.child / 'drivers/soc/mediatek/mt6797-consys.c').read_text()
anchor = consys.index('ret = mt6797_consys_observe_tx_status(dev, owner, true);')
window = consys[anchor:consys.index('return;', anchor)]
assert window.index('mt6797_mac_prepare_rx_format') < window.index('rtnl_unlock()') < window.index('mt6797_mac_scan_ready')

with tempfile.TemporaryDirectory(prefix='mt6797-fixed-format-') as directory:
    tmp = Path(directory)
    reversed_source = tmp / 'reversed'
    shutil.copytree(child, reversed_source / rel)
    soc = Path('drivers/soc/mediatek/mt6797-consys.c')
    (reversed_source / soc).parent.mkdir(parents=True)
    shutil.copyfile(a.child / soc, reversed_source / soc)
    patch = f.parents[2] / 'patches/proposals/0202-wifi-mt6797-compare-firmware-lifetime-fixed-RX-format.patch'
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=reversed_source,
                   check=True, timeout=30)
    for path in parent.iterdir():
        if path.is_file():
            assert path.read_bytes() == (reversed_source / rel / path.name).read_bytes(), path.name
    assert (a.parent / soc).read_bytes() == (reversed_source / soc).read_bytes()
    compat = f.parents[1] / '2026-10-01-mt6797-normal-sets/tests'
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    options = ['-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG', '-DCONFIG_MT6797_CCMP_STABLE_EPOCH',
               '-DCONFIG_MT6797_CCMP_MASK_CONTROL', '-DIS_ENABLED(x)=1']
    include = ['-I', str(tmp), '-I', str(compat)]
    limit = next(line for line in mac.splitlines() if line.startswith('#define MT6797_JOIN_DATA_LAST_PID '))
    start = mac.index('\t\t\tif (ret == -EPROTO && rx.protocol_refusal', mac.index('static void mt6797_mac_scan_work('))
    end = mac.index('\n#endif', start)
    scan_log = 'static void scan_refusal(int ret, unsigned int port, struct mt6797_hif_rx_result rx) {\n' + mac[start:end] + '\n}\n'
    (tmp / 'fixed-mac.inc').write_text(limit + '\n' + '\n'.join(function(mac, s) for s in [
        'static void mt6797_native_diag_step(', 'int mt6797_mac_prepare_rx_format(',
        'void mt6797_mac_scan_ready(', 'static bool mt6797_native_diag_tx_fenced(']) + '\n' + scan_log)
    binary = tmp / 'fixed'
    subprocess.run(['cc', *flags, *options, '-DCONFIG_MT6797_CCMP_FIXED_RX_FORMAT',
                    *include, '-I', str(child), str(f / 'fixed-format-test.c'), '-o', str(binary)],
                   check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)

    before = []
    for source, label in [(parent, 'parent'), (child, 'off')]:
        text = (source / 'mac.c').read_text()
        (tmp / 'native-step.inc').write_text(function(text, 'static void mt6797_native_diag_step('))
        command = ['cc', *flags, *options, *include, '-I', str(source), str(f / 'mask-control-hif-test.c')]
        target = tmp / label
        subprocess.run([*command, '-o', str(target)], check=True, timeout=30)
        subprocess.run([str(target)], check=True, timeout=30)
        result = subprocess.run(['cc', '-E', '-P', *options, *include, '-I', str(source),
                                 str(f / 'mask-control-hif-test.c')], check=True, capture_output=True, text=True, timeout=30)
        before.append(result.stdout)
    assert before[0] == before[1], 'option-off HIF/MAC tokens or formatting changed'

    # Same real receive fixtures and all observed pairs, under the new option.
    baseline_path = f.parents[1] / '2026-10-01-mt6797-pio-rx/tests/test-pio-rx.c'
    baseline = baseline_path.read_text().replace('unsigned int post, header_delta;',
                                               'unsigned int post, header_delta, opposite_length;')
    baseline = baseline.replace('*value = mock.port ? mock.logical << 16 : mock.logical;',
        '*value = mock.port ? (mock.logical << 16) | mock.opposite_length : '
        'mock.logical | (mock.opposite_length << 16);')
    (tmp / 'selected-pio-baseline.inc').write_text(baseline)
    selected = (f / 'closed-selected-hif-test.c').read_text()
    assert selected.count('{427, 379} }') == 1
    selected = selected.replace('{427, 379} }', '{427, 379}, {88, 40}, {94, 142} }')
    selected = selected.replace('four mismatch pairs', 'six mismatch pairs')
    selected = selected.replace('{ 4, 76, 80, 427, 449, 2352 }',
                                '{ 4, 76, 80, 94, 427, 449, 2352 }')
    (tmp / 'selected.c').write_text(selected)
    runtime = (f / 'runtime-no-post-hif-test.c').read_text()
    runtime = runtime.replace('"../../2026-10-01-mt6797-pio-rx/tests/test-pio-rx.c"',
                              '"' + str(baseline_path) + '"')
    runtime = runtime.replace('{ 4, 76, 80, 449, 2352 }',
                              '{ 4, 76, 80, 88, 94, 427, 449, 2352 }')
    needle = '\t\t\ttrial(mode, port, 449, 2352, (unsigned int)-48, 0);'
    assert runtime.count(needle) == 1
    runtime = runtime.replace(needle, needle +
        '\n\t\t\ttrial(mode, port, 88, 2352, (unsigned int)-48, 0);' +
        '\n\t\t\ttrial(mode, port, 427, 2352, (unsigned int)-48, 0);' +
        '\n\t\t\ttrial(mode, port, 94, 2352, 48, 0);')
    (tmp / 'runtime.c').write_text(runtime)
    for name in ['selected', 'runtime']:
        tables = []
        for source, fixed in [(parent, False), (child, True)]:
            target = tmp / (name + ('-fixed' if fixed else '-parent'))
            subprocess.run(['cc', *flags, *options, '-DRUNTIME_CHILD',
                *(['-DCONFIG_MT6797_CCMP_FIXED_RX_FORMAT'] if fixed else []),
                *include, '-I', str(source), str(tmp / (name + '.c')), '-o', str(target)],
                check=True, timeout=30)
            result = subprocess.run([str(target)], check=True, capture_output=True, timeout=30)
            tables.append(result.stdout)
        assert tables[0] == tables[1], name + ' receive I/O/publication table changed'
        print(name + ': same actual receive I/O, all six mismatches, poison/no-copy')

print('PASS fixed-format actual source; option-off byte-equivalent HIF/MAC preprocessing')
print('Host behavior only; no firmware application, queue fence, integrity or key retirement proof')
