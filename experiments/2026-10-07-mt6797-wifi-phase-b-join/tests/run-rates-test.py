#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check 5 GHz rate normalization against the actual prepared driver header."""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
if "mt6797_join_legacy_rates(" not in (driver / "join-commands.h").read_text():
    parser.error("apply the station rate translation patch first")
fixture = Path(__file__).with_name("join-rates-test.c")
with tempfile.TemporaryDirectory(prefix="mt6797-join-rates-") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-pie", "-no-pie",
                    "-I", str(driver), str(fixture), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
print("Rate normalization: PASS (65536 bitmap pairs, high bits, ASan/UBSan)")
