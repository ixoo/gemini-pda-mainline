#!/usr/bin/env python3
"""Validate exact patch admission and isolated third-reader profiles."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


EXPERIMENT = "2026-08-25-mainline-a72-platform-provider-protected-clock-third-read"
PATCHES = (
    "0374-pstore-add-Gemini-A72-platform-provider-clock-ledger.patch",
    "0375-dt-bindings-soc-mediatek-add-A72-platform-provider-clock-observer.patch",
    "0376-soc-mediatek-add-A72-platform-provider-clock-observer.patch",
    "0377-soc-mediatek-test-A72-platform-provider-clock-observer.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"safe file: {path}")
    return path.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    experiment = root / "experiments" / EXPERIMENT
    contract = json.loads(read(experiment / "contract.json"))
    series_path = root / "patches/series"
    series = read(series_path).splitlines()
    expected_tail = [f"v7.1.3/{patch}" for patch in PATCHES]
    require(series[-4:] == expected_tail, "canonical series tail")
    hashes = contract["canonical_patch_sha256"]
    for patch in PATCHES:
        path = root / "patches/v7.1.3" / patch
        require(sha256(path) == hashes[patch],
                f"canonical patch identity: {patch}")
    require(sha256(series_path) == contract["canonical_series_sha256"],
            "canonical series identity")

    manifest = json.loads(read(root / "kernel/manifest.json"))
    profiles = manifest["config"]["profiles"]
    profile_fragments = {
        "a72-platform-provider-clock-kunit":
            "configs/gemini-a72-platform-provider-clock-kunit.fragment",
        "a72-platform-provider-clock-candidate":
            "configs/gemini-a72-platform-provider-clock-candidate.fragment",
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
        "a72-platform-provider-clock-kunit"])
    for token in (
        "CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST=y",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER is not set",
        "# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-clock-third-kunit"',
    ):
        require(token in kunit, f"KUnit fragment token: {token}")
    candidate = read(root / profile_fragments[
        "a72-platform-provider-clock-candidate"])
    for token in (
        "CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER=y",
        "CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER=y",
        "# CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW is not set",
        "# CONFIG_KUNIT is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-clock-third"',
    ):
        require(token in candidate, f"candidate fragment token: {token}")

    runner = read(experiment / "scripts/run-kunit-qemu")
    classifier = read(experiment / "scripts/classify-kunit.py")
    classifier_test = read(experiment / "scripts/test-kunit-classifier.py")
    for token in (
        "EXPECTED_PROFILE=a72-platform-provider-clock-kunit",
        "CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST=y",
        "mt6797_a72_ppc_run",
        "mt6797_dvfsp_clock_backend_read",
        "-nic none",
    ):
        require(token in runner, f"KUnit runner token: {token}")
    for token in (
        'SUITE = "mt6797-a72-platform-provider-clock"',
        'require(ktap.count("1..8") == 1',
        'print("tests=8")',
        'print("boot_candidate=false")',
    ):
        require(token in classifier, f"KUnit classifier token: {token}")
    require("mutations_rejected=8" in classifier_test,
            "classifier mutation gate")

    invariant = subprocess.run(
        [str(root / "scripts/validate-manifest-series")],
        check=True, capture_output=True, text=True,
    ).stdout
    require("profiles_checked=135" in invariant,
            "all manifest profiles checked")
    receipt = read(experiment / "results/buildbox-generation-20260825.txt")
    for token in (
        "repository_commit=c89baef5b5adc988f933b6118bf9f0dfe398b8b2",
        "canonical_patch_bytes=all-four-cmp-pass",
        "profiles_checked=135",
        "focused_kunit_cases=8",
        "kernel_build=pending",
        "device_action=none",
    ):
        require(token in receipt, f"generation receipt token: {token}")
    print("admission_validation=pass")
    print("canonical_patches=4")
    print("isolated_profiles=2")
    print("focused_kunit_cases=8")
    print("kernel_build=pending")
    print("device_action=none")


if __name__ == "__main__":
    main()
