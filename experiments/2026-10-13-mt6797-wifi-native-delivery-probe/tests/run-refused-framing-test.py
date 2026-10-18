#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Two-scalar failure hints on actual C8/child HIF and MAC formatter; no device."""
import argparse
import hashlib
from pathlib import Path
import resource
import runpy
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('parent', type=Path)
parser.add_argument('child', type=Path)
args = parser.parse_args()
fixtures = Path(__file__).resolve().parent
repo = fixtures.parents[2]
rel = Path('drivers/net/wireless/mediatek/mt6797')
parent, child = args.parent.resolve() / rel, args.child.resolve() / rel
pins = {
    'hif.c': '078b08c781d59cfbd624ba1792138013f4f703c9beb019da96c814d7a341851d',
    'hif.h': 'd75a4fbe7d8fdb883d9c5de2be5fcee994cc2bd5355be786c227d100e18ee4a0',
    'mac.c': '2c07e7024e45fc5142d49b6d0b02b3a3ae3b70d3cfb66db32c367c053b77dec1',
}
for name, digest in pins.items():
    assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == digest, name
assert {p.name for p in parent.iterdir()} == {p.name for p in child.iterdir()}
for p in parent.iterdir():
    if p.is_file() and p.name not in pins:
        assert p.read_bytes() == (child / p.name).read_bytes(), p.name
assert (args.parent / 'drivers/soc/mediatek/mt6797-consys.c').read_bytes() == (
    args.child / 'drivers/soc/mediatek/mt6797-consys.c').read_bytes()


def log_block(mac):
    start = mac.index('\t\t\tif (ret == -EPROTO && rx.protocol_refusal')
    end = mac.index('#endif', start)
    return mac[start:end]


old, new = (parent / 'mac.c').read_text(), (child / 'mac.c').read_text()
assert new.replace(log_block(new), log_block(old)) == old, 'MAC changed beyond formatter'


def limit_output():
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))


with tempfile.TemporaryDirectory(prefix='mt6797-framing-hint-') as directory:
    tmp = Path(directory)
    reversed_tree = tmp / 'reversed'
    shutil.copytree(child, reversed_tree / rel)
    patch = repo / 'patches/proposals/0199-wifi-mt6797-retain-refused-descriptor-framing-hints.patch'
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=reversed_tree,
                   check=True, timeout=30)
    for name in pins:
        assert (reversed_tree / rel / name).read_bytes() == (parent / name).read_bytes()

    # Extend the original PIO mock's inputs only; default-zero additions preserve
    # all C8 cases. No hardware FIFO/producer behavior is modeled.
    baseline = (repo / 'experiments/2026-10-01-mt6797-pio-rx/tests/test-pio-rx.c').read_text()
    baseline = baseline.replace('unsigned int post, header_delta;', '''unsigned int post, header_delta, opposite_length;
    unsigned int clocks, expire_clock_at, type_word, header_control, status_flags;
    bool override_fields;''')
    baseline = baseline.replace('u64 ktime_get_ns(void) { return mock.now; }', '''u64 ktime_get_ns(void) {
    if (++mock.clocks == mock.expire_clock_at) mock.now = 1000001000ULL;
    return mock.now;
}''')
    baseline = baseline.replace('*value = mock.port ? mock.logical << 16 : mock.logical;',
        '*value = mock.port ? (mock.logical << 16) | mock.opposite_length :\n'
        '\t\t\tmock.logical | (mock.opposite_length << 16);')
    needle = '\n\t\tword |= value << (byte * 8);'
    assert baseline.count(needle) == 1
    baseline = baseline.replace(needle, '''
        if (mock.override_fields) {
            if (pos == 2) value = mock.type_word & 255;
            if (pos == 3) value = mock.type_word >> 8;
            if (pos == 6) value = mock.header_control;
            if (pos == 10) value = mock.status_flags & 255;
            if (pos == 11) value = mock.status_flags >> 8;
        }
''' + needle)
    (tmp / 'selected-pio-baseline.inc').write_text(baseline)
    c8 = (fixtures / 'closed-selected-hif-test.c').read_text()
    assert c8.count('int main(void)') == 1
    (tmp / 'c8-selected-baseline.inc').write_text(
        c8.replace('int main(void)', 'int selected_baseline_main(void)'))

    def run(fixture, driver, label, flags=()):
        binary = tmp / label
        command = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
                   '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        if sys.platform.startswith('linux'):
            command += ['-fno-pie', '-no-pie']
        command += ['-I', str(tmp), '-I', str(driver), '-I', str(fixtures), '-I',
                    str(repo / 'experiments/2026-10-01-mt6797-normal-sets/tests'),
                    *flags, str(fixtures / fixture), '-o', str(binary)]
        subprocess.run(command, check=True, timeout=30)
        output, errors = tmp / (label + '.stdout'), tmp / (label + '.stderr')
        with output.open('wb') as stdout, errors.open('wb') as stderr:
            result = subprocess.run([str(binary)], stdout=stdout, stderr=stderr,
                                    preexec_fn=limit_output, timeout=30)
        if result.returncode:
            raise RuntimeError(f'{label} exit={result.returncode}: '
                               + errors.read_bytes()[-8192:].decode(errors='replace'))
        return output.read_text(), errors.read_bytes()

    flags = ['-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG', '-DIS_ENABLED(x)=1', '-DRUNTIME_CHILD']
    before, _ = run('runtime-no-post-hif-test.c', parent, 'legacy-parent', flags)
    after, _ = run('runtime-no-post-hif-test.c', child, 'legacy-child', flags)
    assert before == after
    tables = {}
    for label, driver, mac in (('parent', parent, old), ('child', child, new)):
        (tmp / 'framing-log.inc').write_text(
            'static void logged_refusal(int ret, unsigned int rx_port, '
            'const struct mt6797_hif_rx_result *rp) {\n'
            'struct mt6797_hif_rx_result rx = *rp;\n' + log_block(mac) + '}\n')
        extra = [*flags, '-DFRAMING_CHILD'] if label == 'child' else flags
        tables[label], errors = run('refused-framing-hif-test.c', driver, label, extra)
        if label == 'child':
            hint = errors
    assert tables['parent'] == tables['child'], 'I/O/guard/publication table changed'
    assert hint.count(b'one-shot WLAN native HIF framing hint:') == 1
    output_lines = tables['child'].splitlines()
    assert output_lines[0] == 'bounded PIO RX: pass'
    assert output_lines[1].startswith('selected runtime:')
    rows = output_lines[2:]
    assert all(len(row.split()) == 16 for row in rows)
    faults = sum(int(row.split()[8]) != 0 for row in rows)
    print(f'actual HIF/formatter PASS: {len(rows)} paired rows, {faults} injected faults')
    print('C8 legacy/selected tables unchanged; five mismatch pairs, both ports, 3 APIs')
    print('PASS raw/zero/absent fields, class and full-base bounds, completed-read deadline, no-copy/poison/no-second-I/O')
    # Reuse the existing complete CCMP host/classifier fixtures; only the actual
    # new formatter output is added. It cannot manufacture either pass or fault.
    suite = runpy.run_path(str(fixtures / 'ccmp-runtime-test.py'))
    classify = suite['C']
    for payload in (suite['kmsg'], b'', suite['kmsg'] + b'one-shot WLAN join stopped: status=-71\n'):
        args4 = (suite['receipt'], suite['boot'], suite['complete_protocol'])
        assert classify(payload, *args4) == classify(payload + b'\n' + hint, *args4)
print('PASS exact patch reversal, unchanged MAC gates/other files and classifier verdicts')
print('ASan/UBSan; untrusted hints only, no firmware conversion or hardware enforcement proved')
