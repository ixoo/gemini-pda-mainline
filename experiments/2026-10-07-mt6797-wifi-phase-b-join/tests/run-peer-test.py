#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise production peer setup and independent credit/event waits on the host."""
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
names = ("mt6797_mac_join_guard", "mt6797_mac_join_control_event",
         "mt6797_mac_join_wait_credit", "mt6797_mac_join_wait_management",
         "mt6797_mac_join_wait_channel", "mt6797_mac_join_add_peer",
         "mt6797_mac_join_associate", "mt6797_mac_join_request_cleanup",
         "mt6797_mac_join_cleanup_step", "mt6797_mac_mgd_prepare_tx",
         "mt6797_mac_mgd_complete_tx", "mt6797_mac_sta_state",
         "mt6797_mac_set_key")
functions = []
for name in names:
    match = re.search(r"static (?:int|void) " + name + r"\([^;]*?\)\n\{.*?\n\}", source, re.S)
    if not match:
        parser.error("production function missing: " + name)
    functions.append(match.group(0))
with tempfile.TemporaryDirectory(prefix="mt6797-join-peer-") as directory:
    work = Path(directory)
    (work / "peer-functions.h").write_text("\n".join(functions))
    binary = work / "peer-test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-pie", "-no-pie",
                    "-I", str(work), "-I", str(driver),
                    str(Path(__file__).with_name("join-peer-test.c")),
                    "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
print("Peer setup: PASS (production functions, ASan/UBSan; no firmware/race proof)")
