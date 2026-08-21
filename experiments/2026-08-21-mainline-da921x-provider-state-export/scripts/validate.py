#!/usr/bin/env python3
"""Validate the DA921x provider-state generation input."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((HERE / "contract.json").read_text())
    require(contract["repository_parent"] ==
            "4b7535ee4a956c91ef6df3ba8451554af3410d35",
            "platform-state evidence parent")
    require(contract["parent"]["source_state"] ==
            "905fb7f5ead29cbe65eaf7f66e41433aea417c2ee15d751ebda6ddf79f19ad8e",
            "managed parent source state")
    require(contract["expected_patches"] == [
        "patches/v7.1.3/0312-arm64-add-read-only-provider-state-snapshot.patch",
        "patches/v7.1.3/0313-regulator-export-stable-DA921x-provider-state.patch",
        "patches/v7.1.3/0314-regulator-test-stable-DA921x-provider-state.patch",
    ], "three logical patch identities")
    require(contract["validated_generation"] == {
        "repository_commit": "80d271fc17601d53835eb09dd4c585de3f4e1378",
        "buildbox_job": (
            "80d271fc17601d53835eb09dd4c585de3f4e1378-"
            "da921x-provider-state-patchgen"
        ),
        "package": "da921x-provider-state-patches-80d271fc1760",
        "baseline_commit": "e0b6bb338557c4e26fcd6e122208deb624f7a3c8",
        "result_commit": "5197911de74bc75b59226ac76354a9091bca0b5b",
        "sha256sums_sha256": (
            "244bee5940f3710f0271c81627bf76f43a0ae8208d0d501ac8bf753b568a1341"
        ),
        "patch_sha256": [
            "0e323b6fee4797661da868cbeeafcff2bcdee5dbe2fab023fcab70e2890d13fc",
            "81d0980afa67d09377acb077ebf1f4c5291d3ea339a7c859aa642f1b20a88f97",
            "1b238a683f57cf9d8eb58caa4c296397f5ff9a9e460a02e2a04d87a285617c7f",
        ],
        "source_validation": "pass",
        "patch_replay": "pass",
        "strict_checkpatch": "0-errors-0-warnings-0-checks",
    }, "validated Buildbox generation identity")
    require(contract["validated_build"] == {
        "repository_commit": "037009eef8e4ae2d05e7dd944b66e198907e9e03",
        "buildbox_job": (
            "037009eef8e4ae2d05e7dd944b66e198907e9e03-"
            "da921x-provider-state-kunit-m0"
        ),
        "artifact": (
            "linux-7.1.3-gemini-da921x-provider-state-kunit-"
            "9aed726d-2f92b4db"
        ),
        "profile": "da921x-provider-state-kunit",
        "kernel_release": "7.1.3-gemini-da921x-provider-state-kunit",
        "generated_utc": "2026-08-21T16:12:45Z",
        "source_sha256": (
            "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
        ),
        "patchset_sha256": (
            "9aed726d33654b164badd5029465db36412cd61cd2e01bffb20abc802744f92b"
        ),
        "patch_count": 304,
        "config_sha256": (
            "c2c5d3bb46fc3807d2573520c00fadacce3e6edbafb6055a2889631fb114ec6d"
        ),
        "image_sha256": (
            "012863beb73026ecc69d9c0733d762e37653ded914d026bcdcbf02c6d7fec3d8"
        ),
        "image_gzip_sha256": (
            "7ee18b2f97c744e01ddd52be9ea3e92f9f86c09d888dd59c3c517aba4128469c"
        ),
        "sha256sums_sha256": (
            "1afb6f3df000cc6c2c00f9e401291cdb5bf4b6ee51b8dc1de19e12debdf7f323"
        ),
        "package_checksums": "pass",
        "qemu": {
            "observed_utc": "2026-08-21T16:15:46Z",
            "runner": "qemu-system-aarch64-11.0.2",
            "machine": "virt-cortex-a53-four-vcpu-no-network",
            "raw_log_sha256": (
                "84ab9797417b0dce39b136cc041c1adc4308d1c5836e7e5383dd62ea044f0080"
            ),
            "suite": "da9213-legacy-membership-provider",
            "planned_cases": 10,
            "passed_cases": 10,
            "failed_cases": 0,
            "skipped_cases": 0,
            "post_test_state": "expected-vm-rootfs-panic",
            "qemu_exit": 124,
            "classifier": "pass",
        },
    }, "validated Buildbox compile and QEMU identity")
    patch_hashes = []
    for relative in contract["expected_patches"]:
        path = ROOT / relative
        require(path.is_file(), f"canonical patch exists: {relative}")
        patch_hashes.append(sha256(path))
    require(patch_hashes == contract["validated_generation"]["patch_sha256"],
            "canonical patch bytes match Buildbox")
    require(contract["scope"] == {
        "samples": 2,
        "reads_on_success": 10,
        "adapter_retries": 0,
        "polling": False,
        "hardware_write": False,
        "delay": False,
        "a34_caller": False,
        "opens_owner": False,
        "cpu_on": False,
        "cpu_off": False,
        "device_action": False,
        "boot_candidate": False,
    }, "closed scope")

    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    for token in (
        "two immediate complete samples under one root",
        "exactly ten reads on success",
        "provider registry mutex -> endpoint mutex -> I2C root-adapter lock",
        "No result in this experiment authorizes CPU8",
    ):
        require(token in readme, f"README token: {token}")
    for token in (
        "does not classify rail ownership",
        "clears the destination before registry lookup",
        "uses local accounting objects",
        "cannot by itself make CPU8 eligible",
    ):
        require(token in design, f"design token: {token}")

    edits = (HERE / "scripts/source_edits.py").read_text()
    for token in (
        "MT6797_A72_PROVIDER_STATE_ABI",
        "mt6797_a72_provider_snapshot",
        "da9213_provider_snapshot",
        "I2C_LOCK_ROOT_ADAPTER",
        "DA9213_PROVIDER_SNAPSHOT_ACTIONS",
        "da9213_provider_snapshot_transport_faults",
    ):
        require(token in edits, f"source edit token: {token}")
    for forbidden in ("cpu_up(", "cpu_down(", "psci_ops"):
        require(forbidden not in edits, f"forbidden edit effect: {forbidden}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-da921x-provider-state-patches",
        "fetch-da921x-provider-state-patches",
        "generate-da921x-provider-state-tag-fix",
        "fetch-da921x-provider-state-tag-fix",
    ):
        require(buildbox.count(command) >= 2,
                f"Buildbox command: {command}")

    runner = (HERE / "scripts/run-kunit-qemu").read_text()
    classifier = (HERE / "scripts/classify-kunit.py").read_text()
    for token in (
        "EXPECTED_PROFILE=da921x-provider-state-kunit",
        "qemu-system-aarch64",
        "-nic none",
        "focused KUnit test inventory changed",
    ):
        require(token in runner, f"QEMU runner token: {token}")
    for token in (
        'PROFILE = "da921x-provider-state-kunit"',
        '"da9213_provider_snapshot_success"',
        '"da9213_provider_snapshot_transport_faults"',
        '"da9213_provider_snapshot_unstable"',
        '"da9213_provider_snapshot_registry_guards"',
        'require(ktap.count("1..10") == 1',
        'print("tests=10")',
        'print("cpu8_cpu9_admission=closed")',
    ):
        require(token in classifier, f"QEMU classifier token: {token}")

    for name in (
        "buildbox-compile-037009ee.txt",
        "qemu-attempt-1-success-20260821.txt",
    ):
        require((HERE / "results" / name).is_file(), f"result receipt: {name}")

    fix = contract["compile_fix"]
    require(fix["expected_patch"] ==
            "patches/v7.1.3/0315-arm64-rename-read-only-provider-snapshot-record.patch",
            "compile-fix patch identity")
    fix_patch = ROOT / fix["expected_patch"]
    require(fix_patch.is_file(), "canonical compile-fix patch exists")
    require(sha256(fix_patch) ==
            fix["validated_generation"]["patch_sha256"],
            "canonical compile-fix bytes match Buildbox")
    require(fix["validated_generation"]["strict_checkpatch"] ==
            "0-errors-0-warnings-0-checks",
            "compile-fix strict checkpatch")

    series = (ROOT / "patches/series").read_text().splitlines()
    require(series[-4:] == [
        path.removeprefix("patches/")
        for path in contract["expected_patches"]
    ] + [fix["expected_patch"].removeprefix("patches/")],
            "canonical series tail")
    fragment = (
        ROOT / "configs/gemini-da921x-provider-state-kunit.fragment"
    ).read_text()
    for token in (
        "CONFIG_KUNIT=y",
        "CONFIG_REGULATOR_DA9213_LEGACY_MEMBERSHIP_KUNIT_TEST=y",
        'CONFIG_LOCALVERSION="-gemini-da921x-provider-state-kunit"',
    ):
        require(token in fragment, f"profile fragment token: {token}")
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profile = manifest["config"]["profiles"]["da921x-provider-state-kunit"]
    require(profile["patch_series"] == "patches/series",
            "profile selects canonical series")
    require(profile["fragments"][-1] ==
            "configs/gemini-da921x-provider-state-kunit.fragment",
            "profile selects snapshot KUnit fragment")

    print("design_validation=pass")
    print("expected_patch_count=3")
    print("hardware_write=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
