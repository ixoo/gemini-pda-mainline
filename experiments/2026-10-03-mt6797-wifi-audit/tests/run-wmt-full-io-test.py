#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile the actual full-STP IRQ draft against bounded host MMIO/IRQ fixtures."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="gemini-wmt-full-") as temporary:
    work = Path(temporary)
    includes = work / "linux"
    includes.mkdir()
    for name in ("clk", "completion", "interrupt", "io", "jiffies", "spinlock", "string"):
        (includes / f"{name}.h").write_text("")
    # glibc's errno.h itself includes linux/errno.h; preserve its definitions.
    (includes / "errno.h").write_text(
        "#ifdef __linux__\n#include_next <linux/errno.h>\n#endif\n"
    )
    binary = work / "transport-test"
    subprocess.run([
        os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-fsanitize=address,undefined", f"-I{work}",
        str(root / "wmt-full-io-test.c"), "-o", str(binary),
    ], check=True)
    subprocess.run([str(binary)], check=True)
