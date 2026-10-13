#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the actual native caller and HIF with finite mocked MMIO."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("kernel_tree", type=Path)
parser.add_argument("--mac-source", type=Path)
args = parser.parse_args()
driver = args.kernel_tree.resolve() / "drivers/net/wireless/mediatek/mt6797"
source = (args.mac_source or driver / "mac.c").read_text()
start = source.index("static void mt6797_native_diag_step(")
end = source.index("\n}\n", start) + 3
fixture = Path(__file__).with_name("native-hif-test.c")
compat = fixture.parents[2] / "2026-10-01-mt6797-normal-sets/tests"
with tempfile.TemporaryDirectory(prefix="mt6797-native-hif-") as directory:
    output = Path(directory)
    (output / "native-step.inc").write_text(source[start:end])
    binary = output / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG", "-DIS_ENABLED(x)=1",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(output), "-I", str(compat),
                    "-I", str(driver), str(fixture), "-o", str(binary)],
                   check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
print("actual native caller/HIF: PASS (ASan/UBSan; mocked MMIO, not firmware)")
