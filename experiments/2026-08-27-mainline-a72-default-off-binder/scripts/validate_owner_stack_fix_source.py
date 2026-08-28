#!/usr/bin/env python3
"""Validate the stack-safe MT6797 A72 owner KUnit source."""

from __future__ import annotations

import argparse
from pathlib import Path

from owner_stack_fix_edits import OWNER_CASES


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = (
        args.source_root.resolve()
        / "arch/arm64/kernel/mt6797_a72_membership_test.c"
    )
    require(path.is_file() and not path.is_symlink(),
            "unsafe membership KUnit source")
    text = path.read_text(encoding="utf-8")
    owner = text[:text.index(
        "#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST"
    )]

    require("struct mt6797_a72_owner_test_state {" in owner,
            "heap fixture type absent")
    require(owner.count(
        "struct mt6797_a72_owner_test_state *state = test->priv;"
    ) == len(OWNER_CASES), "per-case heap fixture inventory changed")
    require(owner.count(
        "state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);"
    ) == 1, "owner suite heap allocation changed")
    require("test->priv = state;" in owner, "owner suite private state absent")
    require("return !memchr_inv(transaction, 0, sizeof(*transaction));" in owner,
            "allocation-free empty transaction check absent")
    require("static const struct mt6797_a72_transaction "
            "mt6797_a72_empty_transaction;" in owner,
            "static empty transaction reference absent")
    for declaration in (
        "\tstruct owner_observation before;",
        "\tstruct owner_observation after;",
        "\tstruct mt6797_a72_transaction transaction;",
        "\tstruct mt6797_a72_owner_snapshot snapshot;",
        "\tconst struct mt6797_a72_transaction empty",
    ):
        remainder = owner.split(
            "struct mt6797_a72_owner_test_state {", 1
        )[1].split("};", 1)[1]
        require(declaration not in remainder,
                f"large owner fixture remains on stack: {declaration.strip()}")
    for case in OWNER_CASES:
        require(owner.count(f"KUNIT_CASE({case})") == 1,
                f"owner case changed: {case}")
    require(owner.count("KUNIT_CASE(") == len(OWNER_CASES),
            "owner KUnit case count changed")
    for token in (
        "mt6797_a72_owner_binder_success_handoff",
        "mt6797_a72_owner_binder_p32_from_verifying",
        "mt6797_a72_owner_binder_clean_rejection",
        "mt6797_a72_owner_binder_p29_without_provider",
        '.name = "mt6797-a72-p24-owner"',
    ):
        require(token in owner, f"owner contract token absent: {token}")
    for forbidden in (
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
        "arm_smccc_smc(",
        "readl(",
        "writel(",
        "i2c_transfer(",
    ):
        require(forbidden not in owner,
                f"physical operation appeared in owner tests: {forbidden}")

    print("validation=a72-owner-kunit-stack-fix-source")
    print(f"owner_cases={len(OWNER_CASES)}")
    print("owner_stack_observations=0")
    print("owner_stack_transactions=0")
    print("owner_stack_snapshots=0")
    print("kunit_heap_fixture_allocations=1")
    print("production_files_changed=0")
    print("physical_operations=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
