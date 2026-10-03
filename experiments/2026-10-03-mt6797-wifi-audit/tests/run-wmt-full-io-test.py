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
    for name in ("clk", "completion", "interrupt", "io", "jiffies", "spinlock", "string", "delay"):
        (includes / f"{name}.h").write_text("")
    # glibc's errno.h itself includes linux/errno.h; preserve its definitions.
    (includes / "errno.h").write_text(
        "#ifdef __linux__\n#include_next <linux/errno.h>\n#endif\n"
    )
    for fixture in ("wmt-full-io-test.c", "wmt-negotiate-test.c", "wmt-identity-io-test.c"):
        binary = work / fixture.removesuffix(".c")
        subprocess.run([
            os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
            "-fsanitize=address,undefined", f"-I{work}",
            str(root / fixture), "-o", str(binary),
        ], check=True)
        subprocess.run([str(binary)], check=True)
