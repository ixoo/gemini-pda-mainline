#!/usr/bin/env python3
"""Independently validate the exact A72 physical-source boot candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
REPOSITORY_COMMIT = "f3bf03f4c2515e9c1ac5049c6544c618aaeb8af1"
PROFILE = "a72-physical-source-candidate"
RELEASE = "7.1.3-gemini-a72-physical-source"
PACKAGE_NAME = "linux-7.1.3-gemini-a72-physical-source-candidate-b2cd59e6-a48e2c2d"
IMAGE_SHA256 = "1cde8722a28029de498436315eee61027596db19cdee4a2a7224ece079bd7079"
IMAGE_GZIP_SHA256 = "9ecefb990bd0cf136d32f443ebb59597de48a814df84e2dccf3669c600aac3b9"
DTB_SHA256 = "fe67420ca4e2955a73a4a3f2e442af3534b621820cf77ae035be9bf98756425d"
CONFIG_SHA256 = "39a5a007937d10f50e79da865feda843a06c0ed98301333b9f5c24bbd1808f99"
SYSTEM_MAP_SHA256 = "f139629d79deb15726381c898c79ca4e57973da8188e6d4addab9a0ffd9008ef"
BUILD_JSON_SHA256 = "92120e48a478bdbd3aac78f69c3ea00dbc82b86111bebcf022f3d6493c3f180f"
PACKAGE_MANIFEST_SHA256 = "9bcc4a90075f659e4ab423bd6bbcf0eefb1a9f2fe4a9929f44701021d642e52c"
RAMDISK_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
RAW_SHA256 = "1d0c1420ca2a1ea7c88d22ffeda44c2fa14d238ebceeb73ce7d56133bac4f005"
PADDED_SHA256 = "aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246"
RAW_SIZE = 6_912_000
BOOT2_SIZE = 16_777_216
BOOT_NAME = "gemini-a72src"
BOOT_CMDLINE = "bootopt=64S3,32N2,64N2"
BOOT_FILE = "gemini-mt6797-a72-physical-source.boot.img"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular(path: Path) -> None:
    require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
            f"missing, empty, or unsafe input: {path}")


def fdtget(dtb: Path, node: str, prop: str, kind: str = "s") -> str:
    return subprocess.run(
        ["fdtget", "-t", kind, str(dtb), node, prop],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    package = args.package.resolve()
    ramdisk = args.ramdisk.resolve()
    require(artifact.name == f"candidate-a72-physical-source-{RAW_SHA256[:8]}",
            "artifact directory identity changed")
    require(package.name == PACKAGE_NAME, "package directory identity changed")

    image = package / "Image"
    image_gz = package / "Image.gz"
    config = package / "kernel.config"
    system_map = package / "System.map"
    dtb = package / "dtbs/mediatek/mt6797-gemini-pda-a72-physical-source.dtb"
    build_json = package / "provenance/build.json"
    package_manifest = package / "SHA256SUMS"
    analyzer = ROOT / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
    raw = artifact / BOOT_FILE
    padded = artifact / "boot2-padded.img"
    artifact_manifest = artifact / "SHA256SUMS"
    provenance = artifact / "provenance.txt"
    container_analysis = artifact / "container-analysis.txt"
    for path in (image, image_gz, config, system_map, dtb, build_json,
                 package_manifest, ramdisk, analyzer, raw, padded,
                 artifact_manifest, provenance, container_analysis):
        regular(path)

    expected_hashes = {
        image: IMAGE_SHA256,
        image_gz: IMAGE_GZIP_SHA256,
        config: CONFIG_SHA256,
        system_map: SYSTEM_MAP_SHA256,
        dtb: DTB_SHA256,
        build_json: BUILD_JSON_SHA256,
        package_manifest: PACKAGE_MANIFEST_SHA256,
        ramdisk: RAMDISK_SHA256,
        analyzer: ANALYZER_SHA256,
        raw: RAW_SHA256,
        padded: PADDED_SHA256,
    }
    for path, expected in expected_hashes.items():
        require(sha256(path) == expected, f"identity changed: {path.name}")
    subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"],
                   cwd=package, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"],
                   cwd=artifact, check=True, stdout=subprocess.DEVNULL)

    build = json.loads(build_json.read_text(encoding="utf-8"))
    require(build["repository_commit"] == REPOSITORY_COMMIT,
            "package repository commit changed")
    require(build["repository_dirty"] is False, "package source was dirty")
    require(build["build_profile"] == PROFILE, "package profile changed")
    require(build["kernel_release"] == RELEASE, "kernel release changed")
    require(build["config_sha256"] == CONFIG_SHA256,
            "build-record configuration identity changed")

    config_text = config.read_text(encoding="utf-8")
    for line in (
        "CONFIG_MODULES=y",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR=y",
        "CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y",
        "CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y",
        "CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y",
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y",
        "# CONFIG_KUNIT is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-physical-source"',
    ):
        require(config_text.count(line + "\n") == 1,
                f"configuration gate changed: {line}")
    for symbol in (
        "PSTORE_GEMINI_PRE_RAMOOPS_LEDGER",
        "PSTORE_GEMINI_ARM64_ENTRY_LEDGER",
        "PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL",
        "PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER",
        "PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",
        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",
        "PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION",
        "PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION",
        "MTK_MT6797_PROTECTED_READBACK_OBSERVER",
        "ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR",
        "ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER",
        "REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION",
        "MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW",
        "REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE",
    ):
        require(f"CONFIG_{symbol}=y" not in config_text,
                f"forbidden action or ledger enabled: {symbol}")
    require(re.search(r'^CONFIG_CMDLINE=".*maxcpus=8(?: |")', config_text,
                      re.MULTILINE) is not None,
            "maxcpus=8 closure is absent")

    symbols = system_map.read_text(encoding="utf-8")
    for symbol in (
        "mt6797_a72_physical_source_capture",
        "mt6797_a72_physical_source_run",
        "mt6797_a72_direct_source_register",
        "mt6797_a72_direct_state_snapshot",
        "mt6797_a72_direct_source_unregister",
        "mt6797_a72_provider_snapshot",
        "mt6797_a72_platform_state_snapshot",
        "mt6797_dvfsp_clock_backend_read",
        "mt6797_bigidvfs_backend_read",
        "gemini_protected_readback_ledger_checkpoint",
    ):
        require(len(re.findall(rf" [A-Za-z] {re.escape(symbol)}$", symbols,
                               re.MULTILINE)) == 1,
                f"required symbol absent or duplicated: {symbol}")
    for symbol in (
        "mt6797_a72_a34_evaluate",
        "mt6797_a72_atomic_publish",
        "da9213_legacy_provider_transaction_acquire",
        "da9213_legacy_provider_transaction_release",
        "da9213_legacy_same_value_write",
    ):
        require(re.search(rf" [A-Za-z] {re.escape(symbol)}$", symbols,
                          re.MULTILINE) is None,
                f"forbidden symbol linked: {symbol}")

    image_bytes = image.read_bytes()
    for marker in (
        b"GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=before-bigidvfs slot=1 crc32=47eaad49",
        b"GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=after-bigidvfs slot=2 crc32=d03ca6dc",
        b"GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete registrations=1 callbacks=1 unregisters=1 platform_calls=1 provider_snapshots=1 clock_calls=1 retained_writes=2 bigidvfs_calls=1 bigidvfs_smc_reads=8 compositor_retries=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0",
    ):
        require(image_bytes.count(marker) == 1, "Image marker changed")

    observer = "/a72-physical-source-observer"
    platform = "/a72-platform-state@10222000"
    clock = "/dvfsp-clock-backend@1001a000"
    bigidvfs = "/dvfsp-bigidvfs-backend"
    require(fdtget(dtb, observer, "compatible") ==
            "mediatek,mt6797-a72-physical-source-observer",
            "observer compatible changed")
    for node in (observer, platform, clock, bigidvfs):
        require(fdtget(dtb, node, "status") == "okay",
                f"candidate node is not okay: {node}")
    require(fdtget(dtb, bigidvfs, "method") == "smc",
            "BigiDVFS method changed")
    require(fdtget(dtb, "/dvfsp-resource-owner", "status") == "disabled",
            "unrelated resource owner became active")
    for prop, node in (
        ("mediatek,platform-state", platform),
        ("mediatek,clock-backend", clock),
        ("mediatek,bigidvfs-backend", bigidvfs),
    ):
        require(fdtget(dtb, observer, prop, "x") == fdtget(dtb, node, "phandle", "x"),
                f"observer phandle changed: {prop}")

    require(raw.stat().st_size == RAW_SIZE, "raw candidate size changed")
    require(padded.stat().st_size == BOOT2_SIZE, "padded candidate size changed")
    raw_bytes = raw.read_bytes()
    padded_bytes = padded.read_bytes()
    require(padded_bytes[:RAW_SIZE] == raw_bytes, "padded prefix differs from raw candidate")
    require(not any(padded_bytes[RAW_SIZE:]), "padded tail is not all zero")
    analysis = subprocess.run(
        ["python3", str(analyzer), "--validate-lk",
         "--expected-image-gz", str(image_gz),
         "--expected-ramdisk", str(ramdisk), "--expected-dtb", str(dtb),
         "--expected-name", BOOT_NAME, "--expected-cmdline", BOOT_CMDLINE,
         str(raw)],
        check=True, capture_output=True, text=True,
    ).stdout
    require(len(re.findall(r"^gate_.*=yes$", analysis, re.MULTILINE)) == 32,
            "independent analyzer did not pass 32 gates")
    require("lk_validation=passed\n" in analysis and
            "lk_validation_failures=none\n" in analysis,
            "independent LK validation failed")
    require("boot_candidate=pending-independent-validation\n" in
            provenance.read_text(encoding="utf-8"),
            "builder provenance state changed")
    require(container_analysis.read_text(encoding="utf-8").count(
            "lk_validation=passed\n") == 1,
            "builder container analysis changed")

    print("validation=a72-physical-source-candidate-independent")
    print(f"repository_commit={REPOSITORY_COMMIT}")
    print(f"profile={PROFILE}")
    print(f"kernel_release={RELEASE}")
    print(f"candidate_sha256={RAW_SHA256}")
    print(f"candidate_size={RAW_SIZE}")
    print(f"padded_sha256={PADDED_SHA256}")
    print(f"padded_size={BOOT2_SIZE}")
    print("lk_gates=32-of-32")
    print("retained_writes_maximum=2")
    print("platform_calls=1")
    print("provider_snapshots=1")
    print("clock_calls=1")
    print("bigidvfs_calls=1")
    print("bigidvfs_smc_reads=8")
    print("provider_transactions=0")
    print("publisher_calls=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
