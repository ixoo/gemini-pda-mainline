#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the data descriptor report variant and the receive-vector word (0271, 0272) without hardware."""
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
if "mt6797_join_tx_data_descriptor_report(" not in source:
    parser.error("apply the credit-completion proposal first")
here = Path(__file__).resolve().parent
compat = args.compat or here.parents[1] / "2026-10-01-mt6797-normal-sets/tests"
with tempfile.TemporaryDirectory(prefix="mt6797-hif-rx-batch-") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-DIS_ENABLED(x)=0", "-fsanitize=address,undefined",
                    "-fno-pie", "-no-pie", "-I", str(compat), "-I", str(driver),
                    str(here / "credit-completion-test.c"), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
print("credit-completion fixtures: PASS (ASan/UBSan, non-PIE)")
