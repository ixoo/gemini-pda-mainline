#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run actual snapshot.c file operations with pthread kernel-service shims.

Not a mounted debugfs/VFS test: capability, uaccess, allocator, timer and debugfs
registration are simulated. Mutexes, refs, completion waits and reader signals
run concurrently. No firmware or device access.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
a = p.parse_args()
d = a.source / 'drivers/net/wireless/mediatek/mt6797'
source = (d / 'snapshot.c').read_text()
source = '\n'.join(x for x in source.splitlines() if not x.startswith('#include'))
shim = Path(__file__).with_name('snapshot-fops-stress.c').read_text()
with tempfile.TemporaryDirectory(prefix='snapshot-fops-') as tmp:
    tmp = Path(tmp)
    (tmp / 'test.c').write_text(shim.replace('/* ACTUAL_SNAPSHOT_SOURCE */', source))
    subprocess.run(['cc', '-std=gnu11', '-pthread', '-g', '-Wall', '-Wextra',
                    '-Wno-unused-parameter', '-Wno-format',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-fno-pie', '-no-pie', '-I', str(d),
                    str(tmp / 'test.c'), '-o', str(tmp / 'test')], check=True)
    subprocess.run([str(tmp / 'test')], check=True, timeout=30)
