#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual PMIC IRQ initializers against a bounded devres model."""

import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path, help='prepared Linux source directory')
args = parser.parse_args()
legacy = (args.source / 'drivers/mfd/mt6397-irq.c').read_text()
modern = (args.source / 'drivers/mfd/mt6358-irq.c').read_text()


def function(source, declaration):
    start = source.index(declaration)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


functions = ''.join([
    function(legacy, 'void mt6397_irq_domain_exit('),
    function(legacy, 'static void mt6397_irq_unregister_pm_notifier('),
    function(legacy, 'int mt6397_irq_init('),
    function(modern, 'static void mt6358_irq_disable_wake('),
    function(modern, 'int mt6358_irq_init('),
])
tokens = sorted(set(re.findall(r'\bMT\d+_(?:CHIP_ID|INT_[A-Z0-9_]+|IRQ_NR)\b', functions)))
defines = []
for index, token in enumerate(tokens):
    if token.endswith('CHIP_ID'):
        value = int(re.match(r'MT(\d+)', token)[1][-2:], 16)
    elif token.endswith('IRQ_NR'):
        value = {'MT6328_IRQ_NR': 47, 'MT6351_IRQ_NR': 64, 'MT6397_IRQ_NR': 32}[token]
    else:
        value = 0x100 + index * 2
    defines.append(f'#define {token} {value}\n')

fixture = Path(__file__).with_suffix('.c').read_text()
prefix, tests = fixture.split('/* ACTUAL SOURCE FUNCTIONS */')
with tempfile.TemporaryDirectory(prefix='mt6351-irq-lifetime-') as directory:
    root = Path(directory)
    (root / 'test.c').write_text(''.join(defines) + prefix + functions + tests)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', str(root / 'test.c'),
                    '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True)
