#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual-source fixed-mask comparison, validator, HIF and MAC state; no device."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('parent', type=Path)
ap.add_argument('child', type=Path)
a = ap.parse_args()
f = Path(__file__).resolve().parent
rel = Path('drivers/net/wireless/mediatek/mt6797')
p, c = a.parent.resolve() / rel, a.child.resolve() / rel
pins = {
    'hif.c': '5b499e5bab26811bfabfc5dc23ff02f8632d9cc0fd6ec7480eaeed23e9161a3e',
    'hif.h': '6f24b623ba10f9efeb9db759ba5cd5fe3daeb7feaac717594f61039c74a0d8ce',
    'mac.c': 'ec6f81b87b9a81465c88ba217af6e6ff2b6e9178e1adaaba454107576b77659b',
    'Kconfig': '1a45543422dcb060ffa8aac94d65c93b710796305c653b44d16d2c9d2437a0ab',
    'join-commands.h': 'c8c1d40d5d67d3a3decc4a56f87d108263a56a36fa36bd54093e246a995a9973',
    'join-command-submit.h': '2c2caa5d4aa6d4ce62fb2d3cf785992d663fef128e36a3f5086fd644c5bc7d6d',
}
for n, h in pins.items():
    assert hashlib.sha256((p/n).read_bytes()).hexdigest() == h, n
assert {x.name for x in p.iterdir()} == {x.name for x in c.iterdir()}
for x in p.iterdir():
    if x.is_file() and x.name not in pins:
        assert x.read_bytes() == (c/x.name).read_bytes(), x.name
assert (a.parent/'drivers/soc/mediatek/mt6797-consys.c').read_bytes() == (
    a.child/'drivers/soc/mediatek/mt6797-consys.c').read_bytes()
assert (c/'Kconfig').read_text().startswith((p/'Kconfig').read_text())

with tempfile.TemporaryDirectory(prefix='mt6797-mask-') as d:
    tmp = Path(d)
    reverse = tmp/'reverse'
    shutil.copytree(c, reverse/rel)
    patch = f.parents[2]/'patches/proposals/0200-wifi-mt6797-compare-observed-mask-only-control.patch'
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=reverse,
                   check=True, timeout=30)
    for x in p.iterdir():
        if x.is_file():
            assert x.read_bytes() == (reverse/rel/x.name).read_bytes(), x.name
    compat = f.parents[1]/'2026-10-01-mt6797-normal-sets/tests'
    common = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
              '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        common += ['-fno-pie', '-no-pie']
    flags = ['-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG', '-DCONFIG_MT6797_CCMP_STABLE_EPOCH',
             '-DIS_ENABLED(x)=1']

    def run(driver, on, fixture, label, native=True):
        source = (driver/'mac.c').read_text()
        start = source.index('static void mt6797_native_diag_step(')
        end = source.index('\n}\n', start)+3
        (tmp/'native-step.inc').write_text(source[start:end])
        cmd = common + (flags if native else []) + (['-DCONFIG_MT6797_CCMP_MASK_CONTROL'] if on else [])
        binary = tmp/label
        subprocess.run(cmd + ['-I', str(tmp), '-I', str(compat), '-I', str(driver),
                              str(f/fixture), '-o', str(binary)], check=True, timeout=30)
        r = subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=30)
        print(label+': '+r.stdout.strip())

    for driver, label in [(p, 'parent'), (c, 'child-off')]:
        run(driver, False, 'mask-control-validator-test.c', label+'-validator')
        run(driver, False, 'mask-control-hif-test.c', label+'-hif')
    run(p, False, 'mask-control-validator-test.c', 'parent-normal', native=False)
    run(c, False, 'mask-control-validator-test.c', 'child-normal', native=False)
    run(c, True, 'mask-control-validator-test.c', 'child-on-validator')
    run(c, True, 'mask-control-hif-test.c', 'child-on-hif')

    # Preprocess exact actual HIF and MAC step: disabled option must recover C9.
    before = []
    for driver in (p, c):
        source = (driver/'mac.c').read_text()
        start = source.index('static void mt6797_native_diag_step(')
        end = source.index('\n}\n', start)+3
        (tmp/'native-step.inc').write_text(source[start:end])
        r = subprocess.run(['cc', '-E', '-P', *flags, '-I', str(tmp), '-I', str(compat),
                            '-I', str(driver), str(f/'mask-control-hif-test.c')],
                           check=True, capture_output=True, text=True, timeout=30)
        before.append(r.stdout)
    assert before[0] == before[1], 'disabled-option preprocessed HIF/MAC changed'

    # Extract the actual register-time guards, covering both runtime arm flags.
    for on in (False, True):
        source = (c/'mac.c').read_text()
        start = source.index('#ifdef CONFIG_MT6797_CCMP_STABLE_EPOCH\n\tif (ccmp_stable_epoch && native_delivery_diag)')
        end = source.index('\n\tif (capability->product', start)
        guard = source[start:end]
        (tmp/'guard.c').write_text('#include <assert.h>\n#include <stdbool.h>\n#include <errno.h>\n'
            'static int gate(bool ccmp_stable_epoch, bool native_delivery_diag) {\n'+guard+
            '\nreturn 0; }\nint main(void) { for (int c=0;c<2;c++) for (int n=0;n<2;n++) '
            'assert(gate(c,n)==((c&&n'+('||!c' if on else '')+')?-EINVAL:0)); return 0; }\n')
        binary = tmp/('guard-on' if on else 'guard-off')
        subprocess.run(common+flags+(['-DCONFIG_MT6797_CCMP_MASK_CONTROL'] if on else [])+
                       [str(tmp/'guard.c'), '-o', str(binary)], check=True, timeout=30)
        subprocess.run([str(binary)], check=True, timeout=30)
print('PASS option-off byte equivalence; option-on exact control, refusals and runtime arm gates')
print('Synthetic host ordering only; no firmware group semantics, queued-length or crypto enforcement proof')
