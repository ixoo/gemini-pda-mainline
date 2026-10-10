#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the Phase C3 data transmit descriptor, the TC1 page pool and the shared reconciliation on the host."""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
if "mt6797_join_prepare_data" not in (driver / "join-submit.h").read_text():
    parser.error("apply proposal 0167 after the Phase B series first")
experiment = Path(__file__).resolve().parents[1]
compat = experiment.parent / "2026-10-01-mt6797-normal-sets/tests"
fixture = Path(__file__).with_name("data-tx-test.c")
with tempfile.TemporaryDirectory(prefix="mt6797-data-tx-") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(compat), "-I", str(driver), str(fixture),
                    "-o", str(binary)], check=True, timeout=60)
    subprocess.run([str(binary)], check=True, timeout=30)
print("Data TX ledger: PASS (ASan/UBSan; synthetic bytes only, no firmware or device effects)")
