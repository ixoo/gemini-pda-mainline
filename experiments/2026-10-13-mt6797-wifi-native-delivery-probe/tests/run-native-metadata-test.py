#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Paired actual-HIF/RX tests and extracted native metadata hooks; no hardware."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
import runpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("parent_tree", type=Path)
parser.add_argument("child_tree", type=Path)
args = parser.parse_args()
rel = Path("drivers/net/wireless/mediatek/mt6797")
parent = args.parent_tree.resolve() / rel
child = args.child_tree.resolve() / rel
fixtures = Path(__file__).resolve().parent
repo = fixtures.parents[2]
pins = {
    "mac.c": "c794cd5bcebd90f21f29f2a1bae4792f1e00c3160c22680e031f7b714b6aaa23",
    "hif.c": "73f6c0b5182b61953e223e331cc13b64327a784ebbf98977b8a50b7bada9e01c",
    "data-rx.h": "e465bd1ee3a8c16474bfdcc3d909f6ce7349840d4c7fb6160bdcffada54ea2e8",
}
for name, digest in pins.items():
    assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == digest, name


def function(text, name):
    start = text.index(name + "(")
    opening = text.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


mac = (child / "mac.c").read_text()
old_mac = (parent / "mac.c").read_text()
# Admission, prospective reads/ceilings, flags, radio action and READY untouched.
for name in ("mt6797_native_diag_pre_read", "mt6797_native_diag_step"):
    assert function(mac, name) == function(old_mac, name), name
assert (child / "native-diag.h").read_bytes() == (parent / "native-diag.h").read_bytes()
assert mac.count("mt6797_native_diag_rx_report(mac);") == 2
assert "type[rx.packet_type >> 13]++" in mac
assert "admitted = mt6797_native_diag_admit(mac->native_diag_state, &nb);" in mac
assert "if (admitted && gate == MT6797_NATIVE_RX_OK) {" in mac
phase_start = mac.index("\t\t\tnd_over = (")
phase_end = mac.index("\t\t\tif (mac->native_diag_state ==", phase_start)
class_hook = mac[phase_start:phase_end]
gate_start = mac.index("\t\t\t\tif (admitted)\n")
gate_end = mac.index("\t\t\t\tif (admitted && gate", gate_start)
gate_hook = mac[gate_start:gate_end]
fields_start = mac.index("\tstruct {\n\t\tunsigned int type[8]")
fields_end = mac.index("\n", mac.index("\tbool native_diag_rxd_sampled;", fields_start))
refusal_start = mac.index("if (ret == -EPROTO && rx.protocol_refusal")
refusal_end = mac.index("\n#endif", refusal_start)

with tempfile.TemporaryDirectory(prefix="native-metadata-", dir="/tmp/opencode") as directory:
    tmp = Path(directory)
    old_rx = (parent / "data-rx.h").read_text()
    (tmp / "parent-native.h").write_text(
        "static inline bool " + function(old_rx, "mt6797_data_rx_native").replace(
            "mt6797_data_rx_native(", "parent_native(", 1) + "\n")
    (tmp / "metadata-fields.h").write_text(mac[fields_start:fields_end] + "\n")
    (tmp / "metadata-hif-log.h").write_text(
        "static void logged_refusal(int ret, unsigned int port, "
        "struct mt6797_hif_rx_result rx) {\n" +
        mac[refusal_start:refusal_end] + "\n}\n")
    (tmp / "metadata-hooks.h").write_text(
        "static int " + function(mac, "mt6797_native_diag_rx_phase") + "\n"
        "static void " + function(mac, "mt6797_native_diag_rx_report") + "\n"
        "static int observed_class(struct mt6797_mac *mac, "
        "const struct mt6797_hif_rx_result *rp) {\n"
        "struct mt6797_hif_rx_result rx = *rp; bool nd_over; int nd_phase;\n" +
        class_hook + "return nd_phase; }\n"
        "static bool observed_gate(struct mt6797_mac *mac, "
        "const struct mt6797_hif_rx_result *rp, int nd_phase, bool admitted) {\n"
        "struct mt6797_hif_rx_result rx = *rp; size_t mo, ml;\n"
        "enum mt6797_native_rx_gate gate = MT6797_NATIVE_RX_INPUT;\n" +
        gate_hook + "return admitted && gate == MT6797_NATIVE_RX_OK; }\n")

    errors = {}

    def run(fixture, driver, label, extra=()):
        binary = tmp / label
        command = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wformat=2",
                   "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                   "-fno-pie", "-no-pie", "-I", str(tmp), "-I", str(driver),
                   "-I", str(repo / "experiments/2026-10-01-mt6797-normal-sets/tests"),
                   *extra, str(fixtures / fixture), "-o", str(binary)]
        subprocess.run(command, check=True, timeout=30)
        result = subprocess.run([str(binary)], check=True, timeout=30,
                                capture_output=True, text=True)
        errors[label] = result.stderr
        return result.stdout

    defines = ["-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG", "-DIS_ENABLED(x)=1"]
    old = run("native-metadata-hif-test.c", parent, "hif-parent", defines)
    new = run("native-metadata-hif-test.c", child, "hif-child", [*defines, "-DTEST_METADATA"])
    assert old == new, "actual HIF results/transport-call counts changed"
    print("actual HIF: both refusal gates, valid/absent fields, every transport fault; "
          "parent/child identical results/calls, no copy, poison (ASan/UBSan)")
    print(run("native-metadata-rx-test.c", child, "rx-child"), end="")
    phase_output = run("native-metadata-phase-test.c", child, "phase-child")
    print(phase_output, end="")
    assert "bytes=4 fields_valid=0 type=0x0000 channel=0 header=0x00 groups=0x0 msdu=0 status=0x0000" in phase_output
    # Original classifier stays byte-unchanged: separate telemetry prefix must
    # neither force a negative nor manufacture a positive on a faulty run.
    classifier = runpy.run_path(str(fixtures / "classify-native-test.py"))
    classify = classifier["classify"]
    receipt, boot = classifier["receipt"](), classifier["BOOT"]
    telemetry = (phase_output + errors["hif-child"]).encode()
    for fault in (False, True):
        log = classifier["kmsg"](fault=fault)
        assert classify(log, receipt, boot) == classify(log + b"\n" + telemetry, receipt, boot)
    for broken in (b"one-shot WLAN native-diag: state=broken",
                   b"one-shot WLAN native-diag RX: first mpdu_bytes=x",
                   b"one-shot WLAN native-diag no-radio latch"):
        log = classifier["kmsg"]() + b"\n" + broken
        result = classify(log + b"\n" + telemetry, receipt, boot)
        assert not result["native_delivery_pass"] and result["malformed_records"] == 1
    print("existing classifier compatibility: unchanged positive/fault/malformed state/RX/fault verdicts")
print("native metadata: PASS; synthetic only, no kernel build/device access")
