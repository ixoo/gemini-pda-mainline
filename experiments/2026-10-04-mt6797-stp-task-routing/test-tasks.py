#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Test actual shared link/WMT headers; adapt only historical member access paths."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

experiment = Path(__file__).resolve().parent
legacy = experiment.parent / "2026-10-03-mt6797-wifi-audit" / "tests"
headers = Path(sys.argv[1])
selected = (
    "stp-full.h", "stp-full-stream.h", "stp-full-link.h", "stp-full-task.h", "wmt-full-stp.h",
    "wmt-full-stp-state.h", "wmt-full-stp-stream.h", "wmt-full-stp-tx.h",
    "mt6797-wmt-full-io.h",
)
fixtures = (
    "wmt-full-stp-test.c", "wmt-full-stp-state-test.c",
    "wmt-full-stp-stream-test.c", "wmt-full-stp-tx-test.c",
    "wmt-full-io-test.c", "wmt-negotiate-test.c", "wmt-identity-io-test.c",
    "wmt-version-io-test.c", "wmt-versions-test.c",
)


def adapt_members(text):
    # The old fixtures keep their assertions; the four link fields and ACK flag
    # now live inside the shared transport member. No behavior is rewritten.
    return re.sub(r"(\.|->)(tx_next|rx_next|peer_ack|local_ack|ack_owed)\b",
                  r"\1transport.\2", text)


with tempfile.TemporaryDirectory(prefix="gemini-stp-link-") as temporary:
    work = Path(temporary)
    for path in legacy.glob("*.h"):
        (work / path.name).write_text(adapt_members(path.read_text()))
    for name in selected:
        shutil.copyfile(headers / name, work / name)
    includes = work / "linux"
    includes.mkdir()
    for name in ("clk", "completion", "interrupt", "io", "jiffies", "spinlock", "string", "delay"):
        (includes / f"{name}.h").write_text("")
    (includes / "errno.h").write_text(
        "#ifdef __linux__\n#include_next <linux/errno.h>\n#endif\n"
    )
    for name in fixtures:
        (work / name).write_text(adapt_members((legacy / name).read_text()))
    shutil.copyfile(experiment / "test-link.c", work / "test-link.c")
    shutil.copyfile(experiment / "test-tasks.c", work / "test-tasks.c")
    framing = experiment.parent / "2026-10-04-mt6797-stp-task-framing" / "test-stp.c"
    shutil.copyfile(framing, work / "test-stp.c")
    for name in (*fixtures, "test-link.c", "test-stp.c", "test-tasks.c"):
        binary = work / Path(name).stem
        subprocess.run([
            os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
            "-fsanitize=address,undefined", f"-I{work}", str(work / name),
            "-o", str(binary),
        ], check=True)
        subprocess.run([str(binary)], check=True)
