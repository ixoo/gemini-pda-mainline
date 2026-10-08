#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run mac80211's own rate matching on the driver's 5 GHz band and the owner AP's rates."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
tree = args.kernel_tree.resolve()
mlme = (tree / "net/mac80211/mlme.c").read_text()
mac = (tree / "drivers/net/wireless/mediatek/mt6797/mac.c").read_text()
rates = re.search(r"static void ieee80211_get_rates\(struct ieee80211_supported_band \*sband,.*?\n\}", mlme, re.S)
table = re.search(r"static const int bitrates\[\] = \{\n(.*?)\n\t\};", mac, re.S)
if not rates or not table:
    parser.error("production rate matching or driver bitrate table missing")
with tempfile.TemporaryDirectory(prefix="mt6797-scan-rates-") as directory:
    work = Path(directory)
    (work / "rates-function.h").write_text(rates.group(0))
    (work / "driver-bitrates.h").write_text("static const int driver_bitrates[] = {" + table.group(1) + "};\n")
    binary = work / "rates-test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wno-sign-compare",
                    "-fsanitize=address,undefined", "-fno-pie", "-no-pie", "-I", str(work),
                    str(Path(__file__).with_name("scan-rates-test.c")), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
print("Scan rate matching: PASS (mac80211 ieee80211_get_rates on the driver's 5 GHz band; owner AP rates all match; empty record reproduces 'No legacy rates')")
