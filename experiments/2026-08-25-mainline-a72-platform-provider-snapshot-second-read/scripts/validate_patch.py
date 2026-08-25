#!/usr/bin/env python3
"""Validate the generated platform/provider format-patch set."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0367-pstore-add-Gemini-A72-platform-provider-ledger.patch",
    "0368-soc-mediatek-add-A72-platform-provider-snapshot-observer.patch",
    "0369-dt-bindings-soc-mediatek-add-A72-platform-provider-snapshot-observer.patch",
    "0370-soc-mediatek-test-A72-platform-provider-snapshot-observer.patch",
)

EXPECTED_PATHS = {
    PATCHES[0]: {
        "fs/pstore/Kconfig",
        "fs/pstore/gemini_protected_readback_ledger.c",
    },
    PATCHES[1]: {
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer.c",
        "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer-internal.h",
    },
    PATCHES[2]: {
        "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-platform-provider-snapshot-observer.yaml",
    },
    PATCHES[3]: {
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer-test.c",
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def changed_paths(text: str) -> set[str]:
    paths: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("diff --git a/"):
            continue
        left, right = line[len("diff --git ") :].split(" b/", 1)
        require(left.startswith("a/"), "malformed diff left path")
        require(left[2:] == right, "rename or path mismatch is prohibited")
        paths.add(right)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    series = (patch_dir / "series").read_text(encoding="utf-8").splitlines()
    require(tuple(series) == PATCHES, "exact four-patch series order")
    actual = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(actual == PATCHES, "exact generated patch inventory")

    for patch in PATCHES:
        text = (patch_dir / patch).read_text(encoding="utf-8")
        require(text.startswith("From "), f"format-patch header: {patch}")
        require(
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in text,
            f"synthetic experiment author: {patch}",
        )
        require("Signed-off-by:" not in text, f"synthetic sign-off absent: {patch}")
        require(
            changed_paths(text) == EXPECTED_PATHS[patch],
            f"exact changed-file boundary: {patch}",
        )
        for forbidden in (
            "cpu_up(",
            "cpu_down(",
            "arm_smccc_smc(",
            "regmap_write(",
            "mt6797_dvfsp_clock_backend_read(",
            "mt6797_bigidvfs_backend_read(",
            "mt6797_a72_provider_acquire(",
            "mt6797_a72_provider_release(",
        ):
            require(forbidden not in text, f"forbidden token {forbidden}: {patch}")
    observer = (patch_dir / PATCHES[1]).read_text(encoding="utf-8")
    require(
        observer.count("mt6797_a72_provider_snapshot(") == 1,
        "one provider snapshot call in observer patch",
    )
    print("patch_validation=pass")


if __name__ == "__main__":
    main()
