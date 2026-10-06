#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Test management credit preparation against prepared kernel owner headers."""
from pathlib import Path
import argparse
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
for name in ("normal_command.h", "hif_command.h", "hif_transfer_size.h"):
    if not (driver / name).is_file():
        parser.error("prepared Phase A owner headers are required")
experiment = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="mt6797-join-submit-") as directory:
    work = Path(directory)
    for stem in ("join-events", "join-tx", "join-submit"):
        lines = (experiment.parents[1] / "patches" / {"join-events": 'proposals/0122-wifi-mt6797-parse-bounded-station-join-events.patch', "join-tx": 'proposals/0123-wifi-mt6797-encode-finite-management-TX-descriptors.patch', "join-submit": 'proposals/0126-wifi-mt6797-account-management-frame-submission-through-TC4.patch'}[stem]).read_text().splitlines(True)
        hunk = next(i for i, line in enumerate(lines) if line.startswith("@@"))
        (work / (stem + ".h")).write_text("".join(
            line[1:] for line in lines[hunk + 1:] if line.startswith("+")))
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-I", str(work), "-I", str(driver),
                    str(experiment / "tests/join-submit-test.c"),
                    "-o", str(work / "test")], check=True)
    subprocess.run([str(work / "test")], check=True)
print("Management shared-TC4 credit fixtures: PASS (ASan/UBSan)")
