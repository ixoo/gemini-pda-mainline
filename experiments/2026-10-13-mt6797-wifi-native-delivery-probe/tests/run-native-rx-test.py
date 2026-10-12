#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the strict native (encrypted) RXD decoder (proposal 0181) with sanitizers."""
from pathlib import Path
import argparse, subprocess, tempfile
parser = argparse.ArgumentParser(); parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
if not (driver / "data-rx.h").is_file():
    parser.error("apply the Phase B series + proposal 0181 first")
fixture = Path(__file__).with_name("native-rx-test.c")
with tempfile.TemporaryDirectory(prefix="mt6797-native-rx-") as d:
    b = Path(d) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(driver), str(fixture), "-o", str(b)],
                   check=True, timeout=30)
    subprocess.run([str(b)], check=True, timeout=30)
print("native-rx decoder: PASS (ASan/UBSan; synthetic only)")
