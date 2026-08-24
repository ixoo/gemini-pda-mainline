#!/usr/bin/env python3
"""Validate the DA921x read-only snapshot generation input."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    contract = json.loads((EXPERIMENT / "contract.json").read_text())
    require(contract["schema"] == 1, "contract schema")
    require(
        contract["experiment"]
        == "2026-08-24-mainline-da921x-readonly-snapshot-separation",
        "experiment identity",
    )
    require(
        contract["prepared_source_state"]
        == "ac57421ae45c6e55ba34f2cac4131647e89762ad5988baf1b47364c2c75e77cb",
        "prepared source state",
    )
    require(contract["production"] == {
        "samples": 2,
        "reads_per_sample": 5,
        "register_order": ["0x56", "0x51", "0x5e", "0xd9", "0xda"],
        "endpoint_mutexes": 1,
        "root_adapter_locks": 1,
        "adapter_retries": "zero-then-restored",
        "positive_provider_transaction": False,
        "writer_transaction_window": False,
    }, "production contract")
    require(contract["test"] == {
        "focused_cases": 5,
        "negative_transfer_ordinals": 10,
        "short_transfer_ordinals": 10,
        "second_sample_mismatches": 5,
        "physical_i2c": False,
    }, "test contract")
    require(all(value is False for value in contract["exclusions"].values()),
            "all excluded effects remain false")
    require(contract["result"] == "pending-generation", "result state")

    generator = (EXPERIMENT / "scripts/generate-on-buildbox").read_text()
    for token in (
        "PARENT_SOURCE_STATE=ac57421ae45c6e55ba34f2cac4131647e89762ad5988baf1b47364c2c75e77cb",
        "PARENT_SOURCE_INTEGRITY=d87fe0d866aec4825c2e2c2bf5f1df628299692e5bad63e581b07c64d0f3c22d",
        "linux-7.1.3-series-source",
        "generated_patch_count=2",
        "positive_provider_transaction=false",
        "writer_transaction_window=false",
        "physical_i2c=false",
        "boot_candidate=false",
    ):
        require(token in generator, f"generator token {token}")
    source_edits = (EXPERIMENT / "scripts/source_edits.py").read_text()
    for token in (
        "da9213_provider_read_transport_valid",
        "da9213_legacy_provider_snapshot_sample",
        ".snapshot = da9213_provider_snapshot",
        "provider_endpoint.read_transfer = __i2c_transfer",
        "CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER_SNAPSHOT_KUNIT_TEST",
        "depends on !REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION",
        "depends on !MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW",
    ):
        require(token in source_edits, f"source edit token {token}")
    test = (
        EXPERIMENT / "source/da9213-legacy-provider-snapshot-test.c"
    ).read_text()
    require(test.count("KUNIT_CASE(") == 5, "focused KUnit case count")
    for token in (
        "ordinal <= DA9213_SNAPSHOT_READS",
        "byte <= DA9213_SNAPSHOT_BYTES",
        "ret, -EBUSY",
        "ret, -EOPNOTSUPP",
        "state->fake.transfer_calls, 0U",
    ):
        require(token in test, f"KUnit token {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-da921x-readonly-snapshot-patches",
        "fetch-da921x-readonly-snapshot-patches",
    ):
        require(buildbox.count(command) >= 2, f"Buildbox command {command}")
    require(
        "readonly source_root=\"${workspace_root}/src/linux-7.1.3-series-source\""
        in buildbox[buildbox.index("generate_da921x_readonly_snapshot_patches"):],
        "Buildbox exact canonical source root",
    )
    require(
        "2026-08-24-mainline-da921x-readonly-snapshot-separation"
        in (ROOT / "experiments/README.md").read_text(),
        "experiment index",
    )
    require(
        "generate-da921x-readonly-snapshot-patches"
        in (ROOT / "docs/BUILDBOX.md").read_text(),
        "Buildbox documentation",
    )
    require(
        "DA921x read-only snapshot separation"
        in (ROOT / "docs/ROADMAP.md").read_text(),
        "Roadmap selection",
    )

    print("validation=da921x-readonly-snapshot-generation-input")
    print("prepared_source_state=exact")
    print("generated_patch_count=2")
    print("focused_tests=5")
    print("positive_provider_transaction=false")
    print("writer_transaction_window=false")
    print("hardware_operations=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
