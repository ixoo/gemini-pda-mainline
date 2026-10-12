#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile and run the native command-validator test against a kernel tree, BOTH with
and without CONFIG_MT6797_NATIVE_DELIVERY_DIAG, so the 0xFC admission and the
normal-build refusal (boundary) are both exercised -- the validator path ND1 hit."""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
if not (driver / "join-command-submit.h").is_file():
    parser.error("missing join-command-submit.h in the kernel tree")
fixture = Path(__file__).with_name("native-command-validator-test.c")
for extra in ([], ["-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG"]):
    with tempfile.TemporaryDirectory(prefix="mt6797-native-cmd-") as d:
        binary = Path(d) / "test"
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        "-fno-pie", "-no-pie", *extra, "-I", str(driver),
                        str(fixture), "-o", str(binary)], check=True, timeout=30)
        subprocess.run([str(binary)], check=True, timeout=30)
print("native-command-validator: PASS (both CONFIG states)")
