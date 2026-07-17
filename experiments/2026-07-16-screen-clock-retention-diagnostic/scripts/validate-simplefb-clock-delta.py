#!/usr/bin/env python3
"""Require exactly one simplefb backlight-clock property over Candidate E."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import pathlib
import struct
import sys


PROVIDER = "/syscon@10001000"
FRAMEBUFFER = "/chosen/framebuffer@7dfb0000"
CLK_INFRA_DISP_PWM = 45


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


def validate(baseline_path: pathlib.Path, candidate_path: pathlib.Path) -> int:
    fdt = load_fdt_validator()
    baseline, baseline_reservations, baseline_boot_cpu = fdt.parse_fdt(baseline_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(candidate_path)

    if candidate_reservations != baseline_reservations:
        raise ValueError("DTB reservation map changed")
    if candidate_boot_cpu != baseline_boot_cpu:
        raise ValueError("DTB boot_cpuid_phys changed")

    fdt.require_prop(
        baseline,
        PROVIDER,
        "compatible",
        fdt.string("mediatek,mt6797-infracfg") + fdt.string("syscon"),
    )
    fdt.require_prop(baseline, PROVIDER, "#clock-cells", fdt.cells(1))
    phandle_data = baseline[PROVIDER].get("phandle")
    if phandle_data is None or len(phandle_data) != 4:
        raise ValueError("baseline infra clock provider lacks one phandle cell")
    provider_phandle = struct.unpack(">I", phandle_data)[0]
    if provider_phandle == 0:
        raise ValueError("baseline infra clock provider has phandle zero")

    expected_framebuffer = {
        "compatible": fdt.string("simple-framebuffer"),
        "reg": fdt.cells(0, 0x7DFB0000, 0, 0x01F90000),
        "width": fdt.cells(1080),
        "height": fdt.cells(2160),
        "stride": fdt.cells(4352),
        "format": fdt.string("a8r8g8b8"),
    }
    if baseline.get(FRAMEBUFFER) != expected_framebuffer:
        raise ValueError("baseline is not the exact semantic Candidate E framebuffer")
    if "clock-names" in baseline[FRAMEBUFFER]:
        raise ValueError("baseline framebuffer unexpectedly has clock-names")

    expected = copy.deepcopy(baseline)
    expected[FRAMEBUFFER]["clocks"] = fdt.cells(
        provider_phandle, CLK_INFRA_DISP_PWM
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
            "DTB delta is not the one allowlisted clock property: "
            + "; ".join(details[:20])
        )
    return provider_phandle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        provider_phandle = validate(args.baseline, args.candidate)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=simplefb-clock-retention-delta")
    print(f"provider_path={PROVIDER}")
    print(f"provider_phandle={provider_phandle}")
    print("provider_compatible=mediatek,mt6797-infracfg,syscon")
    print("provider_clock_cells=1")
    print("clock_symbol=CLK_INFRA_DISP_PWM")
    print(f"clock_id={CLK_INFRA_DISP_PWM}")
    print(f"consumer_path={FRAMEBUFFER}")
    print("added_properties=clocks")
    print("unexpected_delta=none")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
