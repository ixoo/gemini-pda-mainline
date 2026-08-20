#!/usr/bin/env python3
"""Validate the frozen positive-provider source contract and templates."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    contract = json.loads((ROOT / "contract.json").read_text(encoding="utf-8"))
    implementation = (
        ROOT / "source/da9213-legacy-positive-provider.c.inc"
    ).read_text(encoding="utf-8")
    header = (ROOT / "source/da9213-legacy-provider-contract.h").read_text(
        encoding="utf-8"
    )
    test = (ROOT / "source/da9213-legacy-provider-test.c").read_text(
        encoding="utf-8"
    )

    require(contract["safety"]["default_off"], "positive path must be default-off")
    require(contract["safety"]["hardware_free"], "phase must be hardware-free")
    require(not contract["safety"]["device_access"], "device access forbidden")
    require(not contract["safety"]["cpu_on"], "CPU_ON forbidden")
    require(not contract["safety"]["cpu_off"], "CPU_OFF forbidden")
    require(
        contract["transport"]["transfers_per_successful_acquire"] == 11
        and contract["transport"]["transfers_per_successful_release"] == 11,
        "operation transfer bounds changed",
    )
    require(
        contract["transport"]["root_adapter_lock"]
        == "one-per-complete-acquire-or-release"
        and not contract["transport"]["lock_spans_handle_lifetime"],
        "adapter lock lifetime changed",
    )
    for token in (
        "u8 payload[2] = { 0x5e, value }",
        "0x01, false",
        "0x00, true",
        "i2c_lock_bus(adapter, I2C_LOCK_ROOT_ADAPTER)",
        "adapter->retries = 0",
        "DA9213_LEGACY_PROVIDER_FAULT_RETAINED",
        "request->transaction_generation",
        "request->transaction_cookie",
        ".transfer = __i2c_transfer",
        ".delay = usleep_range",
    ):
        require(token in implementation, f"implementation token missing: {token}")
    require(implementation.count("i2c_lock_bus(") == 2, "lock count changed")
    require(implementation.count("i2c_unlock_bus(") == 4, "unlock count changed")
    require(implementation.count("da9213_legacy_provider_write_cont(") == 3,
            "one helper plus two write call sites required")
    for forbidden in (
        "PAGE_CON",
        "regulator_enable(",
        "regulator_disable(",
        "regulator_set_voltage(",
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
        "ioremap",
        "writel(",
    ):
        require(forbidden not in implementation, f"forbidden source token: {forbidden}")

    require("DA9213_LEGACY_PROVIDER_ACTIONS\t\t11" in header,
            "header action bound changed")
    require("DA9213_LEGACY_PROVIDER_SETTLE_US\t\t1000" in header,
            "settle bound changed")
    require(test.count("KUNIT_CASE(") == 6, "KUnit case count changed")
    for token in (
        "DA9213_PROVIDER_TEST_ADDRESS\t0x2a",
        "ordinal <= DA9213_LEGACY_PROVIDER_ACTIONS",
        "fake.fail_ordinal = ordinal",
        "fake.short_ordinal = ordinal",
        "1, 3, 4, 5, 7, 9, 10, 11",
        "fake.mismatch_ordinal = 2",
        "fake.write_values[0], (u8)0x01",
        "fake.write_values[1], (u8)0x00",
        "fake.adapter.retries",
        "fake.transfer_unlocked",
    ):
        require(token in test, f"KUnit token missing: {token}")
    for forbidden in (
        "i2c_add_adapter",
        "i2c_new_client",
        "ioremap",
        "writel(",
        "regulator_enable(",
        "cpu_up(",
    ):
        require(forbidden not in test, f"hardware test token: {forbidden}")

    print("validation=da921x-positive-provider-contract")
    print("logical_patches=3")
    print("successful_operation_transfers=11")
    print("negative_and_short_failure_ordinals=44")
    print("owned_value_mismatch_ordinals=16")
    print("kunit_cases=6")
    print("hardware_action=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
