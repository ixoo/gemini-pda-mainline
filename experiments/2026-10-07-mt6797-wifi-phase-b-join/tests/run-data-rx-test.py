#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the protected translated data receive decoder (Phase C3) on a Buildbox with sanitizers."""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
if not (driver / "data-rx.h").is_file():
    parser.error("apply proposal 0166 after the Phase B series first")
fixture = Path(__file__).with_name("data-rx-test.c")
with tempfile.TemporaryDirectory(prefix="mt6797-data-rx-") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(driver), str(fixture),
                    "-o", str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
print("Data RX decoder: PASS (ASan/UBSan; synthetic frames only, no reference bytes)")
