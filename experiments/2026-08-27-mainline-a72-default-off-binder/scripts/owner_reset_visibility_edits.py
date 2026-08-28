#!/usr/bin/env python3
"""Expose the existing P30 reset to the MT6797 A72 owner KUnit suite."""

from __future__ import annotations

import argparse
from pathlib import Path


HEADER = Path("arch/arm64/include/asm/late_cpu_startup.h")
SOURCE = Path("arch/arm64/kernel/late_cpu_startup.c")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text.count(old) == 1, f"{label} anchor count changed")
    return text.replace(old, new, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    header_path = root / HEADER
    source_path = root / SOURCE
    for path in (header_path, source_path):
        require(path.is_file() and not path.is_symlink(),
                f"source absent or unsafe: {path}")

    header = header_path.read_text(encoding="utf-8")
    header = replace_once(
        header,
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST\n"
        "void arm64_late_cpu_startup_test_reset(void);\n"
        "void arm64_late_cpu_startup_test_set_online(u32 cpu, bool online);\n"
        "#endif\n",
        "#if defined(CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST) || \\\n"
        "\tdefined(CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST)\n"
        "void arm64_late_cpu_startup_test_reset(void);\n"
        "#endif\n"
        "\n"
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST\n"
        "void arm64_late_cpu_startup_test_set_online(u32 cpu, bool online);\n"
        "#endif\n",
        "header test reset guard",
    )

    source = source_path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST\n"
        "void arm64_late_cpu_startup_test_reset(void)\n",
        "#if defined(CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST) || \\\n"
        "\tdefined(CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST)\n"
        "void arm64_late_cpu_startup_test_reset(void)\n",
        "reset definition guard",
    )
    source = replace_once(
        source,
        "\traw_spin_unlock_irqrestore(&late_startup.lock, flags);\n"
        "}\n"
        "\n"
        "void arm64_late_cpu_startup_test_set_online(u32 cpu, bool online)\n",
        "\traw_spin_unlock_irqrestore(&late_startup.lock, flags);\n"
        "}\n"
        "#endif\n"
        "\n"
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST\n"
        "void arm64_late_cpu_startup_test_set_online(u32 cpu, bool online)\n",
        "set-online guard split",
    )

    header_path.write_text(header, encoding="utf-8")
    source_path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
