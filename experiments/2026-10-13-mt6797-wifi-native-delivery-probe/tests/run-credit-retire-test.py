#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the credit-retire proposal's headers (descriptor without a report; slots retired in order) without hardware."""
from pathlib import Path
import argparse, subprocess, tempfile
parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
parser.add_argument("--compat", type=Path, default=None)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
if "mt6797_data_take_oldest" not in (driver / "join-depth.h").read_text():
    parser.error("apply the credit-retire proposal first")
here = Path(__file__).resolve().parent
compat = args.compat or here.parents[1] / "2026-10-01-mt6797-normal-sets/tests"
with tempfile.TemporaryDirectory(prefix="mt6797-credit-retire-") as directory:
    binary = Path(directory) / "test"
    for depth in ("1", "4"):
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-DIS_ENABLED(x)=0",
                        "-DCONFIG_MT6797_CCMP_TX_DEPTH=" + depth, "-fsanitize=address,undefined",
                        "-fno-pie", "-no-pie", "-I", str(compat), "-I", str(driver),
                        str(here / "credit-retire-test.c"), "-o", str(binary)], check=True)
        if depth == "4":
            subprocess.run([str(binary)], check=True, timeout=10)
print("credit-retire fixtures: PASS (depth 4 run; depth 1 compiled; ASan/UBSan, non-PIE)")
