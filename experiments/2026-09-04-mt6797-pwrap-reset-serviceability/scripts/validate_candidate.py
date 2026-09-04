#!/usr/bin/env python3
"""Independently validate the exact PWRAP-reset serviceability candidate."""

from __future__ import annotations

import argparse
import os
import stat
import struct
import subprocess
from pathlib import Path, PurePosixPath

from build_dtb import CONTROL_SHA256, TARGET_PATH, TARGET_PROPERTY, digest, properties
from validate_package import validate as validate_package


CONTROL_DIR = "candidate-AW-emmc-pmic-wrap-42c5c403"
CONTROL_MANIFEST_SHA256 = "22b2cc789c0ac39792617f693b8852ff1a8ad25d71e733cb6f8727716f34171b"
CONTROL_DTB = "mt6797-gemini-pda-emmc-pmic-development.dtb"
CONTROL_INITRAMFS = "gemini-emmc-pmic-development-initramfs.img"
CONTROL_INITRAMFS_SHA256 = "344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b"
CANDIDATE_DTB = "mt6797-gemini-pda-pwrap-reset-serviceability.dtb"
CANDIDATE_INITRAMFS = "gemini-pwrap-reset-serviceability-initramfs.img"
CANDIDATE_BOOT = "gemini-mt6797-pwrap-reset-serviceability.boot.img"
PADDED_BOOT = "boot2-padded.img"
BOOT2_SIZE = 16 * 1024 * 1024
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"


class CandidateError(ValueError):
    pass


def regular(path: Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise CandidateError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def validate(repository: Path, package: Path, control: Path, candidate: Path) -> None:
    validate_package(repository, package)
    if control.name != CONTROL_DIR or control.is_symlink() or not control.is_dir():
        raise CandidateError("control artifact identity changed")
    if digest(regular(control / "SHA256SUMS", "control manifest")) != CONTROL_MANIFEST_SHA256:
        raise CandidateError("control artifact manifest changed")
    control_dtb = regular(control / CONTROL_DTB, "control DT")
    if digest(control_dtb) != CONTROL_SHA256:
        raise CandidateError("control DT changed")
    control_initramfs = regular(control / CONTROL_INITRAMFS, "control initramfs")
    if digest(control_initramfs) != CONTROL_INITRAMFS_SHA256:
        raise CandidateError("control initramfs changed")
    if candidate.is_symlink() or not candidate.is_dir():
        raise CandidateError("candidate directory is missing or unsafe")
    manifest_lines = regular(candidate / "SHA256SUMS", "candidate manifest").decode().splitlines()
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
        if digest(regular(candidate / path, f"candidate member {relative}")) != expected:
            raise CandidateError(f"candidate manifest mismatch: {relative}")
    expected_members = {
        "Image.gz",
        "System.map",
        "kernel.config",
        "source-build.json",
        "package-validation.txt",
        "dtb-transform.txt",
        "container-validation.txt",
        "provenance.txt",
        CANDIDATE_DTB,
        CANDIDATE_INITRAMFS,
        CANDIDATE_BOOT,
        PADDED_BOOT,
    }
    if seen != expected_members:
        raise CandidateError("candidate manifest inventory changed")

    candidate_dtb = regular(candidate / CANDIDATE_DTB, "candidate DT")
    if len(candidate_dtb) != len(control_dtb):
        raise CandidateError("candidate DT size changed")
    control_props = properties(control_dtb)
    offset, control_value = control_props[(TARGET_PATH, TARGET_PROPERTY)]
    expected_dtb = bytearray(control_dtb)
    expected_dtb[offset + 4:offset + 8] = struct.pack(">I", 1)
    if candidate_dtb != bytes(expected_dtb):
        raise CandidateError("candidate DT has a change outside the one reset cell")
    if control_value != struct.pack(">II", 3, 64):
        raise CandidateError("control reset tuple changed")
    if properties(candidate_dtb)[(TARGET_PATH, TARGET_PROPERTY)][1] != struct.pack(">II", 3, 1):
        raise CandidateError("candidate reset tuple is not <3 1>")
    if regular(candidate / CANDIDATE_INITRAMFS, "candidate initramfs") != control_initramfs:
        raise CandidateError("candidate initramfs differs from control")
    if regular(candidate / "Image.gz", "candidate Image.gz") != regular(package / "Image.gz", "package Image.gz"):
        raise CandidateError("candidate kernel differs from package")

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
    if not 0 < len(raw) < BOOT2_SIZE:
        raise CandidateError("raw candidate does not fit boot2")
    if len(padded) != BOOT2_SIZE or padded[:len(raw)] != raw or any(padded[len(raw):]):
        raise CandidateError("exact boot2 padding contract failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--control", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve(strict=True)
    package = args.package.resolve(strict=True)
    control = args.control.resolve(strict=True)
    candidate = args.candidate.resolve(strict=True)
    validate(repository, package, control, candidate)
    raw = regular(candidate / CANDIDATE_BOOT, "raw candidate")
    padded = regular(candidate / PADDED_BOOT, "padded candidate")
    dtb = regular(candidate / CANDIDATE_DTB, "candidate DT")
    print("validation=mt6797-pwrap-reset-serviceability-candidate")
    print(f"candidate_raw_sha256={digest(raw)}")
    print(f"candidate_raw_size={len(raw)}")
    print(f"candidate_padded_sha256={digest(padded)}")
    print(f"candidate_dtb_sha256={digest(dtb)}")
    print("pwrap_reset=source-proven-set-clear")
    print("thermal_enable=none")
    print("hardware_action=none")
    print("boot_candidate=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
