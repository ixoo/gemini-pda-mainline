#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile/run standalone ASan+UBSan synthetic parser checks, then clean up."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="mtke-memory-") as directory:
    binary = Path(directory) / "test-memory"
    subprocess.run([
        "cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wconversion",
        "-pedantic", "-g", "-O1", "-fsanitize=address,undefined",
        "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
        str(HERE / "mtke.c"), str(HERE / "test-memory.c"), "-lz",
        "-o", str(binary),
    ], check=True)
    env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1",
               UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    subprocess.run([str(binary)], env=env, check=True, timeout=60)
