#!/usr/bin/env python3
"""Validate the frozen platform/provider readiness-repair definition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPERIMENT = "2026-08-25-mainline-a72-platform-provider-deferred-bind-repair"
PREDECESSOR = "2026-08-25-mainline-a72-platform-provider-snapshot-second-read"
PATCHES = (
    "0371-soc-mediatek-defer-A72-platform-provider-until-provider-ready.patch",
    "0372-dt-bindings-soc-mediatek-require-A72-snapshot-provider.patch",
    "0373-soc-mediatek-test-A72-platform-provider-readiness.patch",
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
    edits = read(exp / "scripts/source_edits.py")
    source_validator = read(exp / "scripts/validate_source.py")
    patch_validator = read(exp / "scripts/validate_patch.py")
    generator = read(exp / "scripts/generate-on-buildbox")
    classifier = read(exp / "scripts/classify-kunit.py")
    runner = read(exp / "scripts/run-kunit-qemu")
    dt_builder = read(exp / "scripts/build-provider-ready-dtb.sh")
    buildbox = read(root / "scripts/buildbox")
    manifest = json.loads(read(root / "kernel/manifest.json"))

    require(contract["schema"] == 1, "contract schema")
    require(contract["experiment"] == EXPERIMENT, "experiment identity")
    require(tuple(contract["planned_patches"]) == PATCHES, "planned patch order")
    require(contract["configuration"]["maxcpus"] == 8, "CPU8/CPU9 closed")
    for key in (
        "positive_provider_transaction",
        "firmware_writer_transaction_window",
        "same_value_writer",
        "protected_readback_observer",
        "direct_state_compositor",
        "production_publisher",
    ):
        require(contract["configuration"][key] is False, f"closed config: {key}")
    expected_ceiling = {
        "platform_snapshot_calls": 1,
        "platform_samples": 2,
        "platform_register_observations": 26,
        "provider_snapshots": 1,
        "provider_samples": 2,
        "provider_i2c_reads": 10,
        "provider_i2c_writes": 0,
        "retained_write_attempts_maximum": 2,
        "capture_retries": 0,
        "protected_clock_reads": 0,
        "bigidvfs_reads": 0,
        "secure_calls": 0,
        "provider_acquires": 0,
        "provider_releases": 0,
        "publisher_calls": 0,
        "owner_mutations": 0,
        "cpu_requests": 0,
    }
    require(contract["runtime_ceiling"] == expected_ceiling, "exact runtime ceiling")
    gate = contract["dependency_gate"]
    require(gate == {
        "property": "mediatek,provider",
        "compatible": "dlg,da9214-legacy",
        "lookup": "of_find_i2c_device_by_node",
        "readiness": "device_is_bound",
        "not_ready_result": "-EPROBE_DEFER",
        "not_ready_platform_calls": 0,
        "not_ready_checkpoint_calls": 0,
        "not_ready_provider_calls": 0,
        "not_ready_hardware_access": False,
    }, "exact dependency gate")
    require(contract["candidate_dtb"] == {
        "predecessor_sha256": "ee8baf009bd3c94e59c91a4d4b6090e6280e4045b5a0ff8abdcd0c0ef2f6d1ac",
        "derived_sha256": "923575e4e25498f2749bb440af78372e36bb318bf5717d05ced18be600ebd6c8",
        "provider_phandle": "0x30",
        "added_nodes": 0,
        "added_properties": 2,
        "reverse_normalization": "byte-identical-sorted-dts",
    }, "exact reversible candidate DT")

    parent = root / contract["canonical_parent"]
    require(hashlib.sha256(parent.read_bytes()).hexdigest()
            == contract["canonical_parent_sha256"], "canonical parent hash")
    predecessor_source = root / "experiments" / PREDECESSOR / "source"
    for relative, expected in contract["edited_parent_files"].items():
        source = predecessor_source / Path(relative).name
        require(hashlib.sha256(source.read_bytes()).hexdigest() == expected,
                f"edited parent hash: {relative}")
    for value in (
        contract["prepared_source_state"],
        contract["prepared_source_integrity"],
        contract["canonical_parent_sha256"],
    ):
        require(len(value) == 64 and set(value) <= set("0123456789abcdef"),
                "hash form")

    for token in (
        "zero platform calls, zero retained-checkpoint events, zero provider calls",
        "provider device reference is held until capture and logging complete",
        "adds no I2C transfer",
    ):
        require(token in design, f"design boundary: {token}")
    for token in (
        "Registry source proves",
        "Buildbox only",
        "26 read-only platform register observations",
        "ten read-only pointer/read transfers",
        "No unchanged predecessor retry",
    ):
        require(token in readme, f"README boundary: {token}")

    for patch in PATCHES:
        require(patch in generator and patch in patch_validator, f"patch gate: {patch}")
    for token in (
        contract["prepared_source_state"],
        contract["prepared_source_integrity"],
        contract["canonical_parent_sha256"],
        "provider_not_ready_platform_calls=0",
        "provider_not_ready_checkpoint_calls=0",
        "provider_not_ready_provider_calls=0",
        "hardware_free_tests=7",
        "boot_candidate=false",
    ):
        require(token in generator, f"generator pin: {token}")
    for token in (
        "return -EPROBE_DEFER",
        "of_find_i2c_device_by_node",
        "device_is_bound",
        "provider_ready_gate=passed",
    ):
        require(token in edits and token in source_validator,
                f"source edit and gate: {token}")
    require('"\\tif (!provider)\\n"' in edits, "capture provider gate edit")
    require("--backend vm" not in generator, "no native VM build")
    require(classifier.count('"mt6797_platform_provider_') == 7,
            "seven exact classifier cases")
    for token in (
        'PROFILE = "a72-platform-provider-ready-kunit"',
        '"1..7"',
        "pass:7 fail:0 skip:0 total:7",
        "provider_transactions=0",
        "boot_candidate=false",
    ):
        require(token in classifier, f"KUnit classifier boundary: {token}")
    for token in (
        "readonly EXPECTED_PROFILE=a72-platform-provider-ready-kunit",
        "-nic none",
        "timeout --signal=TERM 45",
        "CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION=y",
    ):
        require(token in runner, f"KUnit runner boundary: {token}")
    for token in (
        "readonly PROVIDER_PHANDLE=30",
        "readonly OUTPUT_SHA256=923575e4e25498f2749bb440af78372e36bb318bf5717d05ced18be600ebd6c8",
        "fdtput -t x",
        "fdtput -d",
        "added_nodes=0",
        "added_properties=2",
    ):
        require(token in dt_builder, f"candidate DT boundary: {token}")

    for token in (
        "generate-a72-platform-provider-ready-patches",
        "fetch-a72-platform-provider-ready-patches",
        "generate_a72_platform_provider_ready_patches",
        "fetch_a72_platform_provider_ready_patches",
        "mainline-a72-platform-provider-ready-patch-generation",
    ):
        require(token in buildbox, f"Buildbox integration: {token}")
    require(
        "  generate-a72-platform-provider-ready-patches) "
        "generate_a72_platform_provider_ready_patches ;;" in buildbox,
        "Buildbox generate dispatcher",
    )
    require(
        "  fetch-a72-platform-provider-ready-patches) "
        "fetch_a72_platform_provider_ready_patches ;;" in buildbox,
        "Buildbox fetch dispatcher",
    )

    profiles = manifest["config"]["profiles"]
    expected_profiles = contract["profiles"]
    for role, profile_name in expected_profiles.items():
        require(profile_name in profiles, f"manifest profile: {role}")
        profile = profiles[profile_name]
        require(profile["patch_series"] == "patches/series", f"series: {role}")
        fragment = f"configs/gemini-a72-platform-provider-ready-{role}.fragment"
        require(profile["fragments"][-1] == fragment, f"isolated final fragment: {role}")
        config = read(root / fragment)
        require("CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER=y" in config,
                f"observer enabled: {role}")
        require("CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set"
                in config, f"writer closed: {role}")
    require('CONFIG_LOCALVERSION="-gemini-a72-provider-ready-kunit"'
            in read(root / "configs/gemini-a72-platform-provider-ready-kunit.fragment"),
            "KUnit release identity")
    require('CONFIG_LOCALVERSION="-gemini-a72-provider-ready"'
            in read(root / "configs/gemini-a72-platform-provider-ready-candidate.fragment"),
            "candidate release identity")

    personal_root = "/" + "Users/"
    require(personal_root not in "\n".join((readme, design, generator)), "no host path")
    print("definition_validation=pass")


if __name__ == "__main__":
    main()
