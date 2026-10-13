#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the ACTUAL mt6797_mac_join_control_event owned-BSS (0x11) admission from
the selected mac.c: valid owned-slot notifications in pre-data/data/teardown (incl
>2 repeats, no cap), foreign-slot/non-boolean/sequence refusals, quota/reserved not
TC4, and the recorded absence driving the gate. Extracts control_event, the absence
gate helpers and set_absent; the fixture includes the real join-events.h and supplies
kernel shims for the unrelated event paths. Not a kernel concurrency model."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
parser.add_argument("--mac-source", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
source = (args.mac_source or driver / "mac.c").read_text()
parts = re.findall(r"^#define MT6797_JOIN_DATA_TX_QUEUE[A-Z0-9_]* .*$", source, re.M)
for name in ("mt6797_mac_join_tx_pressure",
             "mt6797_mac_join_publish_tx_gate", "mt6797_mac_join_set_absent",
             "mt6797_mac_join_control_event"):
    m = re.search(r"static (?:int|bool|void|unsigned int) " + name +
                  r"\((?:const )?[^;]*?\)\n\{.*?\n\}", source, re.S)
    if not m:
        parser.error("function missing (apply 0184): " + name)
    parts.append(m.group(0))
with tempfile.TemporaryDirectory(prefix="mt6797-control-event-") as d:
    (Path(d) / "control-functions.h").write_text("\n".join(parts) + "\n")
    binary = Path(d) / "t"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-unused-function", "-Wno-unused-parameter",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(driver), "-I", str(Path(__file__).resolve().parent),
                    "-DCONTROL_FUNCTIONS=\"%s\"" % (Path(d) / "control-functions.h"),
                    str(Path(__file__).with_name("control-event-test.c")), "-o", str(binary)],
                   check=True, timeout=40)
    subprocess.run([str(binary)], check=True, timeout=30)
print("control-event-admission: PASS")
