#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Source-pinned native-beacon layout/actual-dispatch checks; synthetic, no device."""
import argparse
import hashlib
from pathlib import Path
import signal
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("parent_tree", type=Path)
parser.add_argument("child_tree", type=Path)
args = parser.parse_args()
rel = Path("drivers/net/wireless/mediatek/mt6797")
parent, child = args.parent_tree.resolve() / rel, args.child_tree.resolve() / rel
fixtures = Path(__file__).resolve().parent
assert hashlib.sha256((parent / "mac.c").read_bytes()).hexdigest() == \
    "47dbe9567a216aef6ae2703ee13204c49eb9594c1015c64f369e45598dd4c751"
old, new = (parent / "mac.c").read_text(), (child / "mac.c").read_text()
start = new.index("\t\t\t\t/* Class7 beacon paths above")
end = new.index("\t\t\t\tif (admitted)\n", start)
delta = new[start:end]
normalized = new.replace('#include "native-beacon.h"\n', '').replace(
    '\t\t\t\tstruct mt6797_native_beacon nbcn;\n', '').replace(delta, '')
for p in parent.iterdir():
    if p.is_file() and p.name != "mac.c":
        assert (child / p.name).read_bytes() == p.read_bytes(), p.name
assert {p.name for p in child.iterdir() if p.is_file()} == \
    {p.name for p in parent.iterdir() if p.is_file()} | {"native-beacon.h"}


def function(text, name):
    begin = text.index(name + "(")
    pos = text.index("{", begin) + 1
    depth = 1
    while depth:
        depth += (text[pos] == "{") - (text[pos] == "}")
        pos += 1
    return text[begin:pos]


normalized = normalized.replace(
    'window_blocked, beacons;', 'window_blocked;').replace(
    function(new, "mt6797_native_diag_rx_report"),
    function(old, "mt6797_native_diag_rx_report"))
assert normalized == old, "unexpected MAC change beyond native dispatch/counter/report field"


def hooks(text):
    account_start = text.index("\t\t\tnd_over = (")
    account_end = text.index("\n#endif", account_start)
    beacon_start = text.index("\t\t\tbranch = 7;\n")
    beacon_end = text.index("\t\t\t/* Phase C2:", beacon_start)
    native_start = text.index("\t\t\tif (mac->native_diag_engaged) {")
    native_end = text.index("\n#endif", native_start)
    return (
        "static int " + function(text, "mt6797_native_diag_rx_phase") + "\n"
        "static void " + function(text, "mt6797_native_diag_rx_report") + "\n"
        "static int " + function(text, "mt6797_mac_join_deliver_beacon") + "\n"
        "static int dispatch(struct mt6797_mac *mac, "
        "const struct mt6797_hif_rx_result *rp, struct sk_buff_head *qp) {\n"
        "struct mt6797_hif_rx_result rx = *rp; struct sk_buff_head received = *qp;\n"
        "struct mt6797_scan_frame beacon; struct mt6797_join_action_frame action;\n"
        "struct sk_buff *skb; bool nd_over; int nd_phase, ret = 0;\n"
        "unsigned int branch; (void)branch;\n"
        "for (unsigned int tick = 0; tick < 1; tick++) {\n" +
        text[account_start:account_end] + "\nif (nd_over) continue;\n" +
        text[beacon_start:beacon_end] + text[native_start:native_end] +
        "\n}\nfailed: *qp = received; return ret; }\n")


with tempfile.TemporaryDirectory(prefix="native-beacon-", dir="/tmp/opencode") as temporary:
    tmp = Path(temporary)
    flags = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
             "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie",
             "-I", str(tmp), "-I", str(child)]
    layout = tmp / "layout"
    subprocess.run([*flags, str(fixtures / "native-beacon-test.c"), "-o", str(layout)],
                   check=True, timeout=30)
    subprocess.run([str(layout)], check=True, timeout=30)
    for label, text in (("parent", old), ("child", new)):
        (tmp / "beacon-dispatch.h").write_text(hooks(text))
        binary = tmp / label
        subprocess.run([*flags, str(fixtures / "native-beacon-dispatch-test.c"),
                        "-o", str(binary)], check=True, timeout=30)
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
        if label == "parent":
            assert result.returncode == -signal.SIGABRT and "q.count" in result.stderr, result.stderr
            print("actual ND4 parent negative: same class2 beacon fixture withheld (no compiler failure)")
        else:
            assert result.returncode == 0, result.stderr
            print(result.stdout, end="")
print("native beacon: PASS ASan/UBSan; old ordinary/header/flags/stop/drain/regulatory source unchanged")
