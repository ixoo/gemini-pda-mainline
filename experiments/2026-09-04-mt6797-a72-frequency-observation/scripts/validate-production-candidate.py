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
PACKAGE_NAME = "linux-7.1.3-gemini-gemini-a72-frequency-thermal-candidate-0f2a0357-18ded825"
PACKAGE_MANIFEST_SHA256 = "23b649211c6e086f4e1a15e6aec7a3944da13cd2eecd7ccea6c0402b08bdfff3"
BUILD_COMMIT = "5d892a1c83b8ae5099bbfd5d379f726d04c4ebde"
PROFILE = "gemini-a72-frequency-thermal-candidate"
RELEASE = "7.1.3-gemini-a72-frequency-thermal"
IMAGE_GZ_SHA256 = "02eea29808840c669557b08f20c2bdc871dd74b7eeb68c86000a9058a51739e7"
SYSTEM_MAP_SHA256 = "7731728cc1037932403b4c5711e9fc7588b780452df3dd6cf6fe202e101cd2e6"
CONFIG_SHA256 = "500b3fb53e403d16fcd00bcc9634148da9ef41ab58eec5b4401f5563e1ac24cf"
BUILD_JSON_SHA256 = "2f6a6068d234cb58854ceb02427d93154603985541a5a91fff6101a7b8d43e85"
PACKAGE_DTB_SHA256 = "0c3e71d97a32bdf65d9596c8d5a5cd7eb9f062b515d6807ea9a6d36a6910bdf0"
A41_RECORD_SHA256 = "9558c643264303544b27cfb9b0982a8375836b1b1aaacbf1ed235e28d7835297"
TOPOLOGY_DTB_SHA256 = "4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923"
THERMAL_OVERLAY_SHA256 = "2f0a9a424d75f3042cabcb54fce0518133deb89a065d5671b87fce287b8cc91a"
PRODUCTION_DTB_SHA256 = "a4bf5774bfd97ea102594e08047b81ef22187458ef5591e8b8a72d70c2a44214"
INITRAMFS_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
DT_VALIDATOR_SHA256 = "6497f6a408fe6c99edc71895074bdbedbf145cc3fe1c8bbea7daff1b7313a551"
RAW_SHA256 = "24cb227b415a3285e4518318fece7cd1c080659d6132470e2e08d590fa58089f"
RAW_SIZE = 7_133_184
PADDED_SHA256 = "54a02dd0e46d54702284e679847c69f28c64cc392fca97c9b8d1940374484da7"
BOOT2_SIZE = 16 * 1024 * 1024
CANDIDATE_NAME = "candidate-mt6797-a72-frequency-thermal-successor-24cb227b"
DT_NAME = "mt6797-gemini-pda-a72-frequency-thermal.dtb"
INITRAMFS_NAME = "gemini-a72-frequency-thermal-initramfs.img"
BOOT_NAME = "gemini-mt6797-a72-frequency-thermal.boot.img"
CONFIG_INPUTS_SHA256 = "18ded825be6993a5a403f8cd526e3682199cc55afce876f36b7f194faced0b25"
CONFIG_BINDING_PATCH_SHA256 = "de831423d783cdc72fd34a9b2705366bac4080d997a37c574dc8d13264d49187"
PRODUCTION_OBSERVER_PATCH_SHA256 = "bcd86ad0b4aa27eb2798fef6630eb4543a8e2edf117e3a33ca73a50b3f24e21d"


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
        "variant": "stage18-thermal-frequency-production-successor",
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
