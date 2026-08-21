#!/usr/bin/env python3
"""Validate the generated read-only DA921x provider-state source."""

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
    root = args.source_root.resolve()

    header = (root / "include/linux/mt6797-a72-provider.h").read_text()
    membership = (root / "arch/arm64/kernel/mt6797_a72_membership.c").read_text()
    driver = (root / "drivers/regulator/da9213-legacy-regulator.c").read_text()
    test = (root / "drivers/regulator/da9213-legacy-membership-test.c").read_text()

    for token in (
        "#define MT6797_A72_PROVIDER_STATE_ABI",
        "struct mt6797_a72_provider_state",
        "int (*snapshot)(void *context",
        "int mt6797_a72_provider_snapshot",
    ):
        require(token in header, f"provider header token: {token}")

    start = membership.index("int mt6797_a72_provider_snapshot")
    end = membership.index("struct mt6797_a72_owner_state", start)
    registry = membership[start:end]
    for token in (
        "memset(state, 0, sizeof(*state))",
        "mutex_lock(&a72_provider_registry_lock)",
        "ret = -ENODEV",
        "ret = -EOPNOTSUPP",
        "observed.abi != MT6797_A72_PROVIDER_STATE_ABI",
        "*state = observed",
        "EXPORT_SYMBOL_GPL(mt6797_a72_provider_snapshot)",
    ):
        require(token in registry, f"registry token: {token}")
    require(registry.index("memset(state, 0, sizeof(*state))") <
            registry.index("mutex_lock(&a72_provider_registry_lock)"),
            "destination cleared before registry lookup")

    start = driver.index("da9213_legacy_provider_state_snapshot")
    end = driver.index(
        "static const struct da9213_legacy_provider_transport_ops", start)
    snapshot = driver[start:end]
    for token in (
        "mutex_lock(&endpoint->lock)",
        "i2c_lock_bus(endpoint->adapter, I2C_LOCK_ROOT_ADAPTER)",
        "endpoint->adapter->retries = 0",
        "&result, &first",
        "&result, &second",
        "memcmp(&first, &second, sizeof(first))",
        "ret = -EAGAIN",
        ".abi = MT6797_A72_PROVIDER_STATE_ABI",
        ".valid = 1",
        "da9213_provider_restore_retries",
        "i2c_unlock_bus(endpoint->adapter, I2C_LOCK_ROOT_ADAPTER)",
        "mutex_unlock(&endpoint->lock)",
    ):
        require(token in snapshot, f"DA921x snapshot token: {token}")
    require(snapshot.count("da9213_legacy_provider_snapshot(") == 2,
            "exactly two complete samples")
    require(snapshot.index("mutex_lock(&endpoint->lock)") <
            snapshot.index("i2c_lock_bus(endpoint->adapter"),
            "endpoint-before-root lock order")
    for forbidden in (
        "provider_write", "ops->delay", "usleep", "msleep", "while (",
        "for (", "cpu_up(", "cpu_down(", "psci", "a34",
    ):
        require(forbidden not in snapshot,
                f"forbidden snapshot effect: {forbidden}")

    for token in (
        "DA9213_PROVIDER_SNAPSHOT_ACTIONS\t10",
        "da9213_provider_snapshot_success",
        "da9213_provider_snapshot_transport_faults",
        "da9213_provider_snapshot_unstable",
        "da9213_provider_snapshot_registry_guards",
        "fake->mutate_snapshot && fake->operation_calls == 6",
        "state->endpoint.transaction.total_transfers, 0U",
        "ret, -EOPNOTSUPP",
    ):
        require(token in test, f"KUnit token: {token}")
    require(test.count("KUNIT_CASE(da9213_provider_snapshot_") == 4,
            "four focused snapshot cases")

    print("source_validation=pass")
    print("snapshot_samples=2-no-loop")
    print("success_reads=10")
    print("root_adapter_locks=1")
    print("adapter_retries=0-restored")
    print("hardware_write=none")
    print("delay=none")
    print("a34_caller=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
