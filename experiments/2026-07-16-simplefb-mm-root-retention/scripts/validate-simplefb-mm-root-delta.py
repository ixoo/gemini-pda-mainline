#!/usr/bin/env python3
"""Require exactly one appended MT6797 MM-root clock on Candidate G."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import pathlib
import struct
import sys


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


def provider_phandle(fdt: object, tree: dict, path: str, compatible: bytes) -> int:
    fdt.require_prop(tree, path, "compatible", compatible)
    fdt.require_prop(tree, path, "#clock-cells", fdt.cells(1))
    value = tree[path].get("phandle")
    if value is None or len(value) != 4:
        raise ValueError(f"{path} lacks one phandle cell")
    phandle = struct.unpack(">I", value)[0]
    if phandle == 0:
        raise ValueError(f"{path} has phandle zero")
    return phandle


def validate(baseline_path: pathlib.Path, candidate_path: pathlib.Path) -> tuple[int, int]:
    fdt = load_fdt_validator()
    baseline, baseline_reservations, baseline_boot_cpu = fdt.parse_fdt(baseline_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(candidate_path)

    if candidate_reservations != baseline_reservations:
        raise ValueError("DTB reservation map changed")
    if candidate_boot_cpu != baseline_boot_cpu:
        raise ValueError("DTB boot_cpuid_phys changed")

    infra_phandle = provider_phandle(
        fdt,
        baseline,
        INFRA_PROVIDER,
        fdt.string("mediatek,mt6797-infracfg") + fdt.string("syscon"),
    )
    top_phandle = provider_phandle(
        fdt,
        baseline,
        TOP_PROVIDER,
        fdt.string("mediatek,mt6797-topckgen"),
    )

    expected_framebuffer = {
        "compatible": fdt.string("simple-framebuffer"),
        "reg": fdt.cells(0, 0x7DFB0000, 0, 0x01F90000),
        "width": fdt.cells(1080),
        "height": fdt.cells(2160),
        "stride": fdt.cells(4352),
        "format": fdt.string("a8r8g8b8"),
        "clocks": fdt.cells(infra_phandle, CLK_INFRA_DISP_PWM),
    }
    if baseline.get(FRAMEBUFFER) != expected_framebuffer:
        raise ValueError("baseline is not the exact semantic Candidate G framebuffer")
    if "clock-names" in baseline[FRAMEBUFFER]:
        raise ValueError("baseline framebuffer unexpectedly has clock-names")

    expected = copy.deepcopy(baseline)
    expected[FRAMEBUFFER]["clocks"] = fdt.cells(
        infra_phandle,
        CLK_INFRA_DISP_PWM,
        top_phandle,
        CLK_TOP_MUX_MM,
    )
    if candidate != expected:
        details: list[str] = []
        for path in sorted(set(expected) | set(candidate)):
            if path not in expected:
                details.append(f"unexpected node {path}")
                continue
            if path not in candidate:
                details.append(f"missing node {path}")
                continue
            expected_props = expected[path]
            actual_props = candidate[path]
            for prop in sorted(set(expected_props) | set(actual_props)):
                if prop not in expected_props:
                    details.append(f"unexpected property {path}:{prop}")
                elif prop not in actual_props:
                    details.append(f"missing property {path}:{prop}")
                elif expected_props[prop] != actual_props[prop]:
                    details.append(f"changed property {path}:{prop}")
        raise ValueError(
            "DTB delta is not the one allowlisted appended clock: "
            + "; ".join(details[:20])
        )
    return infra_phandle, top_phandle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        infra_phandle, top_phandle = validate(args.baseline, args.candidate)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=simplefb-mm-root-retention-delta")
    print(f"infra_provider_path={INFRA_PROVIDER}")
    print(f"infra_provider_phandle={infra_phandle}")
    print(f"top_provider_path={TOP_PROVIDER}")
    print(f"top_provider_phandle={top_phandle}")
    print("top_provider_compatible=mediatek,mt6797-topckgen")
    print("provider_clock_cells=1")
    print("existing_clock_symbol=CLK_INFRA_DISP_PWM")
    print(f"existing_clock_id={CLK_INFRA_DISP_PWM}")
    print("added_clock_symbol=CLK_TOP_MUX_MM")
    print(f"added_clock_id={CLK_TOP_MUX_MM}")
    print(f"consumer_path={FRAMEBUFFER}")
    print("changed_properties=clocks")
    print("unexpected_delta=none")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
