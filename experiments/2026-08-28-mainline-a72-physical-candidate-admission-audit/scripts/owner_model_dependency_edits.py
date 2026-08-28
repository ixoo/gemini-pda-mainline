#!/usr/bin/env python3
"""Add the base owner model required by the isolated admission fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path


KCONFIG = Path("arch/arm64/Kconfig")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()

    path = args.source_root.resolve() / KCONFIG
    text = path.read_text(encoding="utf-8")
    start = text.find("config ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST")
    end = text.find("\nconfig ", start + 1)
    require(start >= 0 and end > start, "derived KUnit Kconfig block absent")
    block = text[start:end]
    anchor = "\tselect ARM64_MT6797_A72_P24_OWNER_TEST_SEED\n"
    addition = (
        "\tselect ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL\n"
        + anchor
    )
    require(block.count(anchor) == 1, "owner test-seed anchor changed")
    require(
        "ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL" not in block,
        "base owner model already selected",
    )
    text = text[:start] + block.replace(anchor, addition, 1) + text[end:]
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
