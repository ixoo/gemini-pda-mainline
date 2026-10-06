#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the production WMT full-STP I/O header, including no-source IRQs."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
soc = args.kernel_tree.resolve() / "drivers/soc/mediatek"
with tempfile.TemporaryDirectory(prefix="mt6797-wmt-irq-") as directory:
    work = Path(directory)
    shim = work / "linux"
    shim.mkdir()
    # The test file supplies the kernel definitions; these headers stay empty,
    # except errno, which must still reach the libc definitions.
    for name in ("completion", "interrupt", "io", "jiffies", "spinlock", "string"):
        (shim / (name + ".h")).write_text("")
    (shim / "errno.h").write_text("#include_next <linux/errno.h>\n")
    binary = work / "wmt-irq-test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                    "-I", str(work), "-I", str(soc),
                    str(Path(__file__).with_name("wmt-full-irq-test.c")),
                    "-o", str(binary)], check=True)
    subprocess.run(["setarch", subprocess.check_output(["uname", "-m"], text=True).strip(),
                    "-R", str(binary)], check=True, timeout=60)
print("WMT full I/O: PASS (production header, ASan/UBSan; no-source IRQ cases)")
