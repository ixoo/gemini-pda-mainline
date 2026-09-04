#!/usr/bin/env python3
"""Independently validate the exact stage-18 thermal/frequency boot candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess


ORIGIN = "https://github.com/ixoo/gemini-pda-mainline.git"
PACKAGE_NAME = "linux-7.1.3-gemini-gemini-a72-frequency-thermal-candidate-b7cccd63-18ded825"
PACKAGE_MANIFEST_SHA256 = "b0c13ae492c6882816903fcaa9718629ee55e595a7535b5e28c2bb70eb6854bf"
BUILD_COMMIT = "556575a202e09d25093c578cded454854a3e6d08"
PROFILE = "gemini-a72-frequency-thermal-candidate"
RELEASE = "7.1.3-gemini-a72-frequency-thermal"
IMAGE_GZ_SHA256 = "bb355b5531de49b6aea75f74e6f1340a829a1e602ec1f48a935c64b599d4118d"
SYSTEM_MAP_SHA256 = "724ad03896366e3ce8eeddada7bd743decc5235d81a0cbf277adb4fb911d2bee"
CONFIG_SHA256 = "500b3fb53e403d16fcd00bcc9634148da9ef41ab58eec5b4401f5563e1ac24cf"
BUILD_JSON_SHA256 = "c243ee06650a83ab16ea10e9c0fd679a49bb4125c0b67a3fb02c0600ebb1ab11"
PACKAGE_DTB_SHA256 = "df70033883ae3dc7bee7d3af42e7d1677573c153c24fc295b9b79d919f8722a3"
A41_RECORD_SHA256 = "1cb788595e9af5aa977882308c82938b5d1c1848ae323f4b840172d0994598db"
TOPOLOGY_DTB_SHA256 = "4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923"
THERMAL_OVERLAY_SHA256 = "2f0a9a424d75f3042cabcb54fce0518133deb89a065d5671b87fce287b8cc91a"
PRODUCTION_DTB_SHA256 = "46be0ae62bf66bf8e9f905ec3ad5eebbdc51c79ff3dc21859077ebe3f1aec363"
INITRAMFS_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
DT_VALIDATOR_SHA256 = "b104f6ea11d0b60006dce46b2adaa0827452d643904d33eb5fc65be7ed610fee"
RAW_SHA256 = "398ca636f54a2825ff32f1cba86d06fd55a0a4083c46c77c85a47f0be09804a7"
RAW_SIZE = 7_131_136
PADDED_SHA256 = "ea2aae419220b3c2ea11780f9c91dbb51d509286cd76d2ba1741d9e08e837c9c"
BOOT2_SIZE = 16 * 1024 * 1024
CANDIDATE_NAME = "candidate-mt6797-a72-frequency-zero-divider-398ca636"
DT_NAME = "mt6797-gemini-pda-a72-frequency-thermal.dtb"
INITRAMFS_NAME = "gemini-a72-frequency-thermal-initramfs.img"
BOOT_NAME = "gemini-mt6797-a72-frequency-thermal.boot.img"
CONFIG_INPUTS_SHA256 = "18ded825be6993a5a403f8cd526e3682199cc55afce876f36b7f194faced0b25"
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
PATCHSET_SHA256 = "b7cccd63af8bb60975f4e994e614f8da07b933b76cb18085d5377da938eec169"
CONFIG_BINDING_PATCH_SHA256 = "de831423d783cdc72fd34a9b2705366bac4080d997a37c574dc8d13264d49187"
PRODUCTION_OBSERVER_PATCH_SHA256 = "bcd86ad0b4aa27eb2798fef6630eb4543a8e2edf117e3a33ca73a50b3f24e21d"
FAILURE_TRACE_PATCH_SHA256 = "fbba1a6290082bfafc13612f8d3b32d77dc8aa864424e7865869ea3c1322a851"
FAILURE_TRACE_TEST_PATCH_SHA256 = "575189b39ece9da281f3d7854b210a1a5b0d207b72b83e7263d19aca644f02de"
ZERO_DIVIDER_PATCH_SHA256 = "491711ab7558b549480e2d4ed3f855081ed3c46349ffd8751e758233d9652a7a"
ZERO_DIVIDER_TEST_PATCH_SHA256 = "e92f06ac89c24ca545974e1cf31c7109e6d69677b34fe4f8b244cd7912d5e063"


class CandidateError(ValueError):
    """Candidate validation failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: Path, label: str) -> bytes:
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise CandidateError(f"{label} is missing") from error
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise CandidateError(f"{label} is empty or unsafe")
    return path.read_bytes()


def exact_file(path: Path, expected: str, label: str) -> bytes:
    data = regular(path, label)
    if digest(data) != expected:
        raise CandidateError(f"{label} identity changed")
    return data


def validate_manifest(candidate: Path) -> set[str]:
    lines = regular(candidate / "SHA256SUMS", "candidate manifest").decode().splitlines()
    seen: set[str] = set()
    for line in lines:
        expected, marker, relative = line.partition("  ")
        path = PurePosixPath(relative)
        if (marker != "  " or len(expected) != 64 or path.is_absolute() or
                ".." in path.parts or path.as_posix() in seen):
            raise CandidateError("candidate manifest is malformed")
        seen.add(path.as_posix())
        if digest(regular(candidate / path, f"candidate member {relative}")) != expected:
            raise CandidateError(f"candidate manifest mismatch: {relative}")
    base_members = {
        "Image.gz", "System.map", "kernel.config", "source-build.json",
        "a41-record.json", "package-SHA256SUMS", INITRAMFS_NAME, DT_NAME,
        BOOT_NAME, "boot2-padded.img", "dt-build-validation.txt",
        "dt-independent-validation.txt", "container-validation.txt",
        "provenance.txt",
    }
    if seen not in (base_members, base_members | {"candidate-validation.txt"}):
        raise CandidateError("candidate manifest inventory changed")
    return seen


def validate_config(config: bytes) -> None:
    lines = set(config.decode("ascii").splitlines())
    enabled = (
        "MTK_MT6797_A72_FREQUENCY_OBSERVER",
        "MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER",
        "MTK_MT6797_A72_ADMISSION_CONTROLLER",
        "MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER",
        "MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER",
        "MTK_MT6797_A72_HOTPLUG_EXECUTOR",
        "MTK_MT6797_A72_HOTPLUG_SNAPSHOT",
        "MTK_MT6797_A72_HOTPLUG_BINDER_CORE",
        "MTK_MT6797_A72_HOTPLUG_BINDING",
        "PSTORE_GEMINI_MT6797_THERMAL_LEDGER",
        "THERMAL",
    )
    for symbol in enabled:
        if f"CONFIG_{symbol}=y" not in lines:
            raise CandidateError(f"production symbol is absent: {symbol}")
    if 'CONFIG_LOCALVERSION="-gemini-a72-frequency-thermal"' not in lines:
        raise CandidateError("local version changed")
    for symbol in ("KUNIT", "CPU_FREQ", "CPU_IDLE", "SUSPEND"):
        if f"# CONFIG_{symbol} is not set" not in lines:
            raise CandidateError(f"closed policy changed: {symbol}")


def validate_production_registration(
        package: Path, system_map: bytes, build: dict[str, object]) -> None:
    """Prove the packaged observer is linked through the production owner."""
    if build.get("config_inputs_sha256") != CONFIG_INPUTS_SHA256:
        raise CandidateError("production configuration identity changed")
    binding = exact_file(
        package / "provenance/patches/v7.1.3/"
        "0529-arm64-bind-Gemini-frequency-thermal-configuration.patch",
        CONFIG_BINDING_PATCH_SHA256, "production configuration binding patch",
    ).decode("ascii")
    observer = exact_file(
        package / "provenance/patches/v7.1.3/"
        "0530-soc-mediatek-attach-A72-frequency-observer-to-production.patch",
        PRODUCTION_OBSERVER_PATCH_SHA256, "production observer patch",
    ).decode("ascii")
    exact_file(
        package / "provenance/patches/v7.1.3/"
        "0531-soc-mediatek-trace-A72-frequency-observer-failures.patch",
        FAILURE_TRACE_PATCH_SHA256, "frequency failure trace patch",
    )
    exact_file(
        package / "provenance/patches/v7.1.3/"
        "0532-soc-mediatek-test-A72-frequency-observer-failure-trace.patch",
        FAILURE_TRACE_TEST_PATCH_SHA256, "frequency failure trace test patch",
    )
    exact_file(
        package / "provenance/patches/v7.1.3/"
        "0533-soc-mediatek-accept-zero-MT6797-clock-divider.patch",
        ZERO_DIVIDER_PATCH_SHA256, "zero-divider production repair patch",
    )
    exact_file(
        package / "provenance/patches/v7.1.3/"
        "0534-soc-mediatek-test-live-zero-divider-clock-state.patch",
        ZERO_DIVIDER_TEST_PATCH_SHA256, "zero-divider focused test patch",
    )
    for token in (
        "0x18ded825be6993a5, 0xa403f8cd526e3682",
        "0x2e50cc09d2241006, 0xd819eeb0ed4151fb",
    ):
        if binding.count(token) != 1:
            raise CandidateError("production binding identity proof changed")
    observer_tokens = {
        "struct mt6797_a72_hotplug_snapshot_source frequency_source;": 1,
        "mt6797_a72_hotplug_snapshot_source_init(": 1,
        "&controller->frequency_source, platform, clock, bigidvfs);": 1,
        "return mt6797_a72_frequency_observer_render(": 2,
        "dev, &controller->frequency_source, buf);": 1,
        "&mt6797_a72_admission_frequency_group);": 1,
    }
    for token, expected in observer_tokens.items():
        if observer.count(token) != expected:
            raise CandidateError("production observer source proof changed")
    symbols = [line.rsplit(" ", 1)[-1] for line in system_map.decode("ascii").splitlines()]
    expected_counts = {
        "mt6797_a72_frequency_observer_render": 1,
        "a72_frequency_observation_show": 2,
        "mt6797_a72_admission_prepare": 1,
        "mt6797_a72_admission_probe": 1,
        "trigger_store": 1,
        "dev_attr_a72_frequency_observation": 2,
    }
    for symbol, expected in expected_counts.items():
        if symbols.count(symbol) != expected:
            raise CandidateError(
                f"production registration symbol count changed: {symbol}"
            )
    for excluded in ("mt6797_a72_frequency_observer_suite", "hotplug_binding_suite"):
        if excluded in symbols:
            raise CandidateError(f"KUnit symbol linked into production: {excluded}")


def validate(args: argparse.Namespace) -> None:
    repository = args.repository.resolve(strict=True)
    package = args.package.resolve(strict=True)
    candidate = args.candidate.resolve(strict=True)
    if subprocess.check_output(
            ["git", "-C", os.fspath(repository), "remote", "get-url", "origin"],
            text=True).strip() != ORIGIN:
        raise CandidateError("origin URL changed")
    if package.name != PACKAGE_NAME or package.is_symlink() or not package.is_dir():
        raise CandidateError("package directory identity changed")
    if candidate.name != CANDIDATE_NAME or candidate.is_symlink() or not candidate.is_dir():
        raise CandidateError("candidate directory identity changed")

    exact_file(package / "SHA256SUMS", PACKAGE_MANIFEST_SHA256,
               "package manifest")
    subprocess.run(
        ["sha256sum", "--check", "--strict", "SHA256SUMS"], cwd=package,
        check=True, stdout=subprocess.DEVNULL,
    )
    image_gz = exact_file(package / "Image.gz", IMAGE_GZ_SHA256,
                          "package Image.gz")
    system_map = exact_file(package / "System.map", SYSTEM_MAP_SHA256,
                            "package System.map")
    config = exact_file(package / "kernel.config", CONFIG_SHA256,
                        "package configuration")
    build_json = exact_file(package / "provenance/build.json", BUILD_JSON_SHA256,
                            "package build provenance")
    package_dtb = exact_file(
        package / "dtbs/mediatek/mt6797-gemini-pda.dtb",
        PACKAGE_DTB_SHA256, "package DT",
    )
    a41_record = exact_file(package / "provenance/a41-record.json",
                            A41_RECORD_SHA256, "package A41 record")
    validate_config(config)
    build = json.loads(build_json)
    if (build.get("repository_commit") != BUILD_COMMIT or
            build.get("repository_dirty") is not False or
            build.get("build_profile") != PROFILE or
            build.get("kernel_release") != RELEASE or
            build.get("source_sha256") != SOURCE_SHA256 or
            build.get("patchset_sha256") != PATCHSET_SHA256 or
            build.get("target_architecture") != "arm64" or
            build.get("modules_built") is not False):
        raise CandidateError("package build contract changed")
    validate_production_registration(package, system_map, build)

    topology = exact_file(args.topology_dtb.resolve(strict=True),
                          TOPOLOGY_DTB_SHA256, "topology DT")
    thermal = exact_file(args.thermal_overlay.resolve(strict=True),
                         THERMAL_OVERLAY_SHA256, "thermal overlay source")
    ramdisk = exact_file(args.ramdisk.resolve(strict=True), INITRAMFS_SHA256,
                         "runtime-proven initramfs")
    del topology, thermal
    members = validate_manifest(candidate)
    for name, expected_data in (
        ("Image.gz", image_gz),
        ("System.map", system_map),
        ("kernel.config", config),
        ("source-build.json", build_json),
        ("a41-record.json", a41_record),
        ("package-SHA256SUMS", regular(package / "SHA256SUMS", "package manifest")),
        (INITRAMFS_NAME, ramdisk),
    ):
        if regular(candidate / name, f"candidate {name}") != expected_data:
            raise CandidateError(f"candidate member differs from source: {name}")
    exact_file(candidate / DT_NAME, PRODUCTION_DTB_SHA256, "candidate DT")

    script_dir = Path(__file__).resolve().parent
    dt_validator = script_dir / "validate-production-dtb.py"
    exact_file(dt_validator, DT_VALIDATOR_SHA256, "production DT validator")
    subprocess.run([
        os.fspath(dt_validator),
        "--topology-dtb", os.fspath(args.topology_dtb),
        "--thermal-overlay", os.fspath(args.thermal_overlay),
        "--package-dtb", os.fspath(package / "dtbs/mediatek/mt6797-gemini-pda.dtb"),
        "--record-json", os.fspath(package / "provenance/a41-record.json"),
        "--candidate", os.fspath(candidate / DT_NAME),
    ], check=True, stdout=subprocess.DEVNULL)

    serializer = repository / (
        "experiments/2026-07-12-boot-contract-recovery/scripts/"
        "build-android-boot-v0.py"
    )
    analyzer = repository / (
        "experiments/2026-07-12-boot-contract-recovery/scripts/"
        "analyze-lk-boot-image.py"
    )
    exact_file(serializer, SERIALIZER_SHA256, "container serializer")
    exact_file(analyzer, ANALYZER_SHA256, "container analyzer")
    raw_path = candidate / BOOT_NAME
    subprocess.run([
        os.fspath(analyzer), "--validate-lk",
        "--expected-image-gz", os.fspath(candidate / "Image.gz"),
        "--expected-ramdisk", os.fspath(candidate / INITRAMFS_NAME),
        "--expected-dtb", os.fspath(candidate / DT_NAME),
        "--expected-name", "gemini-a72freq",
        "--expected-cmdline", "bootopt=64S3,32N2,64N2",
        os.fspath(raw_path),
    ], check=True, stdout=subprocess.DEVNULL)
    raw = exact_file(raw_path, RAW_SHA256, "raw candidate")
    padded = exact_file(candidate / "boot2-padded.img", PADDED_SHA256,
                        "padded candidate")
    if len(raw) != RAW_SIZE or len(padded) != BOOT2_SIZE:
        raise CandidateError("candidate size changed")
    if padded[:len(raw)] != raw or any(padded[len(raw):]):
        raise CandidateError("exact zero-padding contract failed")

    provenance = dict(
        line.split("=", 1) for line in
        regular(candidate / "provenance.txt", "candidate provenance").decode().splitlines()
    )
    expected_provenance = {
        "experiment": "2026-09-04-mt6797-a72-frequency-observation",
        "variant": "stage18-thermal-frequency-zero-divider-repair",
        "repository_commit": BUILD_COMMIT,
        "profile": PROFILE,
        "kernel_release": RELEASE,
        "package_manifest_sha256": PACKAGE_MANIFEST_SHA256,
        "image_gz_sha256": IMAGE_GZ_SHA256,
        "config_sha256": CONFIG_SHA256,
        "topology_dtb_sha256": TOPOLOGY_DTB_SHA256,
        "thermal_overlay_sha256": THERMAL_OVERLAY_SHA256,
        "production_dtb_sha256": PRODUCTION_DTB_SHA256,
        "a41_record_sha256": A41_RECORD_SHA256,
        "initramfs_sha256": INITRAMFS_SHA256,
        "candidate_raw_sha256": RAW_SHA256,
        "candidate_raw_size": str(RAW_SIZE),
        "candidate_padded_sha256": PADDED_SHA256,
        "candidate_padded_size": str(BOOT2_SIZE),
        "dt_delta": "exact-thermal-transform-plus-one-package-provenance-leaf",
        "cpu_topology": "4+4+2",
        "thermal_zones": "1",
        "thermal_trips": "0",
        "cooling_maps": "0",
        "frequency_observer_attempts": "3",
        "cpufreq_idle_suspend": "disabled",
        "device_action": "none",
        "hardware_write": "none",
    }
    if provenance != expected_provenance:
        raise CandidateError("candidate provenance changed")
    for filename, tokens in (
        ("dt-build-validation.txt", (
            b"validation=mt6797-a72-frequency-thermal-production-dtb",
            f"output_dtb_sha256={PRODUCTION_DTB_SHA256}".encode(), b"result=pass",
        )),
        ("dt-independent-validation.txt", (
            b"validation=mt6797-a72-frequency-thermal-production-dtb-independent",
            b"dt_delta=exact-thermal-transform-plus-one-package-provenance-leaf",
            b"result=pass",
        )),
        ("container-validation.txt", (
            b"lk_validation=passed", b"expected_dtb_matches=yes",
            b"expected_image_gz_matches=yes", b"expected_ramdisk_matches=yes",
        )),
    ):
        content = regular(candidate / filename, filename)
        if any(token not in content for token in tokens):
            raise CandidateError(f"validation evidence changed: {filename}")
    if "candidate-validation.txt" in members:
        content = regular(candidate / "candidate-validation.txt",
                          "candidate validation")
        for token in (b"boot_candidate=true", b"result=pass"):
            if token not in content:
                raise CandidateError("saved candidate validation changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--ramdisk", required=True, type=Path)
    parser.add_argument("--topology-dtb", required=True, type=Path)
    parser.add_argument("--thermal-overlay", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    try:
        validate(args)
    except (CandidateError, KeyError, OSError, UnicodeError,
            subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print("validation=mt6797-a72-frequency-thermal-production-candidate-independent")
    print(f"candidate_raw_sha256={RAW_SHA256}")
    print(f"candidate_raw_size={RAW_SIZE}")
    print(f"candidate_padded_sha256={PADDED_SHA256}")
    print(f"candidate_padded_size={BOOT2_SIZE}")
    print(f"candidate_dtb_sha256={PRODUCTION_DTB_SHA256}")
    print("configuration=stage18-plus-thermal-plus-three-attempt-read-only-observer")
    print("production_registration_oracle=pass")
    print("cpu_topology=4+4+2")
    print("cpufreq_idle_suspend=disabled")
    print("device_action=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
