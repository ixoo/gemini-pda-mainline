#!/usr/bin/env python3
"""Validate canonical patch admission, isolated profiles, and KUnit lane."""

from __future__ import annotations

import hashlib
import json
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
    require(path.is_file() and not path.is_symlink(), f"safe file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    experiment = root / "experiments" / EXPERIMENT
    contract = json.loads(read(experiment / "contract.json"))
    series = read(root / "patches/series").splitlines()
    expected_tail = [f"v7.1.3/{patch}" for patch in PATCHES]
    require(series[-4:] == expected_tail, "canonical series tail")
    hashes = contract["canonical_patch_sha256"]
    for patch in PATCHES:
        path = root / "patches/v7.1.3" / patch
        require(hashlib.sha256(path.read_bytes()).hexdigest() == hashes[patch],
                f"canonical patch identity: {patch}")

    manifest = json.loads(read(root / "kernel/manifest.json"))
    profiles = manifest["config"]["profiles"]
    profile_fragments = {
        "a72-platform-provider-snapshot-kunit":
            "configs/gemini-a72-platform-provider-snapshot-kunit.fragment",
        "a72-platform-provider-snapshot-candidate":
            "configs/gemini-a72-platform-provider-snapshot-candidate.fragment",
    }
    for name, final_fragment in profile_fragments.items():
        profile = profiles[name]
        require(profile["base"] == "defconfig", f"profile base: {name}")
        require(profile["patch_series"] == "patches/series",
                f"profile series: {name}")
        require(profile["fragments"][-1] == final_fragment,
                f"profile final fragment: {name}")
        require("configs/gemini-da921x-positive-provider.fragment"
                not in profile["fragments"], f"positive writer absent: {name}")
        require("configs/gemini-i2c6-firmware-writer-transaction-window.fragment"
                not in profile["fragments"], f"writer window absent: {name}")

    kunit = read(root / profile_fragments[
        "a72-platform-provider-snapshot-kunit"])
    for token in (
        "CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_KUNIT_TEST=y",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-provider-kunit"',
    ):
        require(token in kunit, f"KUnit fragment token: {token}")
    candidate = read(root / profile_fragments[
        "a72-platform-provider-snapshot-candidate"])
    for token in (
        "CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER=y",
        "CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER=y",
        "# CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW is not set",
        "# CONFIG_KUNIT is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-provider-read"',
    ):
        require(token in candidate, f"candidate fragment token: {token}")

    runner = read(experiment / "scripts/run-kunit-qemu")
    classifier = read(experiment / "scripts/classify-kunit.py")
    classifier_test = read(experiment / "scripts/test-kunit-classifier.py")
    for token in (
        "EXPECTED_PROFILE=a72-platform-provider-snapshot-kunit",
        "CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_KUNIT_TEST=y",
        "mt6797_a72_pp_capture",
        "mt6797_a72_provider_snapshot",
        "-nic none",
    ):
        require(token in runner, f"KUnit runner token: {token}")
    for token in (
        'SUITE = "mt6797-a72-platform-provider-snapshot"',
        'require(ktap.count("1..6") == 1',
        'print("tests=6")',
        'print("boot_candidate=false")',
    ):
        require(token in classifier, f"KUnit classifier token: {token}")
    require('mutations_rejected=8' in classifier_test,
            "classifier mutation gate")

    receipt = read(experiment / "results/buildbox-generation-20260825.txt")
    for token in (
        "repository_commit=170f3732ae7703fd7654c744ae29754ed9255a2a",
        "canonical_patch_bytes=all-four-cmp-pass",
        "profiles_checked=131",
        "kernel_build=pending",
        "device_action=none",
    ):
        require(token in receipt, f"generation receipt token: {token}")
    print("admission_validation=pass")
    print("canonical_patches=4")
    print("isolated_profiles=2")
    print("focused_kunit_cases=6")


if __name__ == "__main__":
    main()
