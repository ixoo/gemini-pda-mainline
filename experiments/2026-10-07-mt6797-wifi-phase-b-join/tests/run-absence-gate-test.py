#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the maintained owned-BSS absence/presence backpressure gate from the
selected mac.c: mt6797_mac_join_tx_pressure / publish_tx_gate / set_absent. Extracts
the struct, the Phase-C3 limits and those three functions; the fixture supplies
kernel shims (ieee80211 stop/wake as counters, skb_queue_len as a test value) and
deterministic scenarios. Not a kernel concurrency model."""
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
limits = [l for l in re.findall(r"^#define MT6797_JOIN_DATA_TX_QUEUE[A-Z0-9_]* .*$", source, re.M)]
if len(limits) < 2:
    parser.error("MT6797_JOIN_DATA_TX_QUEUE limits missing")
parts = list(limits)
for name in ("mt6797_mac_join_tx_pressure", "mt6797_mac_join_publish_tx_gate",
             "mt6797_mac_join_set_absent"):
    m = re.search(r"static (?:bool|void) " + name + r"\([^;]*?\)\n\{.*?\n\}", source, re.S)
    if not m:
        parser.error("function missing (apply the maintained-queue patch): " + name)
    parts.append(m.group(0))
with tempfile.TemporaryDirectory(prefix="mt6797-absence-gate-") as d:
    (Path(d) / "absence-gate-functions.h").write_text("\n".join(parts) + "\n")
    binary = Path(d) / "t"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-unused-function", "-Wno-unused-parameter",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(Path(__file__).resolve().parent),
                    "-DABSENCE_GATE_FUNCTIONS=\"%s\"" % (Path(d) / "absence-gate-functions.h"),
                    str(Path(__file__).with_name("absence-gate-test.c")), "-o", str(binary)],
                   check=True, timeout=40)
    subprocess.run([str(binary)], check=True, timeout=30)
print("absence-gate: PASS (pressure/stop/wake/absence state machine)")
