#!/usr/bin/env python3
"""Validate Candidate L's exact LK overlay and observability DT contract."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import pathlib
import struct
import sys


UART = "/serial@11002000"
PINCTRL = "/pinctrl@10005000"
UART_GROUP = f"{PINCTRL}/uart0-gemini-pins"
UART_PINS = f"{UART_GROUP}/pins-rx-tx"
RAMOOPS = "/reserved-memory/ramoops@44410000"
OLD_RAMOOPS_RESERVATION = "/reserved-memory/memory@44410000"
WATCHDOG = "/watchdog@10007000"
INFRA_PROVIDER = "/syscon@10001000"
TOP_PROVIDER = "/topckgen@10000000"
FRAMEBUFFER = "/chosen/framebuffer@7dfb0000"
CLK_INFRA_DISP_PWM = 45
CLK_TOP_MUX_MM = 6


def load_fdt_validator() -> object:
    experiments = pathlib.Path(__file__).resolve().parents[2]
    source = (
        experiments
        / "2026-07-16-lk-handoff-alignment"
        / "scripts"
        / "validate-lk-compatible-dtb.py"
    )
    spec = importlib.util.spec_from_file_location("gemini_lk_fdt_validator", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load FDT parser from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one_cell(value: bytes | None, label: str) -> int:
    if value is None or len(value) != 4:
        raise ValueError(f"{label} is not exactly one cell")
    result = struct.unpack(">I", value)[0]
    if result == 0:
        raise ValueError(f"{label} is zero")
    return result


def require_exact_node(
    tree: dict[str, dict[str, bytes]], path: str, expected: dict[str, bytes]
) -> None:
    if path not in tree:
        raise ValueError(f"missing required node {path}")
    if tree[path] != expected:
        unexpected = sorted(set(tree[path]) - set(expected))
        missing = sorted(set(expected) - set(tree[path]))
        changed = sorted(
            key
            for key in set(expected) & set(tree[path])
            if expected[key] != tree[path][key]
        )
        raise ValueError(
            f"unexpected {path} properties: missing={missing}, "
            f"unexpected={unexpected}, changed={changed}"
        )


def require_observability_contract(fdt: object, tree: dict[str, dict[str, bytes]]) -> None:
    if OLD_RAMOOPS_RESERVATION in tree:
        raise ValueError(f"obsolete node remains present: {OLD_RAMOOPS_RESERVATION}")
    require_exact_node(
        tree,
        RAMOOPS,
        {
            "compatible": fdt.string("ramoops"),
            "reg": fdt.cells(0, 0x44410000, 0, 0x000E0000),
            "record-size": fdt.cells(0x1000),
            "console-size": fdt.cells(0x10000),
            "ftrace-size": fdt.cells(0x1000),
            "pmsg-size": fdt.cells(0x20000),
            "mem-type": fdt.cells(0),
            "no-map": b"",
        },
    )

    if UART_GROUP not in tree:
        raise ValueError(f"missing board UART pin group {UART_GROUP}")
    uart_phandle = one_cell(tree[UART_GROUP].get("phandle"), f"{UART_GROUP}:phandle")
    require_exact_node(tree, UART_PINS, {"pinmux": fdt.cells(0x6101, 0x6201)})
    fdt.require_prop(tree, UART, "status", fdt.string("okay"))
    fdt.require_prop(tree, UART, "pinctrl-names", fdt.string("default"))
    fdt.require_prop(tree, UART, "pinctrl-0", fdt.cells(uart_phandle))
    fdt.require_prop(tree, "/aliases", "serial0", fdt.string(UART))
    fdt.require_prop(tree, "/chosen", "stdout-path", fdt.string("serial0:921600n8"))

    fdt.require_prop(
        tree,
        WATCHDOG,
        "compatible",
        fdt.string("mediatek,mt6797-wdt") + fdt.string("mediatek,mt6589-wdt"),
    )
    fdt.require_prop(tree, WATCHDOG, "reg", fdt.cells(0, 0x10007000, 0, 0x100))
    fdt.require_prop(tree, WATCHDOG, "interrupts", fdt.cells(0, 137, 2))


def compare_trees(
    expected: dict[str, dict[str, bytes]], actual: dict[str, dict[str, bytes]]
) -> None:
    if actual == expected:
        return
    details: list[str] = []
    for path in sorted(set(expected) | set(actual)):
        if path not in expected:
            details.append(f"unexpected node {path}")
            continue
        if path not in actual:
            details.append(f"missing node {path}")
            continue
        for prop in sorted(set(expected[path]) | set(actual[path])):
            if prop not in expected[path]:
                details.append(f"unexpected property {path}:{prop}")
            elif prop not in actual[path]:
                details.append(f"missing property {path}:{prop}")
            elif expected[path][prop] != actual[path][prop]:
                details.append(f"changed property {path}:{prop}")
    raise ValueError("DTB delta is not allowlisted: " + "; ".join(details[:24]))


def provider_phandle(
    fdt: object,
    tree: dict[str, dict[str, bytes]],
    path: str,
    compatible: bytes,
) -> int:
    fdt.require_prop(tree, path, "compatible", compatible)
    fdt.require_prop(tree, path, "#clock-cells", fdt.cells(1))
    return one_cell(tree[path].get("phandle"), f"{path}:phandle")


def validate(base_path: pathlib.Path, candidate_path: pathlib.Path) -> tuple[int, int]:
    fdt = load_fdt_validator()
    base, base_reservations, base_boot_cpu = fdt.parse_fdt(base_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(candidate_path)
    if candidate_reservations != base_reservations:
        raise ValueError("DTB reservation map changed")
    if candidate_boot_cpu != base_boot_cpu:
        raise ValueError("DTB boot_cpuid_phys changed")

    require_observability_contract(fdt, base)
    require_observability_contract(fdt, candidate)

    expected = copy.deepcopy(base)
    cpu_frequencies = {
        **{f"/cpus/cpu@{cpu:x}": 0x52E8F9C0 for cpu in range(4)},
        **{f"/cpus/cpu@{cpu:x}": 0x743AA380 for cpu in range(0x100, 0x104)},
        **{f"/cpus/cpu@{cpu:x}": 0x88601C00 for cpu in range(0x200, 0x202)},
    }
    for node, frequency in cpu_frequencies.items():
        if node not in expected or "clock-frequency" in expected[node]:
            raise ValueError(f"base has an unexpected LK frequency state at {node}")
        expected[node]["clock-frequency"] = fdt.cells(frequency)

    reserved_compatibles = {
        "/reserved-memory/memory@44600000": "mediatek,mt6797-atf-reserved-memory",
        "/reserved-memory/memory@44610000": "mediatek,mt6797-atf-ramdump-memory",
        "/reserved-memory/memory@44640000": "mediatek,cache-dump-memory",
    }
    for node, compatible in reserved_compatibles.items():
        if node not in expected or "compatible" in expected[node]:
            raise ValueError(f"base has an unexpected LK reservation state at {node}")
        expected[node]["compatible"] = fdt.string(compatible)

    scp = "/scp@10020000"
    if scp in expected:
        raise ValueError(f"base unexpectedly already has {scp}")
    expected[scp] = {
        "compatible": fdt.string("mediatek,scp"),
        "reg": fdt.cells(
            0,
            0x10020000,
            0,
            0x00080000,
            0,
            0x100A0000,
            0,
            0x00001000,
            0,
            0x100A4000,
            0,
            0x00001000,
        ),
        "interrupts": fdt.cells(0, 199, 4),
        "status": fdt.string("disabled"),
    }

    usb_nodes = (
        "/t-phy@11290000",
        "/t-phy@11290000/usb-phy@11290800",
        "/usb@11271000",
    )
    for node in usb_nodes:
        fdt.require_prop(base, node, "status", fdt.string("disabled"))
        expected[node]["status"] = fdt.string("okay")
    fdt.require_prop(
        expected, "/t-phy@11290000/usb-phy@11290900", "status", fdt.string("disabled")
    )
    fdt.require_prop(
        expected, "/usb@11271000/usb@11270000", "status", fdt.string("disabled")
    )

    infra_phandle = provider_phandle(
        fdt,
        base,
        INFRA_PROVIDER,
        fdt.string("mediatek,mt6797-infracfg") + fdt.string("syscon"),
    )
    top_phandle = provider_phandle(
        fdt, base, TOP_PROVIDER, fdt.string("mediatek,mt6797-topckgen")
    )
    chosen = "/chosen"
    if FRAMEBUFFER in base:
        raise ValueError("base unexpectedly already has the simple framebuffer")
    for prop in ("#address-cells", "#size-cells", "ranges"):
        if prop in base[chosen]:
            raise ValueError(f"base unexpectedly already has {chosen}:{prop}")
    expected[chosen]["#address-cells"] = fdt.cells(2)
    expected[chosen]["#size-cells"] = fdt.cells(2)
    expected[chosen]["ranges"] = b""
    expected[FRAMEBUFFER] = {
        "compatible": fdt.string("simple-framebuffer"),
        "reg": fdt.cells(0, 0x7DFB0000, 0, 0x01F90000),
        "width": fdt.cells(1080),
        "height": fdt.cells(2160),
        "stride": fdt.cells(4352),
        "format": fdt.string("a8r8g8b8"),
        "clocks": fdt.cells(
            infra_phandle,
            CLK_INFRA_DISP_PWM,
            top_phandle,
            CLK_TOP_MUX_MM,
        ),
    }

    for node in (
        "/dsi-phy@10215000",
        "/ovl@1400b000",
        "/ovl@1400d000",
        "/ovl@1400e000",
        "/rdma@1400f000",
        "/color@14013000",
        "/ccorr@14014000",
        "/aal@14015000",
        "/gamma@14016000",
        "/od@14017000",
        "/dither@14018000",
        "/ufoe@14019000",
        "/dsi@1401c000",
        "/dpi@1401e000",
    ):
        fdt.require_prop(candidate, node, "status", fdt.string("disabled"))

    compare_trees(expected, candidate)
    return infra_phandle, top_phandle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        infra_phandle, top_phandle = validate(args.base, args.candidate)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=uart-pstore-observability-dtb")
    print("uart0_pins=GPIO97-RX-function1,GPIO98-TX-function1")
    print("ramoops_address=0x44410000")
    print("ramoops_size=0xe0000")
    print("ramoops_record_size=0x1000")
    print("ramoops_console_size=0x10000")
    print("ramoops_ftrace_size=0x1000")
    print("ramoops_pmsg_size=0x20000")
    print("ramoops_mem_type=0")
    print("ramoops_ecc=none")
    print("watchdog_compatible=mediatek,mt6797-wdt")
    print(f"simplefb_infra_phandle={infra_phandle}")
    print(f"simplefb_top_phandle={top_phandle}")
    print("simplefb_clocks=CLK_INFRA_DISP_PWM,CLK_TOP_MUX_MM")
    print("native_display_nodes=disabled")
    print("unexpected_delta=none")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
