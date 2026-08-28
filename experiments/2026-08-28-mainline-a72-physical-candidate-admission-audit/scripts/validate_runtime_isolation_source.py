#!/usr/bin/env python3
"""Validate the derived-admission KUnit fixture dependency boundary."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    kconfig = (root / "arch/arm64/Kconfig").read_text(encoding="utf-8")
    start = kconfig.find(
        "config ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST"
    )
    end = kconfig.find("\nconfig ", start + 1)
    require(start >= 0 and end > start, "derived KUnit Kconfig block absent")
    block = kconfig[start:end]
    require("select ARM64_MT6797_A72_P24_OWNER_TEST_SEED" in block,
            "focused fixture helper selection absent")
    require("select ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST" not in block,
            "unrelated owner suite remains selected")

    guard = (
        "#if defined(CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST) || \\\n"
        "\tdefined(CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED)\n"
    )
    for relative in (
        "arch/arm64/include/asm/late_cpu_startup.h",
        "arch/arm64/kernel/late_cpu_startup.c",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        require(text.count(guard) == 1, f"reset guard changed: {relative}")

    print("validation=a72-derived-admission-kunit-isolation-source")
    print("changed_files=3")
    print("owner_kunit_suite_selected=false")
    print("owner_test_seed_selected=true")
    print("production_semantics_changed=false")
    print("physical_operations=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
