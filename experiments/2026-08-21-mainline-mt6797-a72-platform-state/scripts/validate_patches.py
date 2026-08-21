#!/usr/bin/env python3
"""Validate generated MT6797 A72 platform-state patches."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0308-watchdog-mtk-expose-locked-reset-status.patch",
    "0309-dt-bindings-soc-mediatek-add-MT6797-A72-platform-state.patch",
    "0310-soc-mediatek-add-MT6797-A72-platform-state-source.patch",
    "0311-arm64-dts-mediatek-add-MT6797-A72-platform-state-source.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    found = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(found == PATCHES, "four exact patch filenames")
    require((patch_dir / "series").read_text() == "\n".join(PATCHES) + "\n",
            "generated series")

    watchdog = (patch_dir / PATCHES[0]).read_text()
    binding = (patch_dir / PATCHES[1]).read_text()
    platform = (patch_dir / PATCHES[2]).read_text()
    devicetree = (patch_dir / PATCHES[3]).read_text()
    for data in (watchdog, binding, platform, devicetree):
        require("Signed-off-by:" not in data, "no synthetic certification")
        require(
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in data,
            "synthetic experiment author is explicit",
        )

    require("Subject: [PATCH 1/4] watchdog: mtk: expose locked reset status" in watchdog,
            "watchdog patch subject")
    require("diff --git a/drivers/watchdog/mtk_wdt.c" in watchdog,
            "watchdog path")
    require("drivers/soc/mediatek" not in watchdog,
            "watchdog patch is logically isolated")

    binding_path = (
        "Documentation/devicetree/bindings/soc/mediatek/"
        "mediatek,mt6797-a72-platform-state.yaml"
    )
    require(
        "Subject: [PATCH 2/4] dt-bindings: mediatek: add MT6797 A72 state "
        "source" in binding,
        "binding patch subject",
    )
    require(f"diff --git a/{binding_path} b/{binding_path}" in binding,
            "binding patch path")
    require("drivers/soc/mediatek" not in binding and
            "arch/arm64/boot/dts" not in binding,
            "binding patch is logically isolated")

    require(
        "Subject: [PATCH 3/4] soc: mediatek: add MT6797 A72 state source"
        in platform,
        "platform driver patch subject",
    )
    for path in (
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "drivers/soc/mediatek/mt6797-a72-platform-state.c",
        "include/linux/soc/mediatek/mt6797-a72-platform-state.h",
    ):
        require(f"diff --git a/{path} b/{path}" in platform,
                f"platform driver patch path: {path}")
    require(binding_path not in platform and
            "arch/arm64/boot/dts" not in platform and
            "drivers/watchdog/mtk_wdt.c" not in platform,
            "platform driver patch is logically isolated")

    require(
        "Subject: [PATCH 4/4] arm64: dts: mediatek: add MT6797 A72 state "
        "source" in devicetree,
        "devicetree patch subject",
    )
    for path in (
        "arch/arm64/boot/dts/mediatek/mt6797.dtsi",
        "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts",
    ):
        require(f"diff --git a/{path} b/{path}" in devicetree,
                f"devicetree patch path: {path}")
    require("drivers/soc/mediatek" not in devicetree and
            binding_path not in devicetree,
            "devicetree patch is logically isolated")

    added = added_lines(watchdog + binding + platform + devicetree)
    for forbidden in (
        "writel(", "writeb(", "writew(", "regmap_write(",
        "reset_control_assert(", "reset_control_deassert(",
        "readl_poll", "regmap_read_poll", "cpu_up(", "cpu_down(",
        "mt6797_a72_a34", "psci_ops", "status = \"okay\"",
    ):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")

    print("generated_patch_count=4")
    for index, patch in enumerate(PATCHES, start=1):
        print(f"patch_{index}={patch}")
    print("toprgu_status=locked-read-only")
    print("platform_state=default-off-capture-only")
    print("hardware_write=none")
    print("a34_caller=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
