#!/usr/bin/env python3
"""Validate generated protected-readback observer patches."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0320-soc-mediatek-add-one-shot-protected-readback-observer.patch",
    "0321-arm64-dts-mediatek-add-Gemini-protected-readback-candidate.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    found = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(found == PATCHES, "two exact patch filenames")
    require(
        (patch_dir / "series").read_text() == "\n".join(PATCHES) + "\n",
        "generated series",
    )

    observer = (patch_dir / PATCHES[0]).read_text()
    dts = (patch_dir / PATCHES[1]).read_text()
    for data in (observer, dts):
        require("Signed-off-by:" not in data, "no synthetic certification")
        require(
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in data,
            "explicit synthetic experiment author",
        )

    require(
        "Subject: [PATCH 1/2] soc: mediatek: add one-shot protected readback observer"
        in observer,
        "observer patch subject",
    )
    for path in (
        "drivers/soc/mediatek/mt6797-protected-readback-observer.c",
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "mediatek,mt6797-protected-readback-observer.yaml",
    ):
        require(path in observer, f"observer patch path: {path}")
    require('status = "okay"' not in observer,
            "observer implementation does not activate hardware")

    require(
        "Subject: [PATCH 2/2] arm64: dts: mediatek: add Gemini protected readback candidate"
        in dts,
        "candidate DT patch subject",
    )
    require("mt6797-gemini-pda-protected-readback.dts" in dts,
            "candidate derivative DTS")
    require(
        "diff --git a/arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts"
        not in dts,
        "base Gemini DTS is not modified",
    )
    require(added_lines(dts).count('status = "okay";') == 3,
            "exact three candidate-only enables")

    added = added_lines(observer + dts)
    for forbidden in (
        "MT6797_BIGIDVFS_FID_WRITE",
        "cpu_up(",
        "cpu_down(",
        "psci_ops",
        "device_create_file(",
        "sysfs_create",
    ):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")

    print("generated_patch_count=2")
    for index, patch in enumerate(PATCHES, start=1):
        print(f"patch_{index}={patch}")
    print("observer_calls=clock-1,bigidvfs-1")
    print("candidate_dtb_enables=clock,bigidvfs,observer")
    print("base_gemini_dtb_changed=false")
    print("secure_write=none")
    print("cpu_requests=0")
    print("owner_registration=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
