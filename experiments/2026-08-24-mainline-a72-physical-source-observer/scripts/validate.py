#!/usr/bin/env python3
"""Validate the A72 physical-source observer generation input."""

from __future__ import annotations

import json
import zlib
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
        == "2026-08-24-mainline-a72-physical-source-observer",
        "experiment identity",
    )
    require(
        contract["canonical_parent"].startswith("patches/v7.1.3/0349-"),
        "canonical parent",
    )
    require(
        contract["prepared_source_state"]
        == "6e3b726cd84b346409bb14b6fb66652b7a52aae60a4636b39229e949275d961f",
        "prepared source state",
    )
    require(
        contract["prepared_source_integrity"]
        == "75be833a675873a374e1b4ef1c77ba0557307b4d054eab793e31930d097785dd",
        "prepared source integrity",
    )
    require(contract["production"] == {
        "source_registrations": 1,
        "public_direct_snapshots": 1,
        "source_unregistrations": 1,
        "component_order": [
            "platform", "provider", "clock", "before-bigidvfs",
            "bigidvfs", "after-bigidvfs",
        ],
        "retained_token": "GPSQ-20260824-A",
        "retained_slots": [1, 2],
        "maximum_retained_writes": 2,
        "clock_calls": 1,
        "bigidvfs_calls": 1,
        "bigidvfs_smc_reads": 8,
        "compositor_retries": 0,
    }, "production contract")
    require(contract["test"]["focused_cases"] == 4, "focused case count")
    require(all(value is False for key, value in contract["test"].items()
                if key != "focused_cases"), "hardware-free test effects")
    require(all(value is False for value in contract["exclusions"].values()),
            "excluded effects remain false")
    require(contract["generation"] == {
        "patch_count": 5,
        "logical_boundaries": ["ledger", "observer", "binding", "dts", "tests"],
        "intentional_checkpatch_ignore":
            "SPLIT_STRING-for-two-atomic-retained-records",
        "stopped_attempts": 4,
        "status": "pending",
    }, "generation contract")

    source_dir = EXPERIMENT / "source"
    observer = (source_dir / "mt6797-a72-physical-source-observer.c").read_text()
    tests = (source_dir / "mt6797-a72-physical-source-observer-test.c").read_text()
    binding = (
        source_dir / "mediatek,mt6797-a72-physical-source-observer.yaml"
    ).read_text()
    dts = (source_dir / "mt6797-gemini-pda-a72-physical-source.dts").read_text()
    order = (
        "readers->platform(",
        "readers->provider(",
        "readers->clock(",
        "readers->checkpoint(0)",
        "readers->bigidvfs(",
        "readers->checkpoint(1)",
    )
    positions = [observer.index(token) for token in order]
    require(positions == sorted(positions), "template capture order")
    for token in (
        "mt6797_a72_direct_source_register",
        "mt6797_a72_direct_state_snapshot",
        "mt6797_a72_direct_source_unregister",
        "put_device(context.bigidvfs)",
        "put_device(context.clock)",
        "put_device(context.platform)",
    ):
        require(token in observer, f"observer token: {token}")
    require(tests.count("KUNIT_CASE(") == 4, "four template KUnit cases")
    require('name = "mt6797-a72-physical-source"' in tests,
            "focused suite name")
    require("mediatek,platform-state:" in binding, "platform binding")
    require("mediatek,bigidvfs-backend:" in binding, "BigiDVFS binding")
    require("model =" not in dts, "candidate preserves model")
    require(dts.count('status = "okay";') == 4, "candidate enablement count")

    for checkpoint, slot, checksum in (
        ("before-bigidvfs", 1, "47eaad49"),
        ("after-bigidvfs", 2, "d03ca6dc"),
    ):
        line = (
            "GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A "
            f"checkpoint={checkpoint} slot={slot}"
        )
        require(f"{zlib.crc32(line.encode()):08x}" == checksum,
                f"retained CRC: {checkpoint}")

    generator = (EXPERIMENT / "scripts/generate-on-buildbox").read_text()
    for token in (
        "PARENT_SOURCE_STATE=6e3b726cd84b346409bb14b6fb66652b7a52aae60a4636b39229e949275d961f",
        "PARENT_SOURCE_INTEGRITY=75be833a675873a374e1b4ef1c77ba0557307b4d054eab793e31930d097785dd",
        "generated_patch_count=5",
        "retained_token=GPSQ-20260824-A",
        "provider_transactions=0",
        "publisher_calls=0",
        "owner_mutations=0",
        "cpu_requests=0",
        "checkpatch_intentional_ignore=SPLIT_STRING-for-two-atomic-retained-records",
        "boot_candidate=false",
    ):
        require(token in generator, f"generator token: {token}")
    source_edits = (EXPERIMENT / "scripts/source_edits.py").read_text()
    validator = (EXPERIMENT / "scripts/validate_source.py").read_text()
    for phase in ("ledger", "observer", "binding", "dts", "tests"):
        require(f'"{phase}"' in source_edits, f"source edit phase: {phase}")
    for token in (
        "exact component/checkpoint order",
        "reverse device release order",
        "raw all-ones and signature-last conditionals",
        "test physical operation",
    ):
        require(token in validator, f"source validator token: {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-a72-physical-source-patches",
        "fetch-a72-physical-source-patches",
    ):
        require(buildbox.count(command) >= 2, f"Buildbox command: {command}")
    require(
        "readonly source_root=\"${workspace_root}/src/linux-7.1.3-series-source\""
        in buildbox[buildbox.index("generate_a72_physical_source_patches"):],
        "exact managed source root",
    )
    require(
        "2026-08-24-mainline-a72-physical-source-observer"
        in (ROOT / "experiments/README.md").read_text(),
        "experiment index",
    )
    require(
        "generate-a72-physical-source-patches"
        in (ROOT / "docs/BUILDBOX.md").read_text(),
        "Buildbox documentation",
    )
    require(
        "Phase B physical-source observer"
        in (ROOT / "docs/ROADMAP.md").read_text(),
        "roadmap selection",
    )
    print("validation=a72-physical-source-input")
    print("prepared_source=exact-through-0349")
    print("generated_patch_count=5")
    print("focused_tests=4")
    print("hardware_operations=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
