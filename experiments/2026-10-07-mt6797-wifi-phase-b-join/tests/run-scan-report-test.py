#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Drive the production scan-packet handler: a beacon is queued for mac80211, not informed directly."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
source = (driver / "mac.c").read_text()
match = re.search(r"static int mt6797_mac_scan_packet\([^;]*?\)\n\{.*?\n\}", source, re.S)
if not match:
    parser.error("production function missing: mt6797_mac_scan_packet")
if "cfg80211_inform_bss" in match.group(0):
    parser.error("scan packet handler still informs cfg80211 directly")
with tempfile.TemporaryDirectory(prefix="mt6797-scan-report-") as directory:
    work = Path(directory)
    (work / "scan-packet-function.h").write_text(match.group(0))
    binary = work / "scan-report-test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wno-sign-compare", "-Wno-unused-parameter",
                    "-fsanitize=address,undefined", "-fno-pie", "-no-pie",
                    "-I", str(work), "-I", str(driver),
                    str(Path(__file__).with_name("scan-report-test.c")), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
print("Scan report: PASS (production handler queues the beacon as a mac80211 frame with band/freq/signal; non-beacon frames and foreign channels refused)")
