#!/usr/bin/env python3
"""Validate the generated canonical pure A34 evaluator patch."""

from __future__ import annotations

import argparse
from pathlib import Path


EXPECTED = "0302-arm64-add-A72-A34-eligibility-evaluator.patch"


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
    require("Subject: [PATCH] arm64: add A72 A34 eligibility evaluator" in data,
            "patch subject")
    require("Signed-off-by:" not in data, "no synthetic certification")
    require("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in data,
            "synthetic experiment author is explicit")
    for path in (
        "arch/arm64/Kconfig", "arch/arm64/Kconfig.platforms",
        "arch/arm64/kernel/Makefile",
        "arch/arm64/include/asm/mt6797_a72_membership.h",
        "arch/arm64/kernel/mt6797_a72_membership.c",
        "arch/arm64/kernel/mt6797_a72_a34_evaluator_test.c",
    ):
        require(f"diff --git a/{path} b/{path}" in data,
                f"patch path: {path}")
    for path in ("include/linux/cpuhotplug.h", "kernel/cpu.c",
                 "arch/arm64/kernel/smp.c"):
        require(f"diff --git a/{path} b/{path}" not in data,
                f"forbidden production path: {path}")
    added = "\n".join(
        line[1:] for line in data.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for forbidden in ("psci_ops.cpu_on", "cpu_psci_ops.cpu_boot",
                      "mt6797_a72_provider_acquire(",
                      "mt6797_a72_provider_release(", "writel(", "readl(",
                      "i2c_transfer(", "regulator_", "mutex_lock(",
                      "raw_spin_lock"):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")
    require("mt6797_a72_a34_evaluate" in added,
            "pure evaluator added")
    require("A34_ELIGIBILITY_EVALUATOR" in added,
            "default-off evaluator config added")
    require(data.count("KUNIT_CASE(mt6797_a34_") == 5,
            "focused test inventory")
    print("generated_patch_count=1")
    print(f"patch={EXPECTED}")
    print("production_hook=none")
    print("opens_owner=no")
    print("hardware_effect=no")
    print("cpu_on=no")
    print("result=pass")


if __name__ == "__main__":
    main()
