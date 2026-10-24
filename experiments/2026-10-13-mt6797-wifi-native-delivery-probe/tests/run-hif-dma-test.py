#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the AP-DMA data-port transfer of the patched HIF without hardware."""
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
source = (driver / "hif.c").read_text()
if "mt6797_hif_dma_transfer(" not in source or "mt6797_hif_attach_dma(" not in source:
    parser.error("apply the AP-DMA data-port proposal first")
here = Path(__file__).resolve().parent
compat = args.compat or here.parents[1] / "2026-10-01-mt6797-normal-sets/tests"
with tempfile.TemporaryDirectory(prefix="mt6797-hif-dma-") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-DIS_ENABLED(x)=0", "-fsanitize=address,undefined",
                    "-fno-pie", "-no-pie", "-I", str(compat), "-I", str(driver),
                    str(here / "hif-dma-test.c"), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
print("AP-DMA data-port transfer fixtures: PASS (ASan/UBSan, non-PIE)")
