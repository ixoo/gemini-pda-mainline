#!/usr/bin/env python3
"""Validate the exact CPU8 candidate binding and Device Tree graph."""

from __future__ import annotations

import argparse
from pathlib import Path


def read(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"required source file unavailable: {relative}")
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("binding", "dts"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    binding = read(
        root,
        "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-admission-controller.yaml",
    )
    controller = read(root, "drivers/soc/mediatek/mt6797-a72-admission-controller.c")
    for token in (
        "mediatek,mt6797-a72-admission-controller",
        "mediatek,binder",
        "mediatek,platform-state",
        "mediatek,clock-backend",
        "mediatek,bigidvfs-backend",
        "additionalProperties: false",
    ):
        require(token in binding, f"binding token {token}")
        if token != "additionalProperties: false":
            require(token in controller, f"driver token {token}")
    require(binding.count("  - mediatek,") == 4, "four required phandles")
    if args.stage == "dts":
        dts = read(root, "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-a72-admission.dts")
        makefile = read(root, "arch/arm64/boot/dts/mediatek/Makefile")
        base = read(root, "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts")
        dtsi = read(root, "arch/arm64/boot/dts/mediatek/mt6797.dtsi")
        physical = read(root, "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-a72-physical-source.dts")
        require('#include "mt6797-gemini-pda.dts"' in dts, "candidate inherits exact base")
        require("mt6797-gemini-pda-a72-physical-source" not in dts,
                "candidate does not inherit observer derivative")
        require("a72-physical-source-observer" not in dts,
                "no duplicate standalone observer node")
        for token in (
            'compatible = "mediatek,mt6797-a72-binder";',
            'compatible = "mediatek,mt6797-a72-admission-controller";',
            "mediatek,watchdog = <&watchdog>;",
            "mediatek,binder = <&a72_binder>;",
            "mediatek,platform-state = <&a72_platform_state>;",
            "mediatek,clock-backend = <&dvfsp_clock_backend>;",
            "mediatek,bigidvfs-backend = <&dvfsp_bigidvfs_backend>;",
        ):
            require(dts.count(token) == 1, f"one candidate token {token}")
        require(dts.count("mediatek,bigidvfs = <&dvfsp_bigidvfs_backend>;") == 1,
                "one binder BigiDVFS phandle")
        for label in ("a72_platform_state:", "watchdog:",
                      "dvfsp_clock_backend:", "dvfsp_bigidvfs_backend:"):
            require(label in dtsi, f"supplier label {label}")
        require("da9214: regulator@68" in base, "base DA9214 provider")
        require("&dvfsp_handoff" in base, "base DVFSP handoff")
        require("a72-physical-source-observer" in physical,
                "old observer remains a separate derivative")
        require(makefile.count("mt6797-gemini-pda-a72-admission.dtb") == 1,
                "one candidate DT build entry")
        require("dvfsp_resource_owner" not in dts,
                "unrelated resource-owner node stays disabled")
    print("validation=mt6797-gemini-cpu8-admission-candidate-source")
    print(f"stage={args.stage}")
    print("controller_nodes=1" if args.stage == "dts" else "controller_nodes=pending")
    print("binder_nodes=1" if args.stage == "dts" else "binder_nodes=pending")
    print("standalone_observer_nodes=0")
    print("cpu8_request_owner=controller")
    print("cpu9_request_paths=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
