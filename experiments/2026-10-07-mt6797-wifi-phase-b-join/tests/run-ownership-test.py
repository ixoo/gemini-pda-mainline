#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise production join worker/close frame ownership on the host."""
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
struct = re.search(r"struct mt6797_mac \{.*?\n\};", source, re.S)
if not struct:
    parser.error("production struct mt6797_mac missing")
names = ("mt6797_mac_join_frame", "mt6797_mac_join_guard",
         "mt6797_mac_join_retire_idle_bss", "mt6797_mac_join_close",
         "mt6797_mac_join_control_event", "mt6797_mac_join_cleanup_step",
         "mt6797_mac_join_work", "mt6797_mac_join_wait_credit",
         "mt6797_mac_join_wait_management")
parts = [struct.group(0),
         "static unsigned long wait_for_completion_timeout(struct completion *, unsigned long);",
         "static int mt6797_mac_join_retire_idle_bss(struct mt6797_mac *mac);"]
for name in names:
    match = re.search(r"static (?:int|void|bool) " + name + r"\([^;]*?\)\n\{.*?\n\}", source, re.S)
    if not match:
        parser.error("production function missing: " + name)
    parts.append(match.group(0))
with tempfile.TemporaryDirectory(prefix="mt6797-join-ownership-") as directory:
    work = Path(directory)
    (work / "ownership-functions.h").write_text("\n".join(parts) + "\n")
    binary = work / "ownership-test"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-unused-function",
                    "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                    "-fno-pie", "-no-pie", "-I", str(work), "-I", str(driver),
                    str(Path(__file__).with_name("join-ownership-test.c")),
                    "-o", str(binary)], check=True)
    subprocess.run(["setarch", subprocess.check_output(["uname", "-m"], text=True).strip(),
                    "-R", str(binary)], check=True, timeout=30)
print("Join ownership: PASS (production worker/close, ASan/UBSan; no firmware/race proof)")
