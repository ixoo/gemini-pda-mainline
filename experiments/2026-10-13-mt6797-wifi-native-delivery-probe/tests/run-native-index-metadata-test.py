#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Paired actual ND5 dispatch with bounded index/group4 telemetry; no hardware."""
import argparse
import ast
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
import runpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("parent_tree", type=Path)
parser.add_argument("child_tree", type=Path)
args = parser.parse_args()
rel = Path("drivers/net/wireless/mediatek/mt6797")
parent, child = args.parent_tree.resolve() / rel, args.child_tree.resolve() / rel
fixtures = Path(__file__).resolve().parent
for name, pin in {
    "mac.c": "0327fcd9ddddae40dff6575296da9cff496adbb691141dc8c56c557799555e28",
    "data-rx.h": "02179812099659607a99e0d092c58c031960375f64d502a566274c413106134a",
    "native-diag.h": "905b6763ac1a15cbdca1ef0643db70585dfa443d2fdd36af223b349d157ccae0",
}.items():
    assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == pin, name
for p in parent.iterdir():
    if p.is_file() and p.name != "mac.c":
        assert (child / p.name).read_bytes() == p.read_bytes(), p.name
assert {p.name for p in child.iterdir() if p.is_file()} == \
    {p.name for p in parent.iterdir() if p.is_file()}

# Reuse the existing actual-source extraction functions, not a new harness.
source = (fixtures / "run-native-beacon-test.py").read_text()
tree = ast.parse(source)
functions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)],
                       type_ignores=[])
namespace = {}
exec(compile(functions, str(fixtures / "run-native-beacon-test.py"), "exec"), namespace)
function, hooks = namespace["function"], namespace["hooks"]
old, new = (parent / "mac.c").read_text(), (child / "mac.c").read_text()
call = "gate = mt6797_data_rx_native_gate("
assert old[old.index(call):old.index(";", old.index(call))] == \
    new[new.index(call):new.index(";", new.index(call))], "ordinary decoder call changed"
comment = new.index("\n\n/* Called only after an admitted ordinary decoder call")
helper_end = new.index("\n#endif", comment)
normalized = new[:comment] + new[helper_end:]
normalized = normalized.replace(
    "\t\tunsigned int reported_idx1_translated, reported_idx1_untranslated;\n", "")
normalized = normalized.replace(function(new, "mt6797_native_diag_rx_report"),
                                function(old, "mt6797_native_diag_rx_report"))
begin = normalized.index("\t\t\t\tif (admitted) {\n")
end = normalized.index("\t\t\t\tif (nd_phase >= 0)", begin)
old_begin = old.index("\t\t\t\tif (admitted)\n")
old_end = old.index("\t\t\t\tif (nd_phase >= 0)", old_begin)
normalized = normalized[:begin] + old[old_begin:old_end] + normalized[end:]
assert normalized == old, "unexpected nonmetadata source change"

with tempfile.TemporaryDirectory(prefix="native-index-metadata-", dir="/tmp/opencode") as directory:
    tmp = Path(directory)
    outputs, errors = {}, {}
    for label, text in (("parent", old), ("child", new)):
        helper = ("static void " + function(text, "mt6797_native_diag_ordinary_record") + "\n"
                  if label == "child" else "")
        (tmp / "index-metadata-dispatch.h").write_text(helper + hooks(text))
        binary = tmp / label
        flags = ["-DMETADATA_CHILD"] if label == "child" else []
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wformat=2",
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        "-fno-pie", "-no-pie", "-I", str(tmp), "-I", str(child),
                        *flags, str(fixtures / "native-index-metadata-test.c"),
                        "-o", str(binary)], check=True, timeout=30)
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        outputs[label], errors[label] = result.stdout, result.stderr
    assert outputs["parent"] == outputs["child"], "packet decisions/queue/flags/accounting changed"
    prefix = "one-shot WLAN native RX "
    reports = {}
    for label, telemetry in errors.items():
        reports[label] = []
        for line in telemetry.splitlines():
            assert line.startswith(prefix), "unexpected metadata output"
            fields = dict(item.split("=") for item in line.split(": ", 1)[1].split())
            if "descriptor:" in line:
                allowed = {"phase", "bytes", "fields_valid", "type", "channel", "header",
                           "groups", "msdu", "status"}
                if label == "child":
                    allowed |= {"reported_index", "security_mode", "group4_valid", "fc", "ta_ap_equal"}
                assert set(fields) == allowed, "unexpected field/leak in sample"
                assert all(re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", value)
                           for value in fields.values()), "nonscalar sample"
            else:
                reports[label].append(re.sub(
                    r" reported_idx1_translated=\d+ reported_idx1_untranslated=\d+", "", line))
    assert reports["parent"] == reports["child"], "existing terminal fields changed"
    print("paired actual parent/child dispatch: identical decision/queue/bytes/flags/native/beacon/call/gate tables")
    print("actual child: first translated reported1 sample once; bounded RXD/group4 availability and metadata-only FC/TA")
    print("actual child: eight terminal lines, admitted-only index counters, inactive/beacon/blocked/failure exclusions")
    classifier = runpy.run_path(str(fixtures / "classify-native-test.py"))
    c, boot, receipt = classifier["classify"], classifier["BOOT"], classifier["receipt"]()
    telemetry = errors["child"].encode()
    for fault in (False, True):
        log = classifier["kmsg"](fault=fault)
        assert c(log, receipt, boot) == c(log + b"\n" + telemetry, receipt, boot)
    broken = classifier["kmsg"]() + b"\none-shot WLAN native-diag: state=bad"
    assert not c(broken + b"\n" + telemetry, receipt, boot)["native_delivery_pass"]
    print("original classifier: telemetry preserves exact positive/fault/malformed-line requirements")
print("native index metadata: PASS ASan/UBSan; synthetic only, no kernel build/device action")
