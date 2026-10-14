#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exact ND6 parent, unwired stable-PTK helper; synthetic host checks only."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("parent_tree", type=Path)
parser.add_argument("child_tree", type=Path)
args = parser.parse_args()
rel = Path("drivers/net/wireless/mediatek/mt6797")
parent, child = args.parent_tree.resolve() / rel, args.child_tree.resolve() / rel
fixtures = Path(__file__).resolve().parent
for name, pin in {
    "mac.c": "046012d7448d6a00c2e52ec64e48633d521045e4bda5f6c79b673a2a2959f462",
    "data-rx.h": "02179812099659607a99e0d092c58c031960375f64d502a566274c413106134a",
    "native-diag.h": "905b6763ac1a15cbdca1ef0643db70585dfa443d2fdd36af223b349d157ccae0",
}.items():
    assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == pin, name
for p in parent.iterdir():
    if p.is_file():
        assert (child / p.name).read_bytes() == p.read_bytes(), p.name
assert {p.name for p in child.iterdir() if p.is_file()} == \
    {p.name for p in parent.iterdir() if p.is_file()} | {"ccmp-rx.h"}
helper = (child / "ccmp-rx.h").read_text()
for forbidden in ("ieee80211_rx", "RX_FLAG", "dev_info", "readl", "writel", "generation"):
    assert forbidden not in helper, forbidden
assert not any('"ccmp-rx.h"' in p.read_text()
               for p in parent.iterdir() if p.is_file() and p.suffix in {".c", ".h"})

with tempfile.TemporaryDirectory(prefix="ccmp-rx-", dir="/tmp/opencode") as directory:
    binary = Path(directory) / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(child),
                    str(fixtures / "ccmp-rx-test.c"), "-o", str(binary)],
                   check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
print("CCMP helper: PASS ASan/UBSan, actual header; all ND6 files byte-identical/unwired; no kernel/device")
