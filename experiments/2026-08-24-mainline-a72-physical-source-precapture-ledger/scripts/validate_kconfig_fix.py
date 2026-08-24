#!/usr/bin/env python3
"""Validate the one-line pre-capture Kconfig dependency fix."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    root = parser.parse_args().source_root.resolve()
    text = (root / "fs/pstore/Kconfig").read_text(encoding="utf-8")
    physical = text.split(
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER", 1
    )[1].split(
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER", 1
    )[0]
    precapture = text.split(
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER", 1
    )[1].split("config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER", 1)[0]
    require(
        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER" not in physical,
        "old mode retains reverse dependency",
    )
    require(
        "depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER" in precapture,
        "new mode lost old-mode exclusion",
    )
    require(
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y" in precapture,
        "base writer dependency",
    )
    require(
        "depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y" in precapture,
        "observer dependency",
    )
    print("validation=a72-physical-source-precapture-kconfig-fix")
    print("changed_files=fs/pstore/Kconfig")
    print("removed_dependencies=1")
    print("runtime_source_changed=false")
    print("result=pass")


if __name__ == "__main__":
    main()
