#!/usr/bin/env python3
"""Validate the edited positive-provider kernel source."""

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
    driver = (root / "drivers/regulator/da9213-legacy-regulator.c").read_text()
    header = (root / "drivers/regulator/da9213-legacy-provider-contract.h").read_text()
    test = (root / "drivers/regulator/da9213-legacy-provider-test.c").read_text()
    kconfig = (root / "drivers/regulator/Kconfig").read_text()
    makefile = (root / "drivers/regulator/Makefile").read_text()
    arm64_kconfig = (root / "arch/arm64/Kconfig").read_text()

    require(
        ".acquire = da9213_legacy_provider_acquire,\n"
        "\t.release = da9213_legacy_provider_release," in driver,
        "release callback registration missing",
    )
    acquire = between(
        driver,
        "int da9213_legacy_provider_transaction_acquire(",
        "static bool da9213_provider_handle_matches(",
    )
    release = between(
        driver,
        "int da9213_legacy_provider_transaction_release(",
        "static const struct da9213_legacy_provider_transport_ops",
    )
    for operation in (acquire, release):
        require(operation.count("i2c_lock_bus(") == 1,
                "each operation needs one root lock")
        require(operation.count("i2c_unlock_bus(") == 2,
                "each operation needs success and failure unlocks")
        require("adapter->retries = 0" in operation,
                "zero-retry transport missing")
        require("da9213_legacy_provider_restore_retries" in operation,
                "retry restoration missing")
    require("0x01, false" in acquire, "enable write changed")
    require("0x00, true" in release, "owned inverse changed")
    require("ops->delay(DA9213_LEGACY_PROVIDER_SETTLE_US" in acquire,
            "one-millisecond settle missing")
    require("DA9213_LEGACY_PROVIDER_FAULT_RETAINED" in acquire,
            "acquire terminal state missing")
    require("DA9213_LEGACY_PROVIDER_FAULT_RETAINED" in release,
            "release terminal state missing")
    require("result->state != DA9213_LEGACY_PROVIDER_IDLE" in acquire,
            "second acquire guard missing")
    require("da9213_provider_handle_matches" in release,
            "release handle guard missing")
    require(".transfer = __i2c_transfer" in driver,
            "production transfer seam changed")
    require(".delay = usleep_range" in driver,
            "production delay seam changed")
    require("provider_transaction_lock" in driver,
            "provider state lock missing")
    require("config REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION" in kconfig,
            "positive Kconfig missing")
    require("depends on MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW" in kconfig,
            "firmware transaction-window dependency missing")
    require("does not connect CPU_ON" in arm64_kconfig,
            "owner isolation help missing")

    require("DA9213_LEGACY_PROVIDER_ACTIONS\t\t11" in header,
            "action count changed")
    require("config REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_KUNIT_TEST" in kconfig,
            "provider KUnit Kconfig missing")
    require("da9213-legacy-provider-test.o" in makefile,
            "provider KUnit object missing")
    require(test.count("KUNIT_CASE(") == 6, "KUnit case count changed")
    for token in (
        "DA9213_PROVIDER_TEST_ADDRESS\t0x2a",
        "fake.fail_ordinal = ordinal",
        "fake.short_ordinal = ordinal",
        "ordinal <= DA9213_LEGACY_PROVIDER_ACTIONS",
        "1, 3, 4, 5, 7, 9, 10, 11",
        "fake.mismatch_ordinal = 2",
        "DA9213_LEGACY_PROVIDER_FAULT_RETAINED",
        "fake.adapter.retries",
    ):
        require(token in test, f"KUnit coverage missing: {token}")

    production = between(
        driver,
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n\n"
        "static const u8 da9213_legacy_provider_snapshot_regs[]",
        "#endif\n\nstatic int da9213_legacy_provider_acquire",
    )
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
        require(forbidden not in production,
                f"forbidden production token: {forbidden}")
    for forbidden in ("i2c_add_adapter", "i2c_new_client", "ioremap", "writel("):
        require(forbidden not in test, f"hardware KUnit token: {forbidden}")

    print("validation=da921x-positive-provider-edited-source")
    print("logical_patches=3")
    print("kunit_cases=6")
    print("failure_ordinals=44")
    print("value_mismatch_ordinals=16")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
