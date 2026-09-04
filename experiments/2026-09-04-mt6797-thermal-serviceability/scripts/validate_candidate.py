#!/usr/bin/env python3
"""Independently validate the exact thermal-serviceability boot candidate."""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
from pathlib import Path, PurePosixPath

from validate_package import (
    SERVICE_DTB_SHA256,
    digest,
    regular,
    validate as validate_package,
    validate_dtbs,
)


SOURCE_DIR = "candidate-mt6797-pwrap-reset-305230b1"
SOURCE_MANIFEST_SHA256 = "528f38ae3459149bc6f12242118b69d104590bd8902eef7d3969a1cd1b8d0f17"
SOURCE_INITRAMFS = "gemini-pwrap-reset-serviceability-initramfs.img"
SOURCE_INITRAMFS_SHA256 = "344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b"
PACKAGE_DTB = "dtbs/mediatek/mt6797-gemini-pda-thermal-serviceability.dtb"
CANDIDATE_DTB = "mt6797-gemini-pda-thermal-serviceability.dtb"
CANDIDATE_INITRAMFS = "gemini-mt6797-thermal-serviceability-initramfs.img"
CANDIDATE_BOOT = "gemini-mt6797-thermal-serviceability.boot.img"
PADDED_BOOT = "boot2-padded.img"
BOOT2_SIZE = 16 * 1024 * 1024
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"


class CandidateError(ValueError):
    pass


def local_regular(path: Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise CandidateError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def validate(
    repository: Path,
    package: Path,
    initramfs_source: Path,
    candidate: Path,
) -> None:
    validate_package(repository, package)
    if (
        initramfs_source.name != SOURCE_DIR
        or initramfs_source.is_symlink()
        or not initramfs_source.is_dir()
    ):
        raise CandidateError("initramfs source identity changed")
    if digest(local_regular(initramfs_source / "SHA256SUMS", "source manifest")) != SOURCE_MANIFEST_SHA256:
        raise CandidateError("initramfs source manifest changed")
    source_initramfs = local_regular(initramfs_source / SOURCE_INITRAMFS, "source initramfs")
    if digest(source_initramfs) != SOURCE_INITRAMFS_SHA256:
        raise CandidateError("source initramfs changed")
    if candidate.is_symlink() or not candidate.is_dir():
        raise CandidateError("candidate directory is missing or unsafe")

    manifest_lines = local_regular(candidate / "SHA256SUMS", "candidate manifest").decode().splitlines()
    seen: set[str] = set()
    for line in manifest_lines:
        expected, marker, relative = line.partition("  ")
        path = PurePosixPath(relative)
        normalized = path.as_posix()
        if (
            marker != "  "
            or len(expected) != 64
            or path.is_absolute()
            or ".." in path.parts
            or normalized in seen
        ):
            raise CandidateError("candidate manifest is malformed")
        seen.add(normalized)
        if digest(local_regular(candidate / path, f"candidate member {relative}")) != expected:
            raise CandidateError(f"candidate manifest mismatch: {relative}")
    expected_members = {
        "Image.gz",
        "System.map",
        "kernel.config",
        "source-build.json",
        "package-validation.txt",
        "container-validation.txt",
        "provenance.txt",
        CANDIDATE_DTB,
        CANDIDATE_INITRAMFS,
        CANDIDATE_BOOT,
        PADDED_BOOT,
    }
    if seen != expected_members:
        raise CandidateError("candidate manifest inventory changed")

    candidate_dtb = local_regular(candidate / CANDIDATE_DTB, "candidate DT")
    if digest(candidate_dtb) != SERVICE_DTB_SHA256:
        raise CandidateError("candidate DT identity changed")
    if candidate_dtb != local_regular(package / PACKAGE_DTB, "package DT"):
        raise CandidateError("candidate DT differs from exact package DT")
    validate_dtbs(package)
    if local_regular(candidate / CANDIDATE_INITRAMFS, "candidate initramfs") != source_initramfs:
        raise CandidateError("candidate initramfs differs from its pinned source")
    if local_regular(candidate / "Image.gz", "candidate Image.gz") != regular(package / "Image.gz", "package Image.gz"):
        raise CandidateError("candidate kernel differs from package")
    if local_regular(candidate / "System.map", "candidate System.map") != regular(package / "System.map", "package System.map"):
        raise CandidateError("candidate System.map differs from package")
    if local_regular(candidate / "kernel.config", "candidate config") != regular(package / "kernel.config", "package config"):
        raise CandidateError("candidate config differs from package")
    if local_regular(candidate / "source-build.json", "candidate build provenance") != regular(package / "provenance/build.json", "package build provenance"):
        raise CandidateError("candidate build provenance differs from package")

    provenance = dict(
        line.split("=", 1)
        for line in local_regular(candidate / "provenance.txt", "candidate provenance").decode().splitlines()
    )
    for key, expected in (
        ("experiment", "2026-09-04-mt6797-thermal-serviceability"),
        ("profile", "mt6797-thermal-serviceability"),
        ("initramfs_source", SOURCE_DIR),
        ("initramfs_source_manifest_sha256", SOURCE_MANIFEST_SHA256),
        ("candidate_initramfs_sha256", SOURCE_INITRAMFS_SHA256),
        ("candidate_dtb_sha256", SERVICE_DTB_SHA256),
        ("candidate_padded_size", str(BOOT2_SIZE)),
        ("pwrap_reset_input", "1"),
        ("thermal_reset_input", "0"),
        ("thermal_zones", "1"),
        ("thermal_trips", "0"),
        ("cooling_maps", "0"),
        ("standalone_auxadc", "disabled"),
        ("device_action", "none"),
        ("hardware_write", "none"),
    ):
        if provenance.get(key) != expected:
            raise CandidateError(f"candidate provenance mismatch: {key}")

    serializer = repository / "experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
    analyzer = repository / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
    if digest(local_regular(serializer, "serializer")) != SERIALIZER_SHA256:
        raise CandidateError("serializer changed")
    if digest(local_regular(analyzer, "analyzer")) != ANALYZER_SHA256:
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
    raw = local_regular(raw_path, "raw candidate")
    padded = local_regular(candidate / PADDED_BOOT, "padded candidate")
    if provenance.get("candidate_raw_sha256") != digest(raw):
        raise CandidateError("raw candidate provenance mismatch")
    if provenance.get("candidate_raw_size") != str(len(raw)):
        raise CandidateError("raw candidate size provenance mismatch")
    if provenance.get("candidate_padded_sha256") != digest(padded):
        raise CandidateError("padded candidate provenance mismatch")
    if not 0 < len(raw) < BOOT2_SIZE:
        raise CandidateError("raw candidate does not fit boot2")
    if len(padded) != BOOT2_SIZE or padded[:len(raw)] != raw or any(padded[len(raw):]):
        raise CandidateError("exact boot2 padding contract failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--initramfs-source", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve(strict=True)
    package = args.package.resolve(strict=True)
    initramfs_source = args.initramfs_source.resolve(strict=True)
    candidate = args.candidate.resolve(strict=True)
    validate(repository, package, initramfs_source, candidate)
    raw = local_regular(candidate / CANDIDATE_BOOT, "raw candidate")
    padded = local_regular(candidate / PADDED_BOOT, "padded candidate")
    dtb = local_regular(candidate / CANDIDATE_DTB, "candidate DT")
    print("validation=mt6797-thermal-serviceability-candidate")
    print(f"candidate_raw_sha256={digest(raw)}")
    print(f"candidate_raw_size={len(raw)}")
    print(f"candidate_padded_sha256={digest(padded)}")
    print(f"candidate_dtb_sha256={digest(dtb)}")
    print("pwrap_reset_input=1")
    print("thermal_reset_input=0")
    print("thermal_zones=1")
    print("thermal_trips=0")
    print("cooling_maps=0")
    print("standalone_auxadc=disabled")
    print("hardware_action=none")
    print("boot_candidate=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
