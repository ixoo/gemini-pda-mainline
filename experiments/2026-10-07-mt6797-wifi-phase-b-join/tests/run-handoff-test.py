#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise actual scan-finish/idle-retirement host logic, not firmware or races."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
source = (driver / "mac.c").read_text()
functions = []
for name in ("mt6797_mac_finish_scan", "mt6797_mac_join_retire_idle_bss", "mt6797_mac_join_close", "mt6797_mac_cancel_scan"):
    match = re.search(r"static (?:bool|int|void) " + name + r"\([^;]*?\)\n\{.*?\n\}", source, re.S)
    if not match:
        parser.error("prepared handoff function missing: " + name)
    code = match.group(0)
    if name.endswith("retire_idle_bss"):
        code = "#if CONFIG_MT6797_STATION_JOIN\n" + code + "\n#endif"
    functions.append(code)
fixture = Path(__file__).with_name("join-handoff-test.c")
with tempfile.TemporaryDirectory(prefix="mt6797-join-handoff-") as directory:
    work = Path(directory)
    (work / "handoff-functions.h").write_text("\n".join(functions))
    for join in (0, 1):
        binary = work / ("test-" + str(join))
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
                        "-fsanitize=address,undefined", "-fno-pie", "-no-pie",
                        "-DCONFIG_MT6797_STATION_JOIN=" + str(join),
                        "-DCONFIG_MT6797_SCAN_TUNING_SAMPLE=1",
                        "-I", str(work), "-I", str(driver), str(fixture),
                        "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=10)
print("Scan handoff host logic: PASS (join on/off, ASan/UBSan; no race/firmware proof)")
