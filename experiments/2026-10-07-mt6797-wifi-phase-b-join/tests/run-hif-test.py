#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the actual patched HIF path without accessing hardware."""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
if "mt6797_hif_send_management(" not in (driver / "hif.c").read_text():
    parser.error("apply the Phase B helper and HIF preparation patches first")
experiment = Path(__file__).resolve().parents[1]
compat = experiment.parent / "2026-10-01-mt6797-normal-sets/tests"
with tempfile.TemporaryDirectory(prefix="mt6797-join-hif-") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-DIS_ENABLED(x)=0", "-fsanitize=address,undefined",
                    "-fno-pie", "-no-pie", "-I", str(compat), "-I", str(driver),
                    str(experiment / "tests/join-hif-test.c"),
                    "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
print("Actual HIF management path fault fixtures: PASS (ASan/UBSan, non-PIE)")
