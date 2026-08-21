#!/usr/bin/env python3
"""Validate the generated canonical retained ram-console parser patch."""

from __future__ import annotations

import argparse
from pathlib import Path


EXPECTED = "0304-soc-mediatek-add-retained-ram-console-parser.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    patches = sorted(path.name for path in patch_dir.glob("*.patch"))
    require(patches == [EXPECTED], "single exact patch filename")
    require((patch_dir / "series").read_text() == EXPECTED + "\n",
            "generated series")
    data = (patch_dir / EXPECTED).read_text(encoding="utf-8")
    require(
        "Subject: [PATCH] soc: mediatek: add retained ram-console parser"
        in data,
        "patch subject",
    )
    require("Signed-off-by:" not in data, "no synthetic certification")
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
        in data,
        "synthetic experiment author is explicit",
    )
    for path in (
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "drivers/soc/mediatek/mtk-ram-console.c",
        "include/linux/soc/mediatek/mtk-ram-console.h",
    ):
        require(f"diff --git a/{path} b/{path}" in data,
                f"patch path: {path}")
    for path in (
        "arch/arm64/kernel/smp.c",
        "arch/arm64/kernel/mt6797_a72_membership.c",
        "drivers/watchdog/mtk_wdt.c",
        "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts",
    ):
        require(f"diff --git a/{path} b/{path}" not in data,
                f"forbidden production path: {path}")

    added = "\n".join(
        line[1:] for line in data.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    require(added.count("get_unaligned_le32(bytes + off_pl)") == 1,
            "one added status extraction")
    require(added.count("KUNIT_CASE(mtk_ram_console_") == 8,
            "focused test inventory")
    for forbidden in (
        "ioremap", "memremap", "readl(", "writel(", "psci_ops",
        "cpu_boot", "mt6797_a72_a34_evaluate", "reset_provenance",
        "safe_reset", "regulator_", "i2c_transfer(",
    ):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")

    print("generated_patch_count=1")
    print(f"patch={EXPECTED}")
    print("status_extractions=1")
    print("kunit_cases=8")
    print("physical_mapping=none")
    print("reset_classifier=none")
    print("a34_caller=none")
    print("hardware_action=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
