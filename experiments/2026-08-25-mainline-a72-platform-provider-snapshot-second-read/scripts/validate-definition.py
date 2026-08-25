#!/usr/bin/env python3
"""Validate the frozen platform/provider second-read definition."""

from __future__ import annotations

import argparse
import hashlib
import json
import zlib
from pathlib import Path


EXPERIMENT = "2026-08-25-mainline-a72-platform-provider-snapshot-second-read"
PATCHES = (
    "0367-pstore-add-Gemini-A72-platform-provider-ledger.patch",
    "0368-soc-mediatek-add-A72-platform-provider-snapshot-observer.patch",
    "0369-dt-bindings-soc-mediatek-add-A72-platform-provider-snapshot-observer.patch",
    "0370-soc-mediatek-test-A72-platform-provider-snapshot-observer.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"safe regular file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path)
    args = parser.parse_args()
    root = (
        args.repository_root.resolve()
        if args.repository_root
        else Path(__file__).resolve().parents[3]
    )
    exp = root / "experiments" / EXPERIMENT
    contract = json.loads(read(exp / "contract.json"))
    readme = read(exp / "README.md")
    design = read(exp / "DESIGN.md")
    generator = read(exp / "scripts/generate-on-buildbox")
    edits = read(exp / "scripts/source_edits.py")
    source_validator = read(exp / "scripts/validate_source.py")
    patch_validator = read(exp / "scripts/validate_patch.py")
    buildbox = read(root / "scripts/buildbox")

    require(contract["schema"] == 1, "contract schema")
    require(contract["experiment"] == EXPERIMENT, "experiment identity")
    require(tuple(contract["planned_patches"]) == PATCHES, "planned patch order")
    require(contract["configuration"]["maxcpus"] == 8, "CPU8/CPU9 remain closed")
    for key in (
        "positive_provider_transaction",
        "firmware_writer_transaction_window",
        "platform_only_observer",
        "full_physical_source_observer",
        "protected_readback_observer",
        "direct_state_compositor",
        "production_publisher",
    ):
        require(contract["configuration"][key] is False, f"closed config: {key}")
    effects = contract["runtime_effects"]
    expected_effects = {
        "platform_snapshot_calls": 1,
        "platform_samples": 2,
        "platform_register_observations": 26,
        "provider_snapshots": 1,
        "provider_samples": 2,
        "provider_registers_per_sample": 5,
        "provider_i2c_reads": 10,
        "provider_i2c_writes": 0,
        "retained_write_attempts_maximum": 2,
        "observer_retries": 0,
        "protected_clock_reads": 0,
        "bigidvfs_reads": 0,
        "secure_calls": 0,
        "provider_acquires": 0,
        "provider_releases": 0,
        "publisher_calls": 0,
        "owner_mutations": 0,
        "cpu_requests": 0,
    }
    require(effects == expected_effects, "exact runtime effect inventory")

    parent = root / contract["canonical_parent"]
    require(
        hashlib.sha256(parent.read_bytes()).hexdigest()
        == contract["canonical_parent_sha256"],
        "canonical parent hash",
    )
    for value in (
        contract["prepared_source_state"],
        contract["prepared_source_integrity"],
        *contract["edited_parent_files"].values(),
        *contract["audited_dependencies"].values(),
    ):
        require(len(value) == 64 and set(value) <= set("0123456789abcdef"), "hash form")

    records = contract["retained_records"]
    require(len(records) == 2, "two retained records")
    for expected_slot, expected_checkpoint, expected_crc in (
        (1, "before-provider", "0150f9c7"),
        (2, "after-provider", "4fffb31e"),
    ):
        record = records[expected_slot - 1]
        require(record["slot"] == expected_slot, "retained slot")
        require(record["checkpoint"] == expected_checkpoint, "retained checkpoint")
        require(record["token"] == "GAPP-20260825-A", "retained token")
        line = (
            "GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 token=GAPP-20260825-A "
            f"checkpoint={expected_checkpoint} slot={expected_slot}"
        )
        require(f"{zlib.crc32(line.encode()):08x}" == expected_crc, "fixed CRC oracle")
        require(record["crc32"] == expected_crc, "contract record CRC")
        require(expected_crc in edits and expected_crc in source_validator, "CRC gates")

    for token in (
        "platform_snapshot\n  -> checkpoint(before-provider)\n"
        "  -> provider_snapshot\n  -> checkpoint(after-provider)",
        "Maximum retained write attempts are two",
        "Every failure result must be byte-for-byte zero",
    ):
        require(token in design, f"design boundary: {token.splitlines()[0]}")
    for token in (
        "Changed-ID Gemian with only `before-provider`",
        "do not implicate DA921x",
        "Buildbox only",
        "maxcpus=8",
    ):
        require(token in readme, f"README boundary: {token}")

    source_dir = exp / "source"
    observer = read(source_dir / "mt6797-a72-platform-provider-snapshot-observer.c")
    internal = read(
        source_dir / "mt6797-a72-platform-provider-snapshot-observer-internal.h"
    )
    tests = read(
        source_dir / "mt6797-a72-platform-provider-snapshot-observer-test.c"
    )
    binding = read(
        source_dir / "mediatek,mt6797-a72-platform-provider-snapshot-observer.yaml"
    )
    order = (
        "ops->platform(context, platform, &snapshot->platform)",
        "ops->checkpoint(context, 0)",
        "ops->provider(context, &snapshot->provider)",
        "ops->checkpoint(context, 1)",
        "snapshot->valid = true",
    )
    positions = [observer.index(token) for token in order]
    require(positions == sorted(positions), "template call order")
    require(observer.count("mt6797_a72_provider_snapshot(") == 1, "one provider API call")
    require(observer.count("mt6797_a72_platform_state_snapshot(") == 1, "one platform API call")
    require(observer.count("memset(snapshot, 0, sizeof(*snapshot));") == 2, "zero contract")
    for forbidden in (
        "mt6797_a72_provider_acquire(",
        "mt6797_a72_provider_release(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "i2c_transfer(",
        "regmap_write(",
        "cpu_up(",
    ):
        require(forbidden not in observer, f"template forbidden operation: {forbidden}")
    require("struct mt6797_a72_platform_provider_snapshot" in internal, "typed output")
    require(tests.count("KUNIT_CASE(") == 6, "six injected cases")
    require(
        "mediatek,mt6797-a72-platform-provider-snapshot-observer" in binding
        and binding.count("mediatek,platform-state") == 3,
        "binding shape",
    )

    for patch in PATCHES:
        require(patch in generator and patch in patch_validator, f"patch gate: {patch}")
    for token in (
        contract["prepared_source_state"],
        contract["prepared_source_integrity"],
        contract["canonical_parent_sha256"],
        "hardware_free_tests=6",
        "provider_i2c_reads=10",
        "boot_candidate=false",
    ):
        require(token in generator, f"generator pin: {token}")
    for token in (
        "generate-a72-platform-provider-patches",
        "fetch-a72-platform-provider-patches",
        "generate_a72_platform_provider_patches",
        "fetch_a72_platform_provider_patches",
        "mainline-a72-platform-provider-patch-generation",
    ):
        require(token in buildbox, f"Buildbox integration: {token}")
    require(
        "  generate-a72-platform-provider-patches) "
        "generate_a72_platform_provider_patches ;;" in buildbox,
        "Buildbox generate dispatcher",
    )
    require(
        "  fetch-a72-platform-provider-patches) "
        "fetch_a72_platform_provider_patches ;;" in buildbox,
        "Buildbox fetch dispatcher",
    )
    require("--backend vm" not in generator, "no native VM build")
    personal_root = "/" + "Users/"
    require(personal_root not in "\n".join((readme, design, generator)), "no host path")
    print("definition_validation=pass")


if __name__ == "__main__":
    main()
