#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Test the exact new header carried by the preparation patch."""
from pathlib import Path
import subprocess
import tempfile

experiment = Path(__file__).resolve().parents[1]
patch = (experiment.parents[1] / "patches/proposals/0122-wifi-mt6797-parse-bounded-station-join-events.patch").read_text().splitlines(True)
hunk = next(i for i, line in enumerate(patch) if line.startswith("@@"))
header = "".join(line[1:] for line in patch[hunk + 1:] if line.startswith("+"))
with tempfile.TemporaryDirectory(prefix="mt6797-join-events-") as directory:
    work = Path(directory)
    (work / "join-events.h").write_text(header)
    tx_patch = (experiment.parents[1] / "patches/proposals/0123-wifi-mt6797-encode-finite-management-TX-descriptors.patch").read_text().splitlines(True)
    tx_hunk = next(i for i, line in enumerate(tx_patch) if line.startswith("@@"))
    (work / "join-tx.h").write_text("".join(line[1:] for line in tx_patch[tx_hunk + 1:] if line.startswith("+")))
    rx_patch = (experiment.parents[1] / "patches/proposals/0124-wifi-mt6797-decode-directed-management-join-RX.patch").read_text().splitlines(True)
    rx_hunk = next(i for i, line in enumerate(rx_patch) if line.startswith("@@"))
    (work / "join-rx.h").write_text("".join(line[1:] for line in rx_patch[rx_hunk + 1:] if line.startswith("+")))
    cmd_patch = (experiment.parents[1] / "patches/proposals/0125-wifi-mt6797-encode-bounded-legacy-station-join-payloads.patch").read_text().splitlines(True)
    cmd_hunk = next(i for i, line in enumerate(cmd_patch) if line.startswith("@@"))
    (work / "join-commands.h").write_text("".join(line[1:] for line in cmd_patch[cmd_hunk + 1:] if line.startswith("+")))
    (work / "test.c").write_text((experiment / "tests/join-events-test.c").read_text())
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", str(work / "test.c"),
                    "-o", str(work / "test")], check=True)
    subprocess.run([str(work / "test")], check=True)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-I", str(work),
                    str(experiment / "tests/join-tx-test.c"),
                    "-o", str(work / "tx-test")], check=True)
    subprocess.run([str(work / "tx-test")], check=True)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-I", str(work),
                    str(experiment / "tests/join-rx-test.c"),
                    "-o", str(work / "rx-test")], check=True)
    subprocess.run([str(work / "rx-test")], check=True)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-I", str(work),
                    str(experiment / "tests/join-commands-test.c"),
                    "-o", str(work / "commands-test")], check=True)
    subprocess.run([str(work / "commands-test")], check=True)
print("Join event, TX, RX and state-command fixtures: PASS (ASan/UBSan)")
