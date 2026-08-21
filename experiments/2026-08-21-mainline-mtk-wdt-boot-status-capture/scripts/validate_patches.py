#!/usr/bin/env python3
"""Validate the generated canonical boot-status capture patch."""

from __future__ import annotations

import argparse
from pathlib import Path


EXPECTED = "0303-watchdog-mtk-capture-raw-boot-status.patch"


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
    require("Subject: [PATCH] watchdog: mtk: capture raw boot status" in data,
            "patch subject")
    require("Signed-off-by:" not in data, "no synthetic certification")
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
        in data,
        "synthetic experiment author is explicit",
    )
    for path in (
        "drivers/watchdog/Kconfig",
        "drivers/watchdog/mtk_wdt.c",
        "include/linux/mtk_wdt.h",
    ):
        require(f"diff --git a/{path} b/{path}" in data,
                f"patch path: {path}")
    for path in (
        "arch/arm64/kernel/smp.c",
        "arch/arm64/kernel/mt6797_a72_membership.c",
        "drivers/regulator/da9211-regulator.c",
    ):
        require(f"diff --git a/{path} b/{path}" not in data,
                f"forbidden production path: {path}")
    added = "\n".join(
        line[1:] for line in data.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    require(added.count("readl(mtk_wdt->wdt_base + WDT_STATUS)") == 1,
            "single added status read")
    for forbidden in (
        "reset_provenance", "safe_reset", "psci_ops", "cpu_boot",
        "mt6797_a72_a34_evaluate", "mt6797_a72_provider_acquire",
        "i2c_transfer(", "regulator_", "writel(", "iowrite",
    ):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")
    require(data.count("KUNIT_CASE(mtk_wdt_boot_status_") == 4,
            "focused test inventory")
    print("generated_patch_count=1")
    print(f"patch={EXPECTED}")
    print("status_reads=1")
    print("reset_classifier=none")
    print("a34_caller=none")
    print("hardware_write=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
