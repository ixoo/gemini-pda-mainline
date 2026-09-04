#!/usr/bin/env python3
"""Validate the exact live-model-repaired thermal boot candidate."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
from pathlib import Path, PurePosixPath


ORIGIN = "https://github.com/ixoo/gemini-pda-mainline.git"
BUILD_COMMIT = "08fd54667c620649938f2b500779e59f4d4b8762"
PACKAGE_VALIDATOR_SHA256 = "5cdd5dc86d086c5d48610aa1bcfc7c4f4af73336136200689be71da59a889b77"
RUNTIME_EVIDENCE_SHA256 = "012fa2ec367424da240359a34b82f3285f289eb91b07499e3b7d213440bb1a0c"
SOURCE_DIR = "candidate-mt6797-thermal-serviceability-dt-repair-dd7a6ec4"
SOURCE_MANIFEST_SHA256 = "b89a4d603a55e7f923d70c5dc2699039536244255f6ea7f40b9747fccac2d3d7"
SOURCE_DTB = "mt6797-gemini-pda-thermal-serviceability.dtb"
SOURCE_DTB_SHA256 = "f131a06474ad5665dd957d7290f7b1240ca9603028046c93f4a5527ba3aa1366"
SOURCE_INITRAMFS = "gemini-mt6797-thermal-serviceability-dt-repair-initramfs.img"
SOURCE_INITRAMFS_SHA256 = "344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b"
CANDIDATE_DIR = "candidate-mt6797-thermal-ledger-live-model-repair-40361fae"
CANDIDATE_DTB = "mt6797-gemini-pda-thermal-ledger-live-model-repair.dtb"
CANDIDATE_INITRAMFS = "gemini-mt6797-thermal-ledger-live-model-repair-initramfs.img"
CANDIDATE_BOOT = "gemini-mt6797-thermal-ledger-live-model-repair.boot.img"
PADDED_BOOT = "boot2-padded.img"
BOOT2_SIZE = 16 * 1024 * 1024
RAW_SIZE = 7_555_072
RAW_SHA256 = "40361fae05a603b5f05c98ef88950a404ba95c646b7ded4f773e1088febca27d"
PADDED_SHA256 = "93a78b490a9ffbf32eb60c5c875f508fd05b43b726220b3ccdbe9277792752a4"
IMAGE_GZ_SHA256 = "71104199d99e2be3ac6b42867763d5e74ba8474019f2f47d33c1fc8ac44f8b12"
SYSTEM_MAP_SHA256 = "041d6efae789aadf6a2dc1aaaa980e8ce76f465273dc7d160630d9a73d094a0d"
CONFIG_SHA256 = "f0a135b24055229447d56ae6bda16e1ada683ebe4612af3ba0b96ec7febd375a"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"


class CandidateError(ValueError):
    """Raised when the exact candidate contract is not met."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise CandidateError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def validate_manifest(directory: Path) -> set[str]:
    lines = regular(directory / "SHA256SUMS", "manifest").decode().splitlines()
    seen: set[str] = set()
    for line in lines:
        expected, marker, relative = line.partition("  ")
        path = PurePosixPath(relative)
        normalized = path.as_posix()
        if (marker != "  " or len(expected) != 64 or path.is_absolute()
                or ".." in path.parts or normalized in seen):
            raise CandidateError("manifest is malformed")
        seen.add(normalized)
        if digest(regular(directory / path, f"member {relative}")) != expected:
            raise CandidateError(f"manifest mismatch: {relative}")
    return seen


def validate(repository: Path, package: Path, source: Path, candidate: Path) -> None:
    if subprocess.check_output(
        ["git", "-C", os.fspath(repository), "remote", "get-url", "origin"], text=True
    ).strip() != ORIGIN:
        raise CandidateError("origin URL changed")
    package_validator = repository / "experiments/2026-09-04-mt6797-thermal-ledger-live-model-repair/scripts/validate_package.py"
    if digest(regular(package_validator, "package validator")) != PACKAGE_VALIDATOR_SHA256:
        raise CandidateError("package validator changed")
    subprocess.run(
        [os.fspath(package_validator), "--repository", os.fspath(repository),
         "--package", os.fspath(package)], check=True, stdout=subprocess.DEVNULL,
    )
    runtime_evidence = repository / "experiments/2026-09-04-mt6797-thermal-serviceability-dt-repair/results/runtime-attempt-1-live-ledger-model-rejection-20260904.txt"
    evidence = regular(runtime_evidence, "runtime source evidence")
    if digest(evidence) != RUNTIME_EVIDENCE_SHA256:
        raise CandidateError("runtime source evidence changed")
    for token in (
        b"candidate_full_boot2_sha256=ca3c25889b92673aa341fa97fc347c3469bc3b532d81045659a3afa1f563636a",
        b"live_dt_model=MT6797X",
        b"mainline_netcat=present-one-read-only-frame",
        b"decision=repair only the diagnostic ledger live-model predicate",
    ):
        if token not in evidence:
            raise CandidateError("runtime source evidence lost a required claim")

    if source.name != SOURCE_DIR or source.is_symlink() or not source.is_dir():
        raise CandidateError("source candidate identity changed")
    if digest(regular(source / "SHA256SUMS", "source manifest")) != SOURCE_MANIFEST_SHA256:
        raise CandidateError("source candidate manifest changed")
    validate_manifest(source)
    source_dtb = regular(source / SOURCE_DTB, "source DT")
    source_initramfs = regular(source / SOURCE_INITRAMFS, "source initramfs")
    if digest(source_dtb) != SOURCE_DTB_SHA256:
        raise CandidateError("runtime-proven source DT changed")
    if digest(source_initramfs) != SOURCE_INITRAMFS_SHA256:
        raise CandidateError("source initramfs changed")
    if candidate.name != CANDIDATE_DIR or candidate.is_symlink() or not candidate.is_dir():
        raise CandidateError("candidate directory identity changed")

    seen = validate_manifest(candidate)
    expected_members = {
        "Image.gz", "System.map", "kernel.config", "source-build.json",
        "package-validation.txt", "container-validation.txt", "provenance.txt",
        CANDIDATE_DTB, CANDIDATE_INITRAMFS, CANDIDATE_BOOT, PADDED_BOOT,
    }
    if seen != expected_members:
        raise CandidateError("candidate manifest inventory changed")
    for name, expected in (
        ("Image.gz", IMAGE_GZ_SHA256),
        ("System.map", SYSTEM_MAP_SHA256),
        ("kernel.config", CONFIG_SHA256),
    ):
        data = regular(candidate / name, name)
        if digest(data) != expected or data != regular(package / name, f"package {name}"):
            raise CandidateError(f"candidate {name} identity changed")
    if regular(candidate / CANDIDATE_DTB, "candidate DT") != source_dtb:
        raise CandidateError("candidate DT differs from runtime-proven source")
    if regular(candidate / CANDIDATE_INITRAMFS, "candidate initramfs") != source_initramfs:
        raise CandidateError("candidate initramfs differs from runtime-proven source")
    if regular(candidate / "source-build.json", "candidate build provenance") != regular(
        package / "provenance/build.json", "package build provenance"
    ):
        raise CandidateError("candidate build provenance changed")

    provenance = dict(
        line.split("=", 1)
        for line in regular(candidate / "provenance.txt", "candidate provenance").decode().splitlines()
    )
    expected_provenance = {
        "experiment": "2026-09-04-mt6797-thermal-ledger-live-model-repair",
        "profile": "mt6797-thermal-stage-ledger",
        "repository_commit": BUILD_COMMIT,
        "runtime_proven_source": SOURCE_DIR,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "source_runtime_evidence_sha256": RUNTIME_EVIDENCE_SHA256,
        "candidate_dtb_sha256": SOURCE_DTB_SHA256,
        "candidate_initramfs_sha256": SOURCE_INITRAMFS_SHA256,
        "candidate_raw_sha256": RAW_SHA256,
        "candidate_raw_size": str(RAW_SIZE),
        "candidate_padded_sha256": PADDED_SHA256,
        "candidate_padded_size": str(BOOT2_SIZE),
        "dt_delta": "none-from-runtime-proven-candidate",
        "kernel_delta": "thermal-ledger-live-model-guard-only",
        "usb_keyboard_pwrap_emmc_simplefb": "runtime-proven-preserved",
        "thermal_reset_input": "0",
        "thermal_zones": "1",
        "thermal_trips": "0",
        "cooling_maps": "0",
        "cpu8_cpu9": "offline-no-request",
        "load": "none",
        "cpufreq_opp": "disabled",
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
        [os.fspath(analyzer), "--validate-lk", "--expected-image-gz",
         os.fspath(candidate / "Image.gz"), "--expected-ramdisk",
         os.fspath(candidate / CANDIDATE_INITRAMFS), "--expected-dtb",
         os.fspath(candidate / CANDIDATE_DTB), "--expected-name", "gemini-obs-L",
         "--expected-cmdline", "bootopt=64S3,32N2,64N2", os.fspath(raw_path)],
        check=True, stdout=subprocess.DEVNULL,
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
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    validate(
        args.repository.resolve(strict=True), args.package.resolve(strict=True),
        args.source.resolve(strict=True), args.candidate.resolve(strict=True),
    )
    print("validation=mt6797-thermal-ledger-live-model-repair-candidate")
    print(f"candidate_raw_sha256={RAW_SHA256}")
    print(f"candidate_raw_size={RAW_SIZE}")
    print(f"candidate_padded_sha256={PADDED_SHA256}")
    print(f"candidate_dtb_sha256={SOURCE_DTB_SHA256}")
    print("runtime_proven_serviceability_preserved=yes")
    print("kernel_delta=thermal-ledger-live-model-guard-only")
    print("hardware_action=none")
    print("boot_candidate=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
