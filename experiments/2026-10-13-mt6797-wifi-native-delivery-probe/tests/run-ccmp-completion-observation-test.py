#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual helper tests plus exact reversal of the MAC-only diagnostic delta."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("parent", type=Path)
parser.add_argument("child", type=Path)
args = parser.parse_args()
relative = Path("drivers/net/wireless/mediatek/mt6797")
parent, child = args.parent / relative, args.child / relative
fixtures = Path(__file__).resolve().parent
repo = fixtures.parents[2]
pins = {
    "mac.c": "fdc2d7fb6391e64b1e3d6bda0d75a6f7e326241091da48f9611d328630617d9a",
    "hif.c": "904ee916416359987b6168a6d84a8fbf155fcfabc599a1789609dbd130d83790",
    "hif.h": "55cea74081c83b41221b72246494a42548d4f30857fbe9def9116597ed4ebe11",
}
for name, digest in pins.items():
    assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == digest, name
assert {p.name for p in parent.iterdir()} == {p.name for p in child.iterdir()}
for path in parent.iterdir():
    if path.is_file() and path.name != "mac.c":
        assert path.read_bytes() == (child / path.name).read_bytes(), path.name
assert (args.parent / "drivers/soc/mediatek/mt6797-consys.c").read_bytes() == (
    args.child / "drivers/soc/mediatek/mt6797-consys.c").read_bytes()


def braced(text, marker):
    start = text.index(marker)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


mac = (child / "mac.c").read_text()
names = ("mt6797_ccmp_observe_rx", "mt6797_ccmp_observe_guard",
         "mt6797_ccmp_observe_terminal")
functions = [braced(mac, "static void " + name + "(") for name in names]
# No transport, parser, allocation, scheduling, packet, or key access in helpers.
for body in functions:
    assert "hif_read" not in body and "hif_write" not in body
    assert "join_packet" not in body and "scratch" not in body
    assert "schedule" not in body and "ccmp_rx" not in body
assert mac.count("mt6797_ccmp_observe_terminal(mac);") == 2
assert mac.count("mt6797_ccmp_observe_rx(&mac->ccmp_observation, port, ret, &rx);") == 1
with tempfile.TemporaryDirectory(prefix="ccmp-observation-") as directory:
    tmp = Path(directory)
    (tmp / "observation-struct.h").write_text(
        braced(mac, "struct mt6797_ccmp_observation {") + ";\n")
    (tmp / "observation-functions.h").write_text("\n\n".join(functions) + "\n")
    # Reversing the published patch must recover every parent MAC byte. This
    # proves it contains only the reviewed hooks and preserves all control flow.
    path = tmp / relative / "mac.c"
    path.parent.mkdir(parents=True)
    path.write_text(mac)
    patch = repo / "patches/proposals/0196-wifi-mt6797-retain-terminal-ccmp-completion-observations.patch"
    subprocess.run(["git", "apply", "--reverse", str(patch)], cwd=tmp, check=True)
    assert path.read_bytes() == (parent / "mac.c").read_bytes()
    binary = tmp / "observation-test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wformat=2",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-I", str(tmp), str(fixtures / "ccmp-completion-observation-test.c"),
                    "-o", str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
print("C5 pins, unchanged HIF/boot/driver files and exact MAC reversal: pass")
