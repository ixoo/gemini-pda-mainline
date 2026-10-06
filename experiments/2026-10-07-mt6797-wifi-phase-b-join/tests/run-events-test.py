#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the selected tree's join event, TX, RX and command headers."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
for name in ("join-events.h", "join-tx.h", "join-rx.h", "join-commands.h"):
    if not (driver / name).is_file():
        parser.error("selected tree lacks " + name)
tests = Path(__file__).resolve().parent
arch = subprocess.check_output(["uname", "-m"], text=True).strip()
with tempfile.TemporaryDirectory(prefix="mt6797-join-events-") as directory:
    work = Path(directory)
    for source in ("join-events-test.c", "join-tx-test.c", "join-rx-test.c",
                   "join-commands-test.c"):
        binary = work / source[:-2]
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                        "-fno-pie", "-no-pie", "-I", str(driver),
                        str(tests / source), "-o", str(binary)], check=True)
        # Sanitized binaries need a fixed address layout on the Buildbox; a
        # bounded timeout turns any spin into a failure, not a stall.
        subprocess.run(["setarch", arch, "-R", str(binary)], check=True, timeout=30)
print("Join event, TX, RX and state-command fixtures: PASS (selected headers, ASan/UBSan)")
