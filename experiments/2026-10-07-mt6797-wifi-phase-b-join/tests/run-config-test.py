#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the production config operation: radio index, flags and channel binding."""
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
match = re.search(r"static int mt6797_mac_config\([^;]*?\)\n\{.*?\n\}", source, re.S)
if not match:
    parser.error("production function missing: mt6797_mac_config")
with tempfile.TemporaryDirectory(prefix="mt6797-config-") as directory:
    work = Path(directory)
    (work / "config-function.h").write_text(match.group(0))
    binary = work / "config-test"
    # The kernel build does not use -Wsign-compare; the production function
    # compares an int slot with unsigned channel counts and ignores 'changed'.
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-sign-compare", "-Wno-unused-parameter",
                    "-fsanitize=address,undefined", "-fno-pie", "-no-pie",
                    "-I", str(work), "-I", str(driver),
                    str(Path(__file__).with_name("config-test.c")),
                    "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
print("Config operation: PASS (production function; radio index -1 accepted, >= 0 refused; channel binding)")
