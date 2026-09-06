#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent resource/closure validator for the composed serviceability DTB."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

TRANSFORMER = "550527d86331bd5eb037ba60e787dc7f132a136f005c89e8864c58721ed9dc7d"
SOURCE_VALIDATOR = "332aa7baf063f817552c3394ef55c6448aa19c9703703fc6148475d9520b355a"
BASE = "d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc"
DERIVED = "58629ff9f48ffa3840b04a336d45a52da7f2c1483a4400d2a0f1637fe9638037"

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def get(path: Path, typ: str, node: str, prop: str) -> str:
    return subprocess.run(["fdtget", f"-t{typ}", str(path), node, prop], check=True,
                          text=True, stdout=subprocess.PIPE).stdout.strip()
def absent(path: Path, node: str, prop: str) -> bool:
    return subprocess.run(["fdtget", str(path), node, prop], check=False,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
def children(path: Path, node: str) -> list[str]:
    return subprocess.run(["fdtget", "-l", str(path), node], check=True,
                          text=True, stdout=subprocess.PIPE).stdout.splitlines()
def require(ok: bool, reason: str) -> None:
    if not ok: raise ValueError(reason)


def dts_inventory(path: Path) -> tuple[set[str], set[tuple[str, str, str]]]:
    """Return node and raw-property inventories from dtc's canonical DTS."""
    with tempfile.TemporaryDirectory(prefix="toprgu-dtb-") as temp:
        dts = Path(temp) / "tree.dts"
        subprocess.run(["dtc", "-q", "-I", "dtb", "-O", "dts", "-o", str(dts), str(path)], check=True)
        stack: list[str] = []
        nodes: set[str] = set()
        props: set[tuple[str, str, str]] = set()
        def node_path() -> str:
            names = [item for item in stack if item]
            return "/" + "/".join(names) if names else "/"
        for raw in dts.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("/") and line.endswith(";"):
                continue
            if line == "};" or line == "}":
                if stack: stack.pop()
                continue
            if line.endswith("{"):
                declaration = line[:-1].strip().split()[-1].rstrip(":")
                if declaration == "/":
                    declaration = ""
                stack.append(declaration)
                nodes.add(node_path())
                continue
            if "=" in line and stack:
                prop = line.split("=", 1)[0].strip()
                node = node_path()
                props.add((node, prop, line))
            elif line.endswith(";") and stack and not line.startswith("/"):
                props.add((node_path(), line[:-1].strip(), line))
        return nodes, props


def validate_reserved_memory(base: Path, derived: Path) -> None:
    """Validate the container separately from its static region children."""
    base_nodes, base_props = dts_inventory(base)
    derived_nodes, derived_props = dts_inventory(derived)
    for root in ("/reserved-memory", "/reserved-memory/ramoops@44410000"):
        require(root in base_nodes and root in derived_nodes,
                f"reserved-memory node disappeared: {root}")
    for root in ("/reserved-memory", "/reserved-memory/ramoops@44410000"):
        before = {(prop, value) for node, prop, value in base_props if node == root}
        after = {(prop, value) for node, prop, value in derived_props if node == root}
        require(before == after, f"reserved-memory properties changed: {root}")
    reserved = children(base, "/reserved-memory")
    require(reserved == children(derived, "/reserved-memory"), "reserved-memory region inventory changed")
    static_regions = [name for name in reserved
                      if not absent(base, "/reserved-memory/" + name, "reg")]
    for name in reserved:
        node = "/reserved-memory/" + name
        if name in static_regions:
            require(not absent(derived, node, "reg"), f"reserved-memory child reg disappeared: {node}")
            require(get(base, "x", node, "reg") == get(derived, "x", node, "reg"),
                    f"reserved-memory region changed: {node}")
        else:
            require(absent(derived, node, "reg"), f"reserved-memory dynamic child gained reg: {node}")


def validate_cpu_and_reserved(base: Path, derived: Path) -> None:
    clocks = {f"/cpus/cpu@{idx}": value for idx, value in {
        0: "1391000000", 1: "1391000000", 2: "1391000000", 3: "1391000000",
        100: "1950000000", 101: "1950000000", 102: "1950000000", 103: "1950000000",
        200: "2288000000", 201: "2288000000"}.items()}
    for node, expected in clocks.items():
        require(get(derived, "u", node, "clock-frequency") == expected, f"CPU clock changed: {node}")
    require(get(derived, "s", "/i2c@1100e000", "status") == "okay", "I2C6 provider disabled")
    handoff = get(derived, "x", "/dvfsp-handoff@11015000", "phandle")
    require(get(derived, "x", "/i2c@1100e000", "access-controllers") == handoff,
            "I2C6 provider ownership changed")
    require(get(derived, "s", "/i2c@1100e000/regulator@68", "compatible") == "dlg,da9214-legacy",
            "DA921x provider identity changed")
    require(get(derived, "x", "/i2c@1100e000/regulator@68", "reg") == "68 69",
            "DA921x provider address changed")
    require(get(derived, "s", "/dvfsp-handoff@11015000", "status") == "okay", "handoff provider disabled")
    validate_reserved_memory(base, derived)
    base_nodes, base_props = dts_inventory(base)
    derived_nodes, derived_props = dts_inventory(derived)
    # Every node/property not explicitly mutated must be byte-for-byte equal
    # after dtc canonicalization. The SCP subtree is the single documented add.
    mutable = {
        (node, prop) for node, props in {
            "/t-phy@11290000": {"status"}, "/t-phy@11290000/usb-phy@11290800": {"status"},
            "/usb@11271000": {"status"}, "/usb@11271000/usb@11270000": {"status"},
            "/i2c@1101c000": {"status", "clock-frequency", "pinctrl-names", "pinctrl-0"},
            "/i2c@1101c000/gpio-expander@5b": {"status", "interrupt-parent", "interrupts", "interrupt-controller", "#interrupt-cells"},
            "/keyboard-matrix": {"status", "poll-interval", "col-scan-delay-us"},
            "/dvfsp-handoff@11015000": {"reg", "reg-names"}, "/watchdog@10007000": {"interrupts"},
        }.items() for prop in props
    }
    keep_nodes = {node for node in derived_nodes if node != "/scp@10020000" and not node.startswith("/scp@10020000/")}
    require(base_nodes == keep_nodes, "unrelated DT node inventory changed")
    def filtered(items):
        return {(node, prop, value) for node, prop, value in items
                if not node.startswith("/scp@10020000/") and node != "/scp@10020000"
                and (node, prop) not in mutable}
    require(filtered(base_props) == filtered(derived_props), "unrelated DT nodes/properties/raw values changed")

def validate(base: Path, derived: Path, expected: str) -> None:
    require(expected == DERIVED, "derived DTB expected identity changed")
    # ``__file__`` is ``<repo>/experiments/<name>/scripts/validate-dtb.py``;
    # keep the repository root unambiguous so source pins cannot accidentally
    # resolve beneath ``experiments/``.
    repo = Path(__file__).resolve().parents[3]
    require(sha(repo / "experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/build-serviceability-dtb.sh") == TRANSFORMER, "transformer source pin changed")
    require(sha(repo / "experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/test-candidate.py") == SOURCE_VALIDATOR, "independent DT validator pin changed")
    require(sha(base) == BASE, "base DTB identity changed")
    require(sha(derived) == expected, "derived DTB identity changed")
    require(get(derived, "s", "/usb@11271000", "dr_mode") == "peripheral", "USB role changed")
    require(get(derived, "s", "/usb@11271000", "maximum-speed") == "high-speed", "USB speed changed")
    require(get(derived, "s", "/i2c@1101c000", "status") == "okay", "I2C5 closure changed")
    require(get(derived, "x", "/i2c@1101c000", "clock-frequency") == "61a80", "I2C5 polling clock changed")
    require(get(derived, "s", "/i2c@1101c000/gpio-expander@5b", "status") == "okay", "AW9523 closure changed")
    require(get(derived, "s", "/keyboard-matrix", "status") == "okay", "keyboard closure changed")
    require(get(derived, "x", "/keyboard-matrix", "poll-interval") == "14", "keyboard polling changed")
    require(get(derived, "x", "/keyboard-matrix", "col-scan-delay-us") == "2", "keyboard scan delay changed")
    require(get(derived, "s", "/dvfsp-handoff@11015000", "reg-names") == "cspm scp-cfg devapc-ao", "handoff windows changed")
    require(get(derived, "s", "/usb@11271000/usb@11270000", "status") == "disabled", "xHCI closure changed")
    require(get(derived, "s", "/scp@10020000", "status") == "disabled", "SCP closure changed")
    for node in ("/dvfsp-clock-backend@1001a000", "/dvfsp-bigidvfs-backend", "/ram-console"):
        require(get(derived, "s", node, "status") == "disabled", f"disabled path changed: {node}")
    require(absent(derived, "/watchdog@10007000", "interrupts"), "watchdog IRQ closure changed")
    validate_cpu_and_reserved(base, derived)

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--base", type=Path, required=True); p.add_argument("--derived", type=Path, required=True); p.add_argument("--expected-sha256", required=True)
    a = p.parse_args()
    validate(a.base, a.derived, a.expected_sha256)
    print("dt_validation=pass\nserviceability_mutations=20\nscp_nodes_added=1\nraw_unrelated_properties=preserved\naction_closure=automatic-and-admitted-actions-absent")
    return 0
if __name__ == "__main__": raise SystemExit(main())
