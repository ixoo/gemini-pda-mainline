#!/usr/bin/env python3
"""Validate the isolated derived-admission KUnit dependency closure."""

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

    text = (args.source_root.resolve() / "arch/arm64/Kconfig").read_text(
        encoding="utf-8"
    )
    start = text.find("config ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST")
    end = text.find("\nconfig ", start + 1)
    require(start >= 0 and end > start, "derived KUnit Kconfig block absent")
    block = text[start:end]
    require(
        block.count(
            "\tselect ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL\n"
        ) == 1,
        "base owner model selection",
    )
    require(
        block.count("\tselect ARM64_MT6797_A72_P24_OWNER_TEST_SEED\n") == 1,
        "owner test-seed selection",
    )
    require(
        "\tselect ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST\n" not in block,
        "unrelated owner KUnit suite remains selected",
    )
    require(
        block.index("ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL")
        < block.index("ARM64_MT6797_A72_P24_OWNER_TEST_SEED"),
        "base owner model must precede its test seed",
    )
    print("dependency_validation=pass")
    print("owner_model_selected=true")
    print("owner_test_seed_selected=true")
    print("owner_kunit_suite_selected=false")
    print("production_semantics_changed=false")
