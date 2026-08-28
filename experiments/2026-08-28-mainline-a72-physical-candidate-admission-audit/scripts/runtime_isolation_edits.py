#!/usr/bin/env python3
"""Keep derived-admission KUnit helpers independent of the owner suite."""

from __future__ import annotations

import argparse
from pathlib import Path


KCONFIG = Path("arch/arm64/Kconfig")
STARTUP_HEADER = Path("arch/arm64/include/asm/late_cpu_startup.h")
STARTUP_SOURCE = Path("arch/arm64/kernel/late_cpu_startup.c")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    require(text.count(old) == 1, f"anchor count changed: {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    kconfig = root / KCONFIG
    text = kconfig.read_text(encoding="utf-8")
    start = text.find("config ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST")
    end = text.find("\nconfig ", start + 1)
    require(start >= 0 and end > start, "derived KUnit Kconfig block absent")
    block = text[start:end]
    old = "\tselect ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST\n"
    new = "\tselect ARM64_MT6797_A72_P24_OWNER_TEST_SEED\n"
    require(block.count(old) == 1, "owner-suite selection anchor changed")
    text = text[:start] + block.replace(old, new, 1) + text[end:]
    kconfig.write_text(text, encoding="utf-8")

    old_guard = (
        "#if defined(CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST) || \\\n"
        "\tdefined(CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST)\n"
    )
    new_guard = (
        "#if defined(CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST) || \\\n"
        "\tdefined(CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED)\n"
    )
    replace_once(root / STARTUP_HEADER, old_guard, new_guard)
    replace_once(root / STARTUP_SOURCE, old_guard, new_guard)


if __name__ == "__main__":
    main()
