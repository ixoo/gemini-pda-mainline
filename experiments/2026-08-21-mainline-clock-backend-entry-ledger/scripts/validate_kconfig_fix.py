#!/usr/bin/env python3
"""Validate the parent or corrected clock-entry ledger Kconfig contract."""

from __future__ import annotations

import argparse
from pathlib import Path


OLD = "depends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y"
NEW = OLD + " || MTK_MT6797_DVFSP_CLOCK_BACKEND=y"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def body(text: str, start: str, end: str) -> str:
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--state", choices=("parent", "corrected"), required=True)
    args = parser.parse_args()
    kconfig = (
        args.source_root.resolve() / "fs/pstore/Kconfig"
    ).read_text(encoding="utf-8")
    base = body(
        kconfig,
        "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER",
        "config PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",
    )
    mode = body(
        kconfig,
        "config PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",
        "config PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT",
    )

    require("default n" in base, "base writer remains opt-in")
    require("depends on PSTORE_RAM=y" in base, "base pstore dependency retained")
    require("depends on ARM64 && ARCH_MEDIATEK && OF" in base,
            "base architecture dependencies retained")
    require("depends on !PSTORE_GEMINI_PRE_RAMOOPS_LEDGER" in base,
            "pre-ramoops exclusion retained")
    require("depends on !PSTORE_GEMINI_ARM64_ENTRY_LEDGER" in base,
            "arm64-entry exclusion retained")
    require("depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y" in mode,
            "mode still requires base writer")
    require("depends on MTK_MT6797_DVFSP_CLOCK_BACKEND=y" in mode,
            "mode still requires built-in clock backend")
    require("depends on !PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER" in mode,
            "historical probe/gate mode remains excluded")

    if args.state == "parent":
        require(OLD in base and NEW not in base,
                "parent has the observer-only dependency")
    else:
        require(NEW in base, "corrected dependency contains both exact callers")
        require(base.count("MTK_MT6797_DVFSP_CLOCK_BACKEND") == 1,
                "one clock-backend alternative added")
        require(base.count("MTK_MT6797_PROTECTED_READBACK_OBSERVER") == 1,
                "one historical observer dependency retained")

    print(f"kconfig_fix_validation={args.state}:pass")
    print("base_writer_default=n")
    print("runtime_code_changes=0")


if __name__ == "__main__":
    main()
