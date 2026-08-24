#!/usr/bin/env python3
"""Validate generated A72 physical-source patch boundaries."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0350-pstore-add-Gemini-A72-physical-source-ledger-mode.patch",
    "0351-soc-mediatek-add-A72-direct-physical-source-observer.patch",
    "0352-dt-bindings-soc-mediatek-add-A72-physical-source-observer.patch",
    "0353-arm64-dts-mediatek-add-Gemini-physical-source-candidate.patch",
    "0354-soc-mediatek-test-A72-physical-source-observer.patch",
)
EXPECTED_PATHS = (
    {
        "fs/pstore/Kconfig",
        "fs/pstore/gemini_protected_readback_ledger.c",
    },
    {
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c",
        "drivers/soc/mediatek/mt6797-a72-physical-source-observer-internal.h",
    },
    {
        "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-physical-source-observer.yaml",
    },
    {
        "arch/arm64/boot/dts/mediatek/Makefile",
        "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-a72-physical-source.dts",
    },
    {
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "drivers/soc/mediatek/mt6797-a72-physical-source-observer-test.c",
    },
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def touched_paths(patch: str) -> set[str]:
    return set(re.findall(r"^diff --git a/(.+?) b/", patch, re.MULTILINE))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    series = (patch_dir / "series").read_text(encoding="utf-8").splitlines()
    require(tuple(series) == PATCHES, "generated patch order")
    for name, expected in zip(PATCHES, EXPECTED_PATHS, strict=True):
        path = patch_dir / name
        require(path.is_file() and not path.is_symlink(), f"safe patch: {name}")
        text = path.read_text(encoding="utf-8")
        require(touched_paths(text) == expected, f"logical path boundary: {name}")
        require("Signed-off-by: Gemini Mainline Experiment" not in text,
                f"no synthetic sign-off: {name}")
        require("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
                in text, f"experiment-only author: {name}")
    combined = "".join(
        (patch_dir / name).read_text(encoding="utf-8") for name in PATCHES
    )
    for forbidden in (
        "mt6797_a72_provider_acquire(",
        "mt6797_a72_provider_release(",
        "mt6797_a72_a34_evaluate(",
        "mt6797_a72_membership_publish_up(",
        "cpu_up(",
        "cpu_down(",
        "regmap_write(",
    ):
        require(forbidden not in combined, f"forbidden generated operation: {forbidden}")
    print("validation=a72-physical-source-patches")
    print("generated_patch_count=5")
    print("logical_boundaries=ledger,observer,binding,dts,tests")
    print("synthetic_signoffs=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
