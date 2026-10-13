#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual stop/close/regulatory caller fence with host shims; no device."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('kernel_tree', type=Path)
parser.add_argument('--mac-source', type=Path)
args = parser.parse_args()
driver = args.kernel_tree / 'drivers/net/wireless/mediatek/mt6797'
source = (args.mac_source or driver / 'mac.c').read_text()
parts = []
for name in ('mt6797_mac_send', 'mt6797_mac_domains',
             'mt6797_mac_join_regulatory_stop', 'mt6797_mac_regulatory',
             'mt6797_mac_join_close', 'mt6797_mac_stop'):
    match = re.search(r'static (?:int|void|bool) ' + name + r'\([^;]*?\)\n\{.*?\n\}',
                      source, re.S)
    if not match:
        parser.error('missing actual caller: ' + name)
    parts.append(match.group(0))
with tempfile.TemporaryDirectory(prefix='mt6797-regulatory-close-') as directory:
    output = Path(directory)
    (output / 'regulatory-functions.h').write_text('\n'.join(parts))
    binary = output / 'test'
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', '-fno-pie', '-no-pie',
                    '-I', str(output), str(Path(__file__).with_name('regulatory-close-test.c')),
                    '-o', str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
print('actual stop/close/regulatory fence: PASS (host shims, no kernel concurrency/firmware claim)')
