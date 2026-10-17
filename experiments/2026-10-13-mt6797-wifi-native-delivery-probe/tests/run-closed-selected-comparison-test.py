#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual-source post-CLOSED selection comparison; no hardware/FIFO-pop model."""
import argparse
import hashlib
from pathlib import Path
import resource
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
    'hif.c': '904ee916416359987b6168a6d84a8fbf155fcfabc599a1789609dbd130d83790',
    'hif.h': '55cea74081c83b41221b72246494a42548d4f30857fbe9def9116597ed4ebe11',
    'mac.c': '7faea3f09d29144e8cedd2b12558cfead70c7d4cd6a85916bb570e86624ef4e8',
}
for name, digest in pins.items():
    assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == digest, name
assert {p.name for p in parent.iterdir()} == {p.name for p in child.iterdir()}
for p in parent.iterdir():
    if p.is_file() and p.name not in pins:
        assert p.read_bytes() == (child / p.name).read_bytes(), p.name
assert (args.parent / 'drivers/soc/mediatek/mt6797-consys.c').read_bytes() == (
    args.child / 'drivers/soc/mediatek/mt6797-consys.c').read_bytes()
old, mac = (parent / 'mac.c').read_text(), (child / 'mac.c').read_text()
start = mac.index('\t\t\tbranch = 4;\n')
end = mac.index('#ifdef CONFIG_MT6797_NATIVE_DELIVERY_DIAG\n\t\t\tif (ret == -EPROTO', start)
route = mac[start:end]
a = old.index('\t\t\tbranch = 4;\n')
b = old.index('#ifdef CONFIG_MT6797_NATIVE_DELIVERY_DIAG\n\t\t\tif (ret == -EPROTO', a)
restored = mac[:start] + old[a:b] + mac[end:]
restored = restored.replace('\t\t\tunsigned int rx_port __maybe_unused = port;\n\n', '')
restored = restored.replace('"header-length", rx_port, rx.pre_valid,',
                            '"header-length", port, rx.pre_valid,')
assert restored == old, 'MAC delta beyond the routing/actual-port reporting block'
marker = 'static void mt6797_mac_scan_work('
assert mac[mac.index(marker):] == old[old.index(marker):], 'scan changed'
assert 'ccmp_stable_epoch && mac->native_diag_engaged &&' in route
assert 'mac->native_diag_state == MT6797_ND_CLOSED' in route
assert 'if (port)\n\t\t\t\t\tbreak;' in route


def limit_output():
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))


with tempfile.TemporaryDirectory(prefix='mt6797-closed-select-') as directory:
    tmp = Path(directory)
    reversed_tree = tmp / 'reversed'
    shutil.copytree(child, reversed_tree / rel)
    patch = repo / 'patches/proposals/0198-wifi-mt6797-compare-post-CLOSED-RX-port-selection.patch'
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=reversed_tree,
                   check=True, timeout=30)
    for name in pins:
        assert (reversed_tree / rel / name).read_bytes() == (parent / name).read_bytes()

    # Reuse the original finite PIO mock. The ONLY extension is an independent
    # advertised opposite halfword; zero preserves every original baseline case.
    baseline = (repo / 'experiments/2026-10-01-mt6797-pio-rx/tests/test-pio-rx.c').read_text()
    needle = 'unsigned int post, header_delta;'
    assert baseline.count(needle) == 1
    baseline = baseline.replace(needle, 'unsigned int post, header_delta, opposite_length;')
    needle = '*value = mock.port ? mock.logical << 16 : mock.logical;'
    assert baseline.count(needle) == 1
    baseline = baseline.replace(needle,
        '*value = mock.port ? (mock.logical << 16) | mock.opposite_length :\n'
        '\t\t\tmock.logical | (mock.opposite_length << 16);')
    (tmp / 'selected-pio-baseline.inc').write_text(baseline)
    (tmp / 'closed-selected-route.inc').write_text(route)

    def run(fixture, driver, label, flags=()):
        binary = tmp / label
        command = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
                   '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        if sys.platform.startswith('linux'):
            command += ['-fno-pie', '-no-pie']
        command += ['-I', str(tmp), '-I', str(driver), '-I',
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
        return output.read_text()

    flags = ['-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG', '-DIS_ENABLED(x)=1', '-DRUNTIME_CHILD']
    before = run('runtime-no-post-hif-test.c', parent, 'legacy-parent', flags)
    after = run('runtime-no-post-hif-test.c', child, 'legacy-child', flags)
    assert before == after, 'legacy boot/requested-port transport/publication changed'
    print('legacy boot/requested-runtime tables byte-identical to C7 (ASan/UBSan)')
    print(run('closed-selected-hif-test.c', child, 'selected', flags), end='')
    print(run('closed-selected-routing-test.c', child, 'routing-on',
              ['-DCONFIG_MT6797_CCMP_STABLE_EPOCH']), end='')
    print(run('closed-selected-routing-test.c', child, 'routing-off'), end='')
print('PASS exact patch reversal, unchanged scan/boot/other files and MAC gates')
print('Synthetic host selection/ordering only; no firmware FIFO advance or causal repair proved')
