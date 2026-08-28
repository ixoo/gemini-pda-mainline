#!/usr/bin/env python3
"""Validate the generated owner KUnit P30 reset-visibility patch."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATCH = "0403-arm64-expose-MT6797-A72-owner-KUnit-P30-reset.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def additions(text: str) -> tuple[str, ...]:
    return tuple(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    parser.add_argument("--canonical-import", action="store_true")
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    actual = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    if args.canonical_import:
        require(PATCH in actual, f"canonical reset-visibility patch absent: {actual}")
    else:
        require(actual == (PATCH,), f"unexpected patch inventory: {actual}")

    text = (patch_dir / PATCH).read_text(encoding="utf-8")
    require(text.startswith("From "), "output is not a format patch")
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in text,
        "synthetic archive identity changed",
    )
    require("Signed-off-by:" not in text, "synthetic sign-off forbidden")
    require(
        "Subject: [PATCH 1/1] arm64: expose P30 reset to MT6797 A72 owner KUnit" in text,
        "reset-visibility subject changed",
    )
    paths = tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))
    require(paths == (
        "arch/arm64/include/asm/late_cpu_startup.h",
        "arch/arm64/kernel/late_cpu_startup.c",
    ), f"reset-visibility paths changed: {paths}")
    added = additions(text)
    allowed = {
        "",
        "#if defined(CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST) || \\",
        "\tdefined(CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST)",
        "#endif",
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST",
    }
    require(set(added) <= allowed,
            f"non-guard addition found: {sorted(set(added) - allowed)}")
    require(added.count(
        "#if defined(CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST) || \\"
    ) == 2, "combined guard inventory changed")
    require(added.count(
        "\tdefined(CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST)"
    ) == 2, "owner guard inventory changed")
    for forbidden in (
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
        "arm_smccc_smc(",
        "readl(",
        "writel(",
        "i2c_transfer(",
    ):
        require(forbidden not in "\n".join(added),
                f"forbidden generated token: {forbidden}")

    print("validation=a72-owner-kunit-reset-visibility-patch")
    print("patches=1")
    print("changed_files=2")
    print("added_code=preprocessor-guards-only")
    print("production_configuration_change=none")
    print("physical_operations=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
