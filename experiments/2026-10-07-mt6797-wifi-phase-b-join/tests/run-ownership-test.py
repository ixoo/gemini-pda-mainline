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
# The predicate's accepted RSN body must be the body of the element the
# reviewed connect helper sends; both are parsed from source, never retyped.
def hex_bytes(text):
    return bytes(int(v, 16) for v in re.findall(r"0x([0-9a-fA-F]{2})", text))
driver_rsn = re.search(r"mt6797_join_rsn_body\[20\] = \{(.*?)\};", source, re.S)
helper = (Path(__file__).resolve().parent.parent / "helper/join-connect.c").read_text()
helper_rsn = re.search(r"RSN_ELEMENT\[\] = \{(.*?)\};", helper, re.S)
if not driver_rsn or not helper_rsn:
    parser.error("RSN constants missing from the driver or the helper")
driver_body, helper_element = hex_bytes(driver_rsn.group(1)), hex_bytes(helper_rsn.group(1))
if len(driver_body) != 20 or helper_element[:2] != b"\x30\x14" or helper_element[2:] != driver_body:
    parser.error("the driver's accepted RSN body differs from the helper's RSN element")
rsn_definition = re.search(r"static const u8 mt6797_join_rsn_body\[20\] = \{.*?\};", source, re.S)
parts = [struct.group(0), rsn_definition.group(0),
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
