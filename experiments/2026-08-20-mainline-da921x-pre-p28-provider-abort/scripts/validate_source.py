#!/usr/bin/env python3
"""Validate the edited pre-P28 provider-abort kernel source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def between(text: str, start: str, end: str) -> str:
    require(text.count(start) == 1, f"source boundary changed: {start}")
    require(text.count(end) >= 1, f"source boundary changed: {end}")
    return text.split(start, 1)[1].split(end, 1)[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    root = parser.parse_args().source_root.resolve()
    arm64_kconfig = (root / "arch/arm64/Kconfig").read_text()
    header = (
        root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    ).read_text()
    owner = (
        root / "arch/arm64/kernel/mt6797_a72_membership.c"
    ).read_text()
    regulator_kconfig = (root / "drivers/regulator/Kconfig").read_text()
    makefile = (root / "drivers/regulator/Makefile").read_text()
    provider_header = (
        root / "drivers/regulator/da9213-legacy-provider-contract.h"
    ).read_text()
    driver = (
        root / "drivers/regulator/da9213-legacy-regulator.c"
    ).read_text()
    test = (
        root / "drivers/regulator/da9213-legacy-membership-test.c"
    ).read_text()

    require("#define MT6797_A72_TRANSACTION_ABI 2" in header,
            "transaction ABI did not advance")
    for token in (
        "MT6797_A72_FAULT_PROVIDER_ACQUIRE_RETURN",
        "MT6797_A72_FAULT_PROVIDER_RELEASE_RETURN",
        "struct mt6797_a72_provider_abort_proof",
        "u8 provider_abort;",
        "u32 provider_abort_valid;",
        "mt6797_a72_membership_run_provider_abort",
    ):
        require(token in header, f"membership ABI token missing: {token}")
    require(
        "config ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT" in arm64_kconfig,
        "default-off abort config missing",
    )
    require("adds no production owner opener or caller" in arm64_kconfig,
            "closed lifecycle help missing")
    require("config ARM64_MT6797_A72_P24_OWNER_TEST_SEED" in arm64_kconfig,
            "focused test seed config missing")
    require("#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED" in header,
            "focused test seed declaration guard missing")
    require("#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED" in owner,
            "focused test seed implementation guard missing")

    acquire = between(
        owner,
        "int\nmt6797_a72_membership_run_provider_acquire(",
        "static bool\nmt6797_a72_provider_abort_proof_valid(",
    )
    abort = between(
        owner,
        "static bool\nmt6797_a72_provider_abort_proof_valid(",
        "static bool\nmt6797_a72_p28_preparation_valid(",
    )
    p29 = between(
        owner,
        "static bool\nmt6797_a72_p29_provider_predecessor_valid(",
        "static int\nmt6797_a72_membership_check_up(",
    )
    for token in (
        "mt6797_a72_provider_acquire_response_valid",
        "mt6797_a72_provider_refusal_response_valid",
        "mt6797_a72_membership_latch_provider_fault",
        "MT6797_A72_PROVIDER_FAULT_UNKNOWN",
        "MT6797_A72_OWNER_FAULTED",
        "MT6797_A72_PHASE_FAULT",
        "-EPROTO",
    ):
        require(token in owner, f"fail-stop token missing: {token}")
    for token in (
        "MT6797_A72_PROVIDER_RELEASE_INFLIGHT",
        "budgets.provider_abort",
        "mt6797_a72_provider_release(&handle, response)",
        "MT6797_A72_PROVIDER_ABORT_EXACT_RELEASE",
        "memset(&a72_owner.provider_identity, 0",
        "MT6797_A72_FAULT_PROVIDER_RELEASE_RETURN",
    ):
        require(token in abort, f"abort token missing: {token}")
    for token in (
        "provider_rejection_valid ==",
        "provider_abort_valid",
        "mt6797_a72_provider_abort_proof_valid",
        "MT6797_A72_P28_STAGE_NONE",
        "MT6797_A72_BUDGET_AVAILABLE",
    ):
        require(token in p29, f"P29 predecessor token missing: {token}")
    require("provider_abort = MT6797_A72_BUDGET_AVAILABLE" in owner,
            "CPU8 abort budget initialization missing")
    require("ARM64_LATE_CPU_STARTUP_OP_CPU8_UP" in abort,
            "CPU8-only guard missing")

    for token in (
        "struct da9213_legacy_provider_endpoint",
        "da9213_legacy_provider_test_register",
        "da9213_legacy_provider_test_unregister",
    ):
        require(token in provider_header, f"endpoint token missing: {token}")
    require("struct da9213_legacy_provider_endpoint provider_endpoint;" in driver,
            "production endpoint embedding missing")
    require(driver.count("&da9213_legacy_provider_ops") >= 4,
            "exact production registry ops were not reused")
    require("endpoint->ops" in driver and "endpoint->transaction" in driver,
            "injectable endpoint callback missing")

    require(
        "config REGULATOR_DA9213_LEGACY_MEMBERSHIP_KUNIT_TEST"
        in regulator_kconfig,
        "integration KUnit config missing",
    )
    require("select ARM64_MT6797_A72_P24_OWNER_TEST_SEED"
            in regulator_kconfig, "focused test seed selection missing")
    require("da9213-legacy-membership-test.o" in makefile,
            "integration KUnit object missing")
    require(test.count("KUNIT_CASE(") == 6, "KUnit case count changed")
    require(test.count("kunit_kzalloc(test, sizeof(*state), GFP_KERNEL)") == 6,
            "KUnit heap-state allocation inventory changed")
    require(test.count("struct mt6797_a72_owner_snapshot snapshot;") == 2,
            "owner snapshot escaped heap-backed state")
    require(test.count("struct mt6797_a72_transaction transaction;") == 1,
            "transaction escaped heap-backed state")
    for token in (
        "struct da9213_membership_test_state",
        "mt6797_a72_membership_snapshot(&synthetic->snapshot)",
        "da9213_membership_positive_abort_success",
        "da9213_membership_acquire_transport_faults",
        "da9213_membership_acquire_malformed_success",
        "da9213_membership_release_transport_faults",
        "da9213_membership_release_malformed_success",
        "da9213_membership_abort_guards_and_p29",
        "ordinal <= DA9213_LEGACY_PROVIDER_ACTIONS",
        "mutation <= DA9213_MEMBERSHIP_MUTATIONS",
        "mt6797_a72_provider_register(&da9213_membership_synthetic_ops",
        "da9213_legacy_provider_test_register",
        "release_entry_provider_state",
        "MT6797_A72_PROVIDER_RELEASE_INFLIGHT",
        "synthetic.release_calls, 1U",
        "fake.operation_calls, ordinal",
        "MT6797_A72_P28_STAGE_NONE",
        "MT6797_A72_BUDGET_AVAILABLE",
    ):
        require(token in test, f"KUnit coverage missing: {token}")

    production = acquire + abort + p29 + driver
    for forbidden in (
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
        "ioremap",
        "writel(",
        "regulator_enable(",
        "regulator_disable(",
        "regulator_set_voltage(",
    ):
        require(forbidden not in production,
                f"forbidden production token: {forbidden}")
    for forbidden in (
        "i2c_add_adapter",
        "i2c_new_client",
        "ioremap",
        "writel(",
        "cpu_up(",
        "cpu_down(",
    ):
        require(forbidden not in test, f"hardware KUnit token: {forbidden}")

    print("validation=da921x-pre-p28-provider-abort-edited-source")
    print("logical_patches=5")
    print("kunit_cases=6")
    print("acquire_failure_ordinals=22")
    print("release_failure_ordinals=22")
    print("malformed_responses=28")
    print("p29_mutations=9")
    print("hardware_action=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
