#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the native-crypto-delivery diagnostic decision core (proposal 0181) with sanitizers."""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
for name in ("native-diag.h", "join-commands.h"):
    if not (driver / name).is_file():
        parser.error("apply proposal 0181 on the 0180 parent first (missing %s)" % name)
fixture = Path(__file__).with_name("native-diag-test.c")
with tempfile.TemporaryDirectory(prefix="mt6797-native-diag-") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(driver), str(fixture),
                    "-o", str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
    # The CCMP budget step under the 60-second window, with and without the
    # connected lifetime (0274: the lifetime's ceilings are counts, not stops).
    ccmp = Path(__file__).with_name("ccmp-budget-step-test.c")
    for defines in (["-DCONFIG_MT6797_CCMP_60S_WINDOW"],
                    ["-DCONFIG_MT6797_CCMP_60S_WINDOW", "-DCONFIG_MT6797_CCMP_CONNECTED_LIFETIME"]):
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", *defines,
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        "-fno-pie", "-no-pie", "-I", str(driver), str(ccmp),
                        "-o", str(binary)], check=True, timeout=30)
        subprocess.run([str(binary)], check=True, timeout=30)
print("native-diag decision: PASS (ASan/UBSan; synthetic only; CCMP budget step with and without the connected lifetime)")
