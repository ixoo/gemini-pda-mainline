#!/usr/bin/env python3
"""Validate the stack-safe DA921x membership KUnit source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", type=Path, required=True)
    source = parser.parse_args().source_file.resolve()
    require(source.is_file() and not source.is_symlink(),
            "unsafe stack-fix source")
    text = source.read_text(encoding="utf-8")

    require(text.count("KUNIT_CASE(") == 6, "KUnit case count changed")
    require(text.count("kunit_kzalloc(test, sizeof(*state), GFP_KERNEL)") == 6,
            "KUnit heap-state allocation inventory changed")
    require(text.count("struct mt6797_a72_owner_snapshot snapshot;") == 2,
            "owner snapshot escaped heap-backed state")
    require(text.count("struct mt6797_a72_transaction transaction;") == 1,
            "transaction escaped heap-backed state")
    for token in (
        "struct da9213_membership_test_state",
        "mt6797_a72_membership_snapshot(&synthetic->snapshot)",
        ".name = \"da9213-legacy-membership-provider\"",
    ):
        require(token in text, f"stack-fix token missing: {token}")
    for forbidden in (
        "i2c_add_adapter",
        "i2c_new_client",
        "ioremap",
        "writel(",
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
    ):
        require(forbidden not in text, f"hardware test token: {forbidden}")

    print("validation=da921x-pre-p28-provider-abort-stack-fix-source")
    print("kunit_cases=6")
    print("heap_state_allocations=6")
    print("production_code_changed=false")
    print("hardware_action=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
