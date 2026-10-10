#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile and run the observer core fixture against lifecycle/gwref10.c (host only)."""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='gwref10-test-') as tmp:
    binary = pathlib.Path(tmp) / 'gwref10-test'
    subprocess.run(['cc', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror', '-pthread',
                    '-I', str(HERE), '-o', str(binary), str(HERE / 'gwref10-test.c')], check=True)
    sys.exit(subprocess.run([str(binary)]).returncode)
