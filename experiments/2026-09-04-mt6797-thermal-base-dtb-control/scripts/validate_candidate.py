#!/usr/bin/env python3
"""Validate the exact MT6797 thermal base-DT control candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path, PurePosixPath


ORIGIN = "https://github.com/ixoo/gemini-pda-mainline.git"
BUILD_COMMIT = "b66b03c722cd67584fb8fb15de493ebb084954b4"
PACKAGE_VALIDATOR_SHA256 = "0bec8097f36e2831a19239810d4faf2d1f74fe480f80e9391ecad703ccdf9191"
SOURCE_DIR = "candidate-mt6797-pwrap-reset-305230b1"
SOURCE_MANIFEST_SHA256 = "528f38ae3459149bc6f12242118b69d104590bd8902eef7d3969a1cd1b8d0f17"
SOURCE_INITRAMFS = "gemini-pwrap-reset-serviceability-initramfs.img"
SOURCE_INITRAMFS_SHA256 = "344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b"
PACKAGE_DTB = "dtbs/mediatek/mt6797-gemini-pda.dtb"
DTB_SHA256 = "d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc"
CANDIDATE_DIR = "candidate-mt6797-thermal-base-dtb-control-fb660f34"
CANDIDATE_DTB = "mt6797-gemini-pda.dtb"
CANDIDATE_INITRAMFS = "gemini-mt6797-thermal-base-dtb-control-initramfs.img"
CANDIDATE_BOOT = "gemini-mt6797-thermal-base-dtb-control.boot.img"
PADDED_BOOT = "boot2-padded.img"
BOOT2_SIZE = 16 * 1024 * 1024
RAW_SIZE = 7_557_120
RAW_SHA256 = "fb660f34d631109eeeaa5625c457e141ff0beadafbdbf47375f11d11ca9e449d"
PADDED_SHA256 = "ec26245757291c4d7761683b7afc8042cc8bf98fd34a4c977946cf23a5147db5"
IMAGE_GZ_SHA256 = "3e1ebb8de1aeb9ff1c6c6cbe655f18d1affd751959967bfd85507d280dedd2a2"
SYSTEM_MAP_SHA256 = "dc7809a74259d616afe263a3f2846cd48edf1e6cbafe5d68483f844604f78c88"
CONFIG_SHA256 = "f0a135b24055229447d56ae6bda16e1ada683ebe4612af3ba0b96ec7febd375a"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"


class CandidateError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise CandidateError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def run_package_validator(repository: Path, package: Path) -> None:
    validator = repository / "experiments/2026-09-04-mt6797-thermal-stage-ledger/scripts/validate_package.py"
    if digest(regular(validator, "package validator")) != PACKAGE_VALIDATOR_SHA256:
        raise CandidateError("pinned package validator changed")
    subprocess.run(
        [os.fspath(validator), "--repository", os.fspath(repository), "--package", os.fspath(package)],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def validate(repository: Path, package: Path, source: Path, candidate: Path) -> None:
    if subprocess.check_output(
        ["git", "-C", os.fspath(repository), "remote", "get-url", "origin"], text=True
    ).strip() != ORIGIN:
        raise CandidateError("origin URL changed")
    run_package_validator(repository, package)
    if source.name != SOURCE_DIR or source.is_symlink() or not source.is_dir():
        raise CandidateError("initramfs source identity changed")
    if digest(regular(source / "SHA256SUMS", "source manifest")) != SOURCE_MANIFEST_SHA256:
        raise CandidateError("source manifest changed")
    source_ramdisk = regular(source / SOURCE_INITRAMFS, "source initramfs")
    if digest(source_ramdisk) != SOURCE_INITRAMFS_SHA256:
        raise CandidateError("source initramfs changed")
    if candidate.name != CANDIDATE_DIR or candidate.is_symlink() or not candidate.is_dir():
        raise CandidateError("candidate directory identity changed")

    lines = regular(candidate / "SHA256SUMS", "candidate manifest").decode().splitlines()
    seen: set[str] = set()
    for line in lines:
        expected, marker, relative = line.partition("  ")
        path = PurePosixPath(relative)
        if (
            marker != "  " or len(expected) != 64 or path.is_absolute()
            or ".." in path.parts or path.as_posix() in seen
        ):
            raise CandidateError("candidate manifest is malformed")
        seen.add(path.as_posix())
        if digest(regular(candidate / path, f"candidate member {relative}")) != expected:
            raise CandidateError(f"candidate manifest mismatch: {relative}")
    expected_members = {
        "Image.gz", "System.map", "kernel.config", "source-build.json",
        "package-validation.txt", "container-validation.txt", "provenance.txt",
        CANDIDATE_DTB, CANDIDATE_INITRAMFS, CANDIDATE_BOOT, PADDED_BOOT,
    }
    if seen != expected_members:
        raise CandidateError("candidate manifest inventory changed")

    for name, expected, package_name in (
        ("Image.gz", IMAGE_GZ_SHA256, "Image.gz"),
        ("System.map", SYSTEM_MAP_SHA256, "System.map"),
        ("kernel.config", CONFIG_SHA256, "kernel.config"),
        (CANDIDATE_DTB, DTB_SHA256, PACKAGE_DTB),
    ):
        data = regular(candidate / name, name)
        if digest(data) != expected or data != regular(package / package_name, f"package {name}"):
            raise CandidateError(f"candidate {name} identity changed")
    if regular(candidate / CANDIDATE_INITRAMFS, "candidate initramfs") != source_ramdisk:
        raise CandidateError("candidate initramfs differs from source")
    if regular(candidate / "source-build.json", "build provenance") != regular(
        package / "provenance/build.json", "package build provenance"
    ):
        raise CandidateError("candidate build provenance changed")

    provenance = dict(
        line.split("=", 1)
        for line in regular(candidate / "provenance.txt", "candidate provenance").decode().splitlines()
    )
    expected_provenance = {
        "experiment": "2026-09-04-mt6797-thermal-base-dtb-control",
        "profile": "mt6797-thermal-stage-ledger",
        "repository_commit": BUILD_COMMIT,
        "initramfs_source": SOURCE_DIR,
        "candidate_initramfs_sha256": SOURCE_INITRAMFS_SHA256,
        "candidate_dtb_sha256": DTB_SHA256,
        "candidate_raw_sha256": RAW_SHA256,
        "candidate_raw_size": str(RAW_SIZE),
        "candidate_padded_sha256": PADDED_SHA256,
        "candidate_padded_size": str(BOOT2_SIZE),
        "appended_dtb_delta": "thermal-serviceability-to-base-only",
        "pwrap_reset_input": "1",
        "thermal_reset_input": "0",
        "thermal_controller": "disabled",
        "standalone_auxadc": "disabled",
        "thermal_zones": "0",
        "thermal_ledger_expected_owner": "no-exact-model-guard",
        "device_action": "none",
        "hardware_write": "none",
    }
    if provenance != expected_provenance:
        raise CandidateError("candidate provenance changed")

    serializer = repository / "experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
    analyzer = repository / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
    if digest(regular(serializer, "serializer")) != SERIALIZER_SHA256:
        raise CandidateError("serializer changed")
    if digest(regular(analyzer, "analyzer")) != ANALYZER_SHA256:
        raise CandidateError("analyzer changed")
    raw_path = candidate / CANDIDATE_BOOT
    subprocess.run(
        [
            os.fspath(analyzer), "--validate-lk",
            "--expected-image-gz", os.fspath(candidate / "Image.gz"),
            "--expected-ramdisk", os.fspath(candidate / CANDIDATE_INITRAMFS),
            "--expected-dtb", os.fspath(candidate / CANDIDATE_DTB),
            "--expected-name", "gemini-obs-L",
            "--expected-cmdline", "bootopt=64S3,32N2,64N2",
            os.fspath(raw_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    raw = regular(raw_path, "raw candidate")
    padded = regular(candidate / PADDED_BOOT, "padded candidate")
    if len(raw) != RAW_SIZE or digest(raw) != RAW_SHA256:
        raise CandidateError("selected raw candidate identity changed")
    if len(padded) != BOOT2_SIZE or digest(padded) != PADDED_SHA256:
        raise CandidateError("selected padded candidate identity changed")
    if padded[:len(raw)] != raw or any(padded[len(raw):]):
        raise CandidateError("exact zero-padding contract failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--initramfs-source", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    validate(
        args.repository.resolve(strict=True),
        args.package.resolve(strict=True),
        args.initramfs_source.resolve(strict=True),
        args.candidate.resolve(strict=True),
    )
    print("validation=mt6797-thermal-base-dtb-control-candidate")
    print(f"candidate_raw_sha256={RAW_SHA256}")
    print(f"candidate_raw_size={RAW_SIZE}")
    print(f"candidate_padded_sha256={PADDED_SHA256}")
    print(f"candidate_dtb_sha256={DTB_SHA256}")
    print("dt_delta=thermal-serviceability-to-base-only")
    print("thermal_controller=disabled")
    print("standalone_auxadc=disabled")
    print("thermal_zones=0")
    print("hardware_action=none")
    print("boot_candidate=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
