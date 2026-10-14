#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual-source stable-epoch callbacks and original-native equivalence; no device."""
import argparse
import ast
import re
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
old, new = (parent / "mac.c").read_text(), (child / "mac.c").read_text()


def without_stable(text):
    result, depth = [], 0
    for line in text.splitlines():
        if depth:
            if line.startswith(("#if ", "#ifdef ", "#ifndef ")):
                depth += 1
            elif line.startswith("#endif"):
                depth -= 1
            continue
        if line == "#ifdef CONFIG_MT6797_CCMP_STABLE_EPOCH":
            depth = 1
        elif line.strip():
            result.append(line)
    assert not depth
    return result


assert without_stable(new) == [line for line in old.splitlines() if line.strip()], \
    "original source changed outside new CONFIG guard"
for p in parent.iterdir():
    if p.is_file() and p.name not in {"mac.c", "Kconfig"}:
        assert (child / p.name).read_bytes() == p.read_bytes(), p.name
assert (child / "Kconfig").read_text().startswith((parent / "Kconfig").read_text())

def matching_endif(text, start):
    depth = 0
    for match in re.finditer(r"(?m)^#(if[^\n]*|endif[^\n]*)$", text[start:]):
        if match[1].startswith("if"):
            depth += 1
        elif depth:
            depth -= 1
        else:
            return start + match.start() - 1
    raise AssertionError("missing outer endif")


extractors = (fixtures / "run-native-beacon-test.py").read_text().replace(
    'text.index("\\n#endif", native_start)', 'matching_endif(text, native_start)').replace(
    'text.index("\\n#endif", account_start)', 'matching_endif(text, account_start)')
tree = ast.parse(extractors)
ns = {"matching_endif": matching_endif}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)],
                        type_ignores=[]), "existing-extractors", "exec"), ns)
def function(text, name):
    # The shared extractor expects a definition, not an earlier prototype.
    match = re.search(r"\b" + re.escape(name) + r"\([^;]*?\)\n\{", text)
    assert match, name
    return ns["function"](text[match.start():], name)
with tempfile.TemporaryDirectory(prefix="ccmp-monitor-", dir="/tmp/opencode") as directory:
    tmp = Path(directory)
    start = new.index("struct mt6797_mac {")
    end = new.index("\n};", start) + 3
    names = [
        ("void", "mt6797_ccmp_withdraw"), ("bool", "mt6797_ccmp_rx_ready"),
        ("void", "mt6797_ccmp_receive"), ("void", "mt6797_mac_sta_set_decap_offload"),
        ("int", "mt6797_ccmp_queue_rx"),
        ("void", "mt6797_native_diag_rx_report"), ("int", "mt6797_mac_join_fail_stop"),
        ("int", "mt6797_ccmp_disable_key"), ("int", "mt6797_mac_set_key"),
        ("int", "mt6797_mac_sta_state"),
        ("int", "mt6797_native_diag_pre_read"),
        ("void", "mt6797_native_diag_ordinary_record"),
        ("void", "mt6797_mac_tx"),
        ("void", "mt6797_native_diag_step"),
        ("bool", "mt6797_native_diag_tx_fenced"),
    ]
    (tmp / "actual-ccmp-monitor.inc").write_text(new[start:end] + "\n" + "\n".join(
        "#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored \"-Wunused-parameter\"\n" +
        "static " + result + " " + function(new, name) + "\n#pragma GCC diagnostic pop"
        for result, name in names))
    event = new.index("\tif (mt6797_join_event(mac->join_packet, bytes, 0x24, 8))")
    event_end = new.index("\n\tif (mt6797_join_event(mac->join_packet, bytes, 0x11", event)
    event_body = new[event:event_end].rsplit("\n#endif", 1)[0]
    (tmp / "actual-key-event.inc").write_text(
        "static int owned_key_event(struct mt6797_mac *mac, size_t bytes) {\n" +
        event_body + "\nreturn -EINVAL; }\n")
    (tmp / "parent-monitor-step.inc").write_text("static void " +
        function(old, "mt6797_native_diag_step").replace(
            "mt6797_native_diag_step(", "parent_monitor_step(", 1) + "\n")
    dispatch = ns["hooks"](new)
    dispatch = dispatch.replace(
        "static void " + function(new, "mt6797_native_diag_rx_report") + "\n", "")
    (tmp / "actual-dispatch.inc").write_text(dispatch)
    baseline = (fixtures / "ccmp-rx-test.c").read_text()
    baseline = baseline.replace(
        '"../../2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c"',
        '"' + str(fixtures.parents[1] / "2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c") + '"')
    baseline = baseline.replace("int main(void)", "int offline_helper_tests(void)")
    (tmp / "helper-fixture.inc").write_text(baseline)
    native = (fixtures / "native-rx-test.c").read_text().replace(
        "int main(void)", "int native_layout_tests(void)")
    (tmp / "native-fixture.inc").write_text(
        "#define own native_own\n#define ap native_ap\n" + native + "\n#undef own\n#undef ap\n")
    binary = tmp / "test"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wformat=2",
                    "-pthread", "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-fno-pie", "-no-pie", "-I", str(tmp), "-I", str(child),
                    str(fixtures / "ccmp-monitor-state-test.c"), "-o", str(binary)],
                   check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)
print("original native source: byte-identical after excluding new CONFIG blocks; other driver files unchanged")
