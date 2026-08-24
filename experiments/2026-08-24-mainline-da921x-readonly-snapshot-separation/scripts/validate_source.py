#!/usr/bin/env python3
"""Validate cumulative DA921x read-only snapshot source phases."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("core", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    header = (
        root / "drivers/regulator/da9213-legacy-provider-contract.h"
    ).read_text()
    driver = (root / "drivers/regulator/da9213-legacy-regulator.c").read_text()

    for token in (
        "da9213_legacy_provider_read_transfer_t",
        "struct device *dev;",
        "read_transfer;",
        "CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION",
    ):
        require(token in header, f"private endpoint token {token}")
    endpoint = header[
        header.index("struct da9213_legacy_provider_endpoint {") :
        header.index("};", header.index("struct da9213_legacy_provider_endpoint {"))
    ]
    require("read_transfer" in endpoint, "endpoint read transport")
    require("#if IS_ENABLED(" in endpoint, "transaction fields remain guarded")
    require(endpoint.index("#if IS_ENABLED(") < endpoint.index("ops;"),
            "delay-bearing ops pointer is positive-only")
    require(endpoint.index("#if IS_ENABLED(") < endpoint.index("transaction;"),
            "mutable transaction is positive-only")

    owner = driver.index("#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)")
    positive = driver.index(
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)",
        owner,
    )
    readonly = driver[owner:positive]
    for token in (
        "da9213_legacy_provider_snapshot_regs[]",
        "0x56, 0x51, 0x5e, 0xd9, 0xda",
        "da9213_provider_read_transport_valid",
        "da9213_legacy_provider_snapshot_read",
        "da9213_legacy_provider_snapshot_sample",
        "da9213_provider_snapshot(void *context",
        "mutex_lock(&endpoint->lock)",
        "i2c_lock_bus(endpoint->adapter, I2C_LOCK_ROOT_ADAPTER)",
        "endpoint->adapter->retries = 0",
        "&first",
        "&second",
        "memcmp(&first, &second, sizeof(first))",
        "ret = -EAGAIN",
        "endpoint->adapter->retries = saved_retries",
        "i2c_unlock_bus(endpoint->adapter, I2C_LOCK_ROOT_ADAPTER)",
        "mutex_unlock(&endpoint->lock)",
    ):
        require(token in readonly, f"read-only production token {token}")
    require(readonly.count("da9213_legacy_provider_snapshot_sample(") == 3,
            "one helper definition and exactly two complete samples")
    require(readonly.count("read_transfer(") == 1,
            "one transport call site")
    require(readonly.index("mutex_lock(&endpoint->lock)") <
            readonly.index("i2c_lock_bus(endpoint->adapter"),
            "endpoint-before-root lock order")
    positions = [readonly.index(token) for token in (
        "mutex_lock(&endpoint->lock)",
        "i2c_lock_bus(endpoint->adapter",
        "endpoint->adapter->retries = 0",
        "da9213_legacy_provider_snapshot_sample(endpoint, &first)",
        "da9213_legacy_provider_snapshot_sample(endpoint, &second)",
        "memcmp(&first, &second, sizeof(first))",
        "endpoint->adapter->retries = saved_retries",
        "i2c_unlock_bus(endpoint->adapter",
        "mutex_unlock(&endpoint->lock)",
    )]
    require(positions == sorted(positions), "stable snapshot operation order")
    for forbidden in (
        "write_cont", "ops->delay", "usleep", "msleep", "cpu_up(",
        "cpu_down(", "writel(", "readl(", "arm_smccc", "a34", "p30",
    ):
        require(forbidden not in readonly,
                f"read-only path effect {forbidden}")

    ops_start = driver.index(
        "static const struct mt6797_a72_provider_ops da9213_legacy_provider_ops"
    )
    ops_end = driver.index("};", ops_start)
    ops = driver[ops_start:ops_end]
    require(".snapshot = da9213_provider_snapshot" in ops,
            "snapshot callback registered")
    require("CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE" not in ops,
            "snapshot registration is unconditional under owner")
    register_start = driver.index("static int da9213_legacy_register_owner")
    register_end = driver.index("#endif", register_start)
    register = driver[register_start:register_end]
    for token in (
        "context = &chip->provider_endpoint",
        "provider_endpoint.dev = chip->dev",
        "provider_endpoint.adapter = chip->client->adapter",
        "provider_endpoint.address = chip->client->addr",
        "provider_endpoint.read_transfer = __i2c_transfer",
        "devm_add_action_or_reset",
    ):
        require(token in register, f"owner lifetime token {token}")

    acquire = driver[
        driver.index("static int da9213_legacy_provider_acquire") :
        driver.index("static int da9213_legacy_provider_release")
    ]
    release = driver[
        driver.index("static int da9213_legacy_provider_release") : ops_start
    ]
    for name, function in (("acquire", acquire), ("release", release)):
        else_start = function.index("#else")
        refusal = function[else_start:]
        require("return -EOPNOTSUPP;" in refusal, f"{name} refusal")
        for forbidden in ("read_transfer", "i2c_", "provider_transaction_"):
            require(forbidden not in refusal,
                    f"{name} refusal transport effect {forbidden}")

    if args.phase == "core":
        require(
            not (root / "drivers/regulator/da9213-legacy-provider-snapshot-test.c").exists(),
            "test leaked into core phase",
        )
        print("validation=da921x-readonly-snapshot-source")
        print("phase=core")
        print("snapshot_samples=2")
        print("success_reads=10")
        print("positive_provider_transaction=false")
        print("hardware_writes=0")
        print("result=pass")
        return

    kconfig = (root / "drivers/regulator/Kconfig").read_text()
    makefile = (root / "drivers/regulator/Makefile").read_text()
    test = (
        root / "drivers/regulator/da9213-legacy-provider-snapshot-test.c"
    ).read_text()
    for token in (
        "config REGULATOR_DA9213_LEGACY_PROVIDER_SNAPSHOT_KUNIT_TEST",
        "depends on !REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION",
        "depends on !MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW",
    ):
        require(token in kconfig, f"test Kconfig token {token}")
    require(
        "CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER_SNAPSHOT_KUNIT_TEST"
        in makefile,
        "test Makefile wiring",
    )
    require(test.count("KUNIT_CASE(") == 5, "five focused KUnit cases")
    for token in (
        "da9213_snapshot_success_test",
        "da9213_snapshot_transfer_faults_test",
        "da9213_snapshot_mismatches_test",
        "da9213_snapshot_registry_lifetime_test",
        "da9213_snapshot_readonly_lifecycle_test",
        "ordinal <= DA9213_SNAPSHOT_READS",
        "byte <= DA9213_SNAPSHOT_BYTES",
        "ret, -EBUSY",
        "ret, -EOPNOTSUPP",
        "state->fake.transfer_calls, 0U",
        'name = "da9213-legacy-provider-snapshot"',
    ):
        require(token in test, f"focused test token {token}")
    for forbidden in (
        "i2c_add_adapter", "i2c_new_client", "writel(", "readl(",
        "arm_smccc", "cpu_up(", "cpu_down(", "provider_write_cont",
    ):
        require(forbidden not in test, f"test hardware effect {forbidden}")

    print("validation=da921x-readonly-snapshot-source")
    print("phase=tests")
    print("focused_tests=5")
    print("negative_transfer_ordinals=10")
    print("short_transfer_ordinals=10")
    print("second_sample_mismatches=5")
    print("positive_provider_transaction=false")
    print("writer_transaction_window=false")
    print("physical_i2c=false")
    print("hardware_writes=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
