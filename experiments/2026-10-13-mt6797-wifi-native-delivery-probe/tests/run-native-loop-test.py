#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the native-crypto-delivery control-loop event order (proposal 0181) with sanitizers."""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
if not (driver / "native-diag.h").is_file():
    parser.error("apply proposal 0181 on the 0180 parent first (missing native-diag.h)")
fixture = Path(__file__).with_name("native-loop-test.c")
with tempfile.TemporaryDirectory(prefix="mt6797-native-loop-") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(driver), str(fixture),
                    "-o", str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
print("native-loop control-order: PASS (ASan/UBSan; synthetic only)")
