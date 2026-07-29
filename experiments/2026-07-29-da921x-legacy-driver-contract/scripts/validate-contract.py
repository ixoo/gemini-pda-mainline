#!/usr/bin/env python3
"""Validate the fixed Gate 1 legacy DA921x probe contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn


EXPERIMENT = Path(__file__).resolve().parents[1]
CONTRACT = EXPERIMENT / "probe-contract.json"

EXPECTED_TRANSFERS = [
    (1, 0, "0x69", "0x05", "0xd9"),
    (2, 0, "0x69", "0x06", "0xd0"),
    (3, 0, "0x69", "0x47", "0xc0"),
    (4, 0, "0x68", "0xd3", "0x1f"),
    (5, 0, "0x68", "0x5e", "0x00"),
    (6, 0, "0x68", "0xd9", "0x46"),
    (7, 0, "0x68", "0xda", "0x46"),
    (8, 1, "0x69", "0x05", "0xd9"),
    (9, 1, "0x69", "0x06", "0xd0"),
    (10, 1, "0x69", "0x47", "0xc0"),
    (11, 1, "0x68", "0xd3", "0x1f"),
    (12, 1, "0x68", "0x5e", "0x00"),
    (13, 1, "0x68", "0xd9", "0x46"),
    (14, 1, "0x68", "0xda", "0x46"),
]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"error: {message}")


def require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        fail(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> None:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    fixed_scalars = {
        "schema": 1,
        "compatible": "dlg,da9214-legacy",
        "driver_stage": "identification-only",
        "required_functionality": "I2C_FUNC_I2C",
        "transfer_api": "__i2c_transfer",
        "root_adapter_lock": True,
        "messages_per_transaction": 2,
        "pointer_write_length": 1,
        "register_data_write_length": 0,
        "read_length": 1,
        "retries": 0,
        "probe_passes": 2,
    }
    for key, expected in fixed_scalars.items():
        require_equal(data.get(key), expected, key)

    require_equal(
        data.get("addresses"),
        {"primary": "0x68", "page2": "0x69"},
        "fixed direct addresses",
    )

    transactions = data.get("transactions")
    if not isinstance(transactions, list):
        fail("transactions must be a list")

    normalized = []
    for item in transactions:
        if not isinstance(item, dict):
            fail("every transaction must be an object")
        require_equal(
            set(item),
            {"ordinal", "pass", "address", "register", "expected"},
            f"transaction {item!r} keys",
        )
        normalized.append(
            (
                item["ordinal"],
                item["pass"],
                item["address"],
                item["register"],
                item["expected"],
            )
        )

    require_equal(normalized, EXPECTED_TRANSFERS, "probe transaction sequence")

    lifecycle = data.get("lifecycle_transactions")
    require_equal(
        lifecycle,
        {
            "failed_probe_cleanup": 0,
            "unbind": 0,
            "shutdown": 0,
            "suspend": 0,
            "resume": 0,
        },
        "lifecycle transaction counts",
    )

    provider = data.get("provider")
    require_equal(
        provider,
        {
            "regulators_registered": 0,
            "writable_operations": 0,
            "consumers": 0,
            "a72_requests": 0,
            "irqs_requested": 0,
        },
        "provider boundary",
    )

    forbidden = data.get("forbidden_registers")
    require_equal(forbidden, ["0x00", "0x80", "0x100", "0x201"], "forbidden registers")
    observed = {entry[3] for entry in EXPECTED_TRANSFERS}
    overlap = observed.intersection(forbidden)
    if overlap:
        fail(f"probe reads forbidden registers: {sorted(overlap)}")

    print("validation=da921x-legacy-driver-contract")
    print(f"probe_transactions={len(EXPECTED_TRANSFERS)}")
    print("register_data_writes=0")
    print("lifecycle_transactions=0")
    print("provider=absent")


if __name__ == "__main__":
    main()
