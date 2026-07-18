#!/usr/bin/env python3
"""Require Candidate M to remove only the optional watchdog interrupt."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import pathlib
import struct
import sys


WATCHDOG = "/watchdog@10007000"
SYSIRQ = "/interrupt-controller@10200620"
GIC = "/interrupt-controller@19000000"


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


def validate(baseline_path: pathlib.Path, candidate_path: pathlib.Path) -> None:
    fdt = load_fdt_validator()
    baseline, baseline_reservations, baseline_boot_cpu = fdt.parse_fdt(baseline_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(
        candidate_path
    )
    if candidate_reservations != baseline_reservations:
        raise ValueError("DTB reservation map changed")
    if candidate_boot_cpu != baseline_boot_cpu:
        raise ValueError("DTB boot_cpuid_phys changed")

    fdt.require_prop(
        baseline,
        WATCHDOG,
        "compatible",
        fdt.string("mediatek,mt6797-wdt") + fdt.string("mediatek,mt6589-wdt"),
    )
    fdt.require_prop(baseline, WATCHDOG, "reg", fdt.cells(0, 0x10007000, 0, 0x100))
    fdt.require_prop(baseline, WATCHDOG, "interrupts", fdt.cells(0, 137, 2))

    sysirq_phandle = one_cell(baseline[SYSIRQ].get("phandle"), f"{SYSIRQ}:phandle")
    gic_phandle = one_cell(baseline[GIC].get("phandle"), f"{GIC}:phandle")
    fdt.require_prop(baseline, "/", "interrupt-parent", fdt.cells(sysirq_phandle))
    fdt.require_prop(
        baseline,
        SYSIRQ,
        "compatible",
        fdt.string("mediatek,mt6797-sysirq")
        + fdt.string("mediatek,mt6577-sysirq"),
    )
    fdt.require_prop(baseline, SYSIRQ, "interrupt-parent", fdt.cells(gic_phandle))
    fdt.require_prop(baseline, GIC, "compatible", fdt.string("arm,gic-v3"))

    expected = copy.deepcopy(baseline)
    del expected[WATCHDOG]["interrupts"]
    compare_trees(expected, candidate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        validate(args.baseline, args.candidate)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=watchdog-registration-dtb-delta")
    print(f"watchdog_path={WATCHDOG}")
    print("baseline_interrupts=GIC_SPI-137,IRQ_TYPE_EDGE_FALLING")
    print("candidate_interrupts=absent")
    print(f"consumer_interrupt_parent={SYSIRQ}")
    print(f"sysirq_parent={GIC}")
    print("changed_properties=/watchdog@10007000:interrupts-deleted")
    print("unexpected_delta=none")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
