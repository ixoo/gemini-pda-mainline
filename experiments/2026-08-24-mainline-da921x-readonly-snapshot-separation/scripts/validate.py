#!/usr/bin/env python3
"""Validate the DA921x read-only snapshot generation input."""

from __future__ import annotations

import hashlib
import json
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
    generation = contract["validated_generation"]
    require(generation == {
        "repository_commit":
            "866d528c6454cd1fd49c4446ac432791984af61f",
        "buildbox_job":
            "866d528c6454cd1fd49c4446ac432791984af61f-da921x-readonly-snapshot-patchgen",
        "package": "da921x-readonly-snapshot-866d528c6454",
        "parent_commit": "fd7b8191422ce4736406c49560603da11d73471c",
        "result_commit": "9a937ed6aad8b508b6f67758446656ec0c4ac48c",
        "sha256sums_sha256":
            "826041bc713c8ed0182dcdf8cf3860f9e13622213047b6c9c1b05d7407f3895c",
        "patch_sha256": [
            "d88c1f19b9d921223b94783d132f29b6f760f2634ecfade1d5fa91607cbb316b",
            "f1ffac88aa2536246293d9718202eb94246b4ba69be0ddb62f9a2b6048b83445",
        ],
        "source_validation": "pass",
        "patch_replay": "pass",
        "strict_checkpatch": "0-errors-0-warnings-0-checks",
        "canonical_admission": "0348-0349",
    }, "validated generation")
    build = contract["validated_build"]
    require(
        build["repository_commit"]
        == "e1ecf96c2132de58681b4abb17a7fe409c5a704f",
        "validated build commit",
    )
    require(build["profile"] == "da921x-readonly-snapshot-kunit",
            "validated build profile")
    require(build["patch_count"] == 338, "validated build patch count")
    require(build["modules_built"] is False, "validated build modules")
    require(build["snapshot_symbol"] == "present",
            "validated snapshot symbol")
    require(build["writer_symbols"] == "absent",
            "validated writer symbols")
    require(build["qemu"] == {
        "observed_utc": "2026-08-24T12:43:29Z",
        "runner": "qemu-system-aarch64-11.0.2",
        "machine": "virt-cortex-a53-four-vcpu-no-network",
        "raw_log_sha256":
            "26457e64180ec7e943480cf27853fdb11aa2f3acd83b25aca949ee7351a91001",
        "suite": "da9213-legacy-provider-snapshot",
        "planned_cases": 5,
        "passed_cases": 5,
        "failed_cases": 0,
        "skipped_cases": 0,
        "post_test_state": "expected-vm-rootfs-panic",
        "qemu_exit": 124,
        "classifier": "pass",
    }, "validated QEMU result")
    require(contract["result"] == "phase-a-pass", "result state")

    canonical = [
        ROOT / "patches/v7.1.3" / patch for patch in contract["patches"]
    ]
    require(all(path.is_file() and not path.is_symlink() for path in canonical),
            "canonical patch inventory")
    require([sha256(path) for path in canonical] == generation["patch_sha256"],
            "canonical patch identities")
    series = (ROOT / "patches/series").read_text().splitlines()
    phase_a_series = [
        "v7.1.3/0348-regulator-separate-read-only-DA921x-provider-snapshot.patch",
        "v7.1.3/0349-regulator-test-read-only-DA921x-provider-snapshot.patch",
    ]
    phase_a_index = series.index(phase_a_series[0])
    require(series[phase_a_index:phase_a_index + 2] == phase_a_series,
            "canonical Phase A series order")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profile = manifest["config"]["profiles"]["da921x-readonly-snapshot-kunit"]
    require(profile["base"] == "defconfig", "profile base")
    require(profile["patch_series"] == "patches/series", "profile series")
    require(profile["fragments"][-1] ==
            "configs/gemini-da921x-readonly-snapshot-kunit.fragment",
            "profile fragment")
    for forbidden_fragment in (
        "configs/gemini-i2c6-firmware-writer-transaction-window.fragment",
        "configs/gemini-da921x-positive-provider.fragment",
        "configs/gemini-a72-pre-p28-provider-abort.fragment",
    ):
        require(forbidden_fragment not in profile["fragments"],
                f"writer-related profile fragment {forbidden_fragment}")
    fragment = (ROOT /
                "configs/gemini-da921x-readonly-snapshot-kunit.fragment").read_text()
    for token in (
        "CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER_SNAPSHOT_KUNIT_TEST=y",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW is not set",
    ):
        require(token in fragment, f"profile token {token}")

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
        "da9213_provider_snapshot_sample",
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
    runner = (EXPERIMENT / "scripts/run-kunit-qemu").read_text()
    classifier = (EXPERIMENT / "scripts/classify-kunit.py").read_text()
    for token in (
        "EXPECTED_PROFILE=da921x-readonly-snapshot-kunit",
        "CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER_SNAPSHOT_KUNIT_TEST=y",
        "da9213_legacy_provider_write_cont",
        "-nic none",
    ):
        require(token in runner, f"runner token {token}")
    for token in (
        'SUITE = "da9213-legacy-provider-snapshot"',
        '"da9213_snapshot_readonly_lifecycle_test"',
        'print("writer_symbols=absent")',
        'print("boot_candidate=false")',
    ):
        require(token in classifier, f"classifier token {token}")
    receipt = (EXPERIMENT /
               "results/buildbox-generation-866d528c.txt").read_text()
    for token in (
        "source_validation=pass",
        "patch_replay=pass",
        "strict_checkpatch=0-errors-0-warnings-0-checks",
        "canonical_admission=0348-0349",
        "compile=pending",
        "boot_candidate=false",
    ):
        require(token in receipt, f"generation receipt token {token}")
    compile_receipt = (EXPERIMENT /
                       "results/buildbox-compile-e1ecf96c.txt").read_text()
    for token in (
        "profile=da921x-readonly-snapshot-kunit",
        "package_checksums=pass",
        "modules_built=false",
        "snapshot_symbol=present",
        "writer_symbols=absent",
        "build=pass",
        "boot_candidate=false",
    ):
        require(token in compile_receipt, f"compile receipt token {token}")
    runtime_receipt = (EXPERIMENT /
                       "results/qemu-attempt-1-success-20260824.txt").read_text()
    for token in (
        "raw_log_sha256=26457e64180ec7e943480cf27853fdb11aa2f3acd83b25aca949ee7351a91001",
        "writer_symbols=absent",
        "suites=1",
        "tests=5",
        "failed=0",
        "skipped=0",
        "tap_summary=pass:5_fail:0_skip:0_total:5",
        "result=pass",
    ):
        require(token in runtime_receipt, f"runtime receipt token {token}")

    print("validation=da921x-readonly-snapshot-phase-a")
    print("prepared_source_state=exact")
    print("generated_patch_count=2")
    print("focused_tests=5")
    print("positive_provider_transaction=false")
    print("writer_transaction_window=false")
    print("hardware_operations=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("canonical_admission=0348-0349")
    print("compile=pass")
    print("snapshot_symbol=present")
    print("writer_symbols=absent")
    print("qemu=pass-5-of-5")
    print("phase_a=complete")
    print("result=pass")


if __name__ == "__main__":
    main()
