#!/usr/bin/env python3
"""Validate the owner KUnit P30 reset-visibility source repair."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


HEADER = Path("arch/arm64/include/asm/late_cpu_startup.h")
SOURCE = Path("arch/arm64/kernel/late_cpu_startup.c")
OWNER_TEST = Path("arch/arm64/kernel/mt6797_a72_membership_test.c")
COMBINED_GUARD = (
    "#if defined(CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST) || \\\n"
    "\tdefined(CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST)\n"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    paths = (root / HEADER, root / SOURCE, root / OWNER_TEST)
    for path in paths:
        require(path.is_file() and not path.is_symlink(),
                f"source absent or unsafe: {path}")
    header, source, owner_test = (
        path.read_text(encoding="utf-8") for path in paths
    )

    require(header.count(COMBINED_GUARD) == 1,
            "header reset guard changed")
    require(source.count(COMBINED_GUARD) == 1,
            "source reset guard changed")
    require(header.count("void arm64_late_cpu_startup_test_reset(void);") == 1,
            "reset declaration inventory changed")
    require(source.count("void arm64_late_cpu_startup_test_reset(void)\n") == 1,
            "reset definition inventory changed")
    narrow_guard = (
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST\n"
        "void arm64_late_cpu_startup_test_set_online"
    )
    require(header.count(narrow_guard) == 1,
            "header set-online guard widened")
    require(source.count(narrow_guard) == 1,
            "source set-online guard widened")
    require(owner_test.count("arm64_late_cpu_startup_test_reset();") == 4,
            "owner reset call inventory changed")
    cases = re.findall(r"KUNIT_CASE\((mt6797_a72_owner_[a-z0-9_]+)\)",
                       owner_test)
    require(len(cases) == 30 and len(set(cases)) == 30,
            f"owner case inventory changed: {len(cases)}")

    print("validation=a72-owner-kunit-reset-visibility-source")
    print("changed_files=2")
    print("owner_cases=30")
    print("owner_reset_calls=4")
    print("production_configuration_change=none")
    print("physical_operations=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
