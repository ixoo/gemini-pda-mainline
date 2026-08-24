#!/usr/bin/env python3
"""Validate the A72 physical-source observer generation input."""

from __future__ import annotations

import hashlib
import json
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        "stopped_attempts": 5,
        "status": "validated",
        "repository_commit":
            "8d0d49042331f54eeef475f9601bc9de2a5722ea",
        "buildbox_job":
            "8d0d49042331f54eeef475f9601bc9de2a5722ea-a72-physical-source-patchgen",
        "package": "a72-physical-source-8d0d49042331",
        "parent_commit": "a796fdef26e26c896db6147de3f4166a87bebb99",
        "result_commit": "31d96ca391708d74228e6b8621bf7931ed2a8e7e",
        "sha256sums_sha256":
            "36a69869b23a34e66b4285235b7562a1e104b576e96cb1bc70cba3c34a173547",
        "patch_sha256": [
            "b13b8e2451e6807b6fcdf0863c774e9219616f09d7cb58d1575ebcd10c84badd",
            "d6f173fe53251644e671f49961b11e15b39f337923bfe9501a7efde6c19bf5c7",
            "209c9304567976287e385e48d46797d837876a7b38bbf880a3a554659ca42c9c",
            "bba2c1ba68ac231d9360e428c39d8fda2e40698e2f14c821de69383f23ed0756",
            "c9d35ee189e081099520a18becc3f839c04085aaa7fc1863c9c62270944a8aca",
        ],
        "canonical_admission": "0350-0354",
    }, "generation contract")
    require(contract["build"] == {
        "profile": "a72-physical-source-kunit",
        "backend": "buildbox",
        "status": "pending",
        "qemu": "pending",
    }, "build contract")

    canonical = [ROOT / "patches/v7.1.3" / patch
                 for patch in contract["patches"]]
    require(all(path.is_file() and not path.is_symlink() for path in canonical),
            "canonical patch inventory")
    require([sha256(path) for path in canonical]
            == contract["generation"]["patch_sha256"],
            "canonical patch identities")
    series = (ROOT / "patches/series").read_text().splitlines()
    require(series[-5:] == [f"v7.1.3/{patch}"
                            for patch in contract["patches"]],
            "canonical series tail")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profile = manifest["config"]["profiles"]["a72-physical-source-kunit"]
    require(profile["base"] == "defconfig", "profile base")
    require(profile["patch_series"] == "patches/series", "profile series")
    require(profile["fragments"][-1]
            == "configs/gemini-a72-physical-source-kunit.fragment",
            "profile final fragment")
    fragment = (
        ROOT / "configs/gemini-a72-physical-source-kunit.fragment"
    ).read_text()
    for token in (
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST=y",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR=y",
        "# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW is not set",
    ):
        require(token in fragment, f"profile token: {token}")

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
    runner = (EXPERIMENT / "scripts/run-kunit-qemu").read_text()
    classifier = (EXPERIMENT / "scripts/classify-kunit.py").read_text()
    for token in (
        "EXPECTED_PROFILE=a72-physical-source-kunit",
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST=y",
        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y",
        "-nic none",
    ):
        require(token in runner, f"QEMU runner token: {token}")
    for token in (
        'SUITE = "mt6797-a72-physical-source"',
        '"mt6797_source_capture_failures_test"',
        'print("tests=4")',
        'print("boot_candidate=false")',
    ):
        require(token in classifier, f"classifier token: {token}")
    receipt = (
        EXPERIMENT / "results/buildbox-generation-8d0d4904.txt"
    ).read_text()
    for token in (
        "source_validation=pass-all-five-phases",
        "patch_replay=byte-exact-pass",
        "strict_checkpatch=0-errors-0-warnings-0-checks",
        "canonical_admission=0350-0354",
        "compile=pending",
        "boot_candidate=false",
    ):
        require(token in receipt, f"generation receipt token: {token}")
    print("validation=a72-physical-source-admission")
    print("prepared_source=exact-through-0349")
    print("generated_patch_count=5")
    print("focused_tests=4")
    print("canonical_admission=0350-0354")
    print("compile=pending")
    print("hardware_operations=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
