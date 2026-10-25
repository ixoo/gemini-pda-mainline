#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the data descriptor's rate code and the receive-vector word (0271, 0273), at the default and at a profile's value without hardware."""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
parser.add_argument("--compat", type=Path, default=None,
                    help="directory holding test-compat.h (default: the normal-sets tests)")
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
source = (driver / "join-tx.h").read_text()
if "MT6797_DATA_FIXED_RATE_CODE" not in source:
    parser.error("apply the rate-code proposal first")
here = Path(__file__).resolve().parent
compat = args.compat or here.parents[1] / "2026-10-01-mt6797-normal-sets/tests"
with tempfile.TemporaryDirectory(prefix="mt6797-hif-rx-batch-") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-DIS_ENABLED(x)=0", "-fsanitize=address,undefined",
                    "-fno-pie", "-no-pie", "-I", str(compat), "-I", str(driver),
                    str(here / "data-descriptor-test.c"), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-DIS_ENABLED(x)=0", "-DCONFIG_MT6797_DATA_FIXED_RATE_CODE=0x4c", "-fsanitize=address,undefined",
                    "-fno-pie", "-no-pie", "-I", str(compat), "-I", str(driver),
                    str(here / "data-descriptor-test.c"), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
print("data descriptor fixtures: PASS (default and 0x4c; ASan/UBSan, non-PIE)")
