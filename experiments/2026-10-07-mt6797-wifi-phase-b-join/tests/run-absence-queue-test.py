#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Test actual worker selection and close/rearm queue blocks, not concurrency."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("mac_source", type=Path)
args = parser.parse_args()
source = args.mac_source.read_text()
parts = re.findall(r"^#define MT6797_JOIN_DATA_(?:TX_QUEUE\w*|LAST_PID) .*$", source, re.M)
for name in ("mt6797_mac_join_tx_pressure", "mt6797_mac_join_publish_tx_gate",
             "mt6797_mac_join_set_absent"):
    match = re.search(r"static (?:bool|void) " + name + r"\([^;]*?\)\n\{.*?\n\}", source, re.S)
    if not match:
        parser.error("missing function " + name)
    parts.append(match.group(0))
start = source.index("\tif (!mac->join_inflight && !mac->join_page_debt) {")
end = source.index("\n\t\tif (skb) {", start)
parts.append("static struct sk_buff *select_owned(struct mt6797_mac *mac, "
             "struct sk_buff_head discard) {\nunsigned long flags; "
             "struct sk_buff *skb = NULL;\n" + source[start:end] + "\n}\nreturn skb;\n}")
for name in ("rearm", "close"):
    start = source.index("static void mt6797_mac_join_" + name + "(")
    end = source.index("\n}\n", start)
    body = source[start:end]
    first = body.index("\tspin_lock_irqsave(&mac->join_queue.lock, flags);")
    last = body.index("\n\tspin_unlock_irqrestore(&mac->join_queue.lock, flags);", first)
    last += len("\n\tspin_unlock_irqrestore(&mac->join_queue.lock, flags);")
    parts.append("static void " + name + "_gate(struct mt6797_mac *mac) {\n"
                 "unsigned long flags;\n" + body[first:last] + "\n}")
with tempfile.TemporaryDirectory(prefix="mt6797-absence-queue-") as directory:
    output = Path(directory)
    (output / "queue-functions.h").write_text("\n".join(parts))
    binary = output / "test"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-pie", "-no-pie",
                    "-I", str(output), str(Path(__file__).with_name("absence-queue-test.c")),
                    "-o", str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
print("actual absence dequeue/close/rearm blocks: PASS (host, not concurrency)")
