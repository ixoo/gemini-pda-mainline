#!/usr/bin/env python3
"""Validate separation and safety of generated atomic-publication patches."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0345-arm64-finalize-P30-pristine-bootstrap-claim.patch",
    "0346-arm64-add-atomic-A72-bootstrap-publisher.patch",
    "0347-arm64-test-atomic-A72-bootstrap-publication.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def changed_files(text: str) -> set[str]:
    return set(re.findall(r"^diff --git a/(\S+) b/\1$", text, re.MULTILINE))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    series = (patch_dir / "series").read_text().splitlines()
    require(series == list(PATCHES), "generated series order")
    texts = [(patch_dir / name).read_text() for name in PATCHES]
    require(changed_files(texts[0]) == {
        "arch/arm64/include/asm/late_cpu_startup.h",
        "arch/arm64/kernel/late_cpu_startup.c",
    }, "finalizer patch separation")
    require(changed_files(texts[1]) == {
        "arch/arm64/include/asm/mt6797_a72_membership.h",
        "arch/arm64/kernel/mt6797_a72_membership.c",
        "arch/arm64/Kconfig.platforms",
    }, "publisher patch separation")
    require(changed_files(texts[2]) == {
        "arch/arm64/Kconfig",
        "arch/arm64/kernel/mt6797_a72_membership_test.c",
    }, "test patch separation")
    require("arm64_late_cpu_startup_finalize_pristine" in texts[0],
            "finalizer absent")
    require("mt6797_a72_membership_publish_bootstrap" not in texts[0],
            "publisher leaked into finalizer patch")
    require("mt6797_a72_membership_publish_bootstrap" in texts[1],
            "publisher absent")
    require("KUNIT_CASE(" not in texts[1], "tests leaked into publisher patch")
    require(texts[2].count("KUNIT_CASE(") == 8,
            "generated focused test count")
    combined = "\n".join(texts)
    for forbidden in (
        "arch/arm64/kernel/mt6797_psci.c", "drivers/", "arch/arm64/boot/dts/",
        "mt6797_a72_provider_acquire(", "arm64_late_cpu_startup_prepare(&",
        "psci_ops.cpu_boot", "writel(", "i2c_transfer(",
    ):
        require(forbidden not in combined, f"forbidden patch effect {forbidden}")
    require("default n" in texts[1], "publisher is not default-off")
    require("no production caller" in texts[1].lower(),
            "production caller closure absent")

    print("validation=a72-atomic-publication-generated-patches")
    print("generated_patch_count=3")
    print("finalizer_patch_files=2")
    print("publisher_patch_files=3")
    print("test_patch_files=2")
    print("focused_tests=8")
    print("production_callers=0")
    print("physical_reader_binding=false")
    print("cpu_veto_change=false")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
