#!/usr/bin/env python3
"""Validate the exact runtime-proven-DT thermal serviceability candidate."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
from pathlib import Path, PurePosixPath


ORIGIN = "https://github.com/ixoo/gemini-pda-mainline.git"
BUILD_COMMIT = "b66b03c722cd67584fb8fb15de493ebb084954b4"
PACKAGE_VALIDATOR_SHA256 = "0bec8097f36e2831a19239810d4faf2d1f74fe480f80e9391ecad703ccdf9191"
RUNTIME_PROOF_SHA256 = "aa72a61e0cf6076e175a08631adc788429c53bd73006f933614ca51541665c7b"
SOURCE_DIR = "candidate-mt6797-pwrap-reset-305230b1"
SOURCE_MANIFEST_SHA256 = "528f38ae3459149bc6f12242118b69d104590bd8902eef7d3969a1cd1b8d0f17"
SOURCE_DTB = "mt6797-gemini-pda-pwrap-reset-serviceability.dtb"
SOURCE_DTB_SHA256 = "e1e4eca289320533bad5c879e78055eaa86a295080b1154c13debe29ddd8ee4a"
SOURCE_INITRAMFS = "gemini-pwrap-reset-serviceability-initramfs.img"
SOURCE_INITRAMFS_SHA256 = "344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b"
CANDIDATE_DIR = "candidate-mt6797-thermal-serviceability-dt-repair-dd7a6ec4"
CONTROL_DTB = "mt6797-gemini-pda-runtime-proven-pwrap.dtb"
CANDIDATE_DTB = "mt6797-gemini-pda-thermal-serviceability.dtb"
CANDIDATE_DTB_SHA256 = "f131a06474ad5665dd957d7290f7b1240ca9603028046c93f4a5527ba3aa1366"
CANDIDATE_INITRAMFS = "gemini-mt6797-thermal-serviceability-dt-repair-initramfs.img"
CANDIDATE_BOOT = "gemini-mt6797-thermal-serviceability-dt-repair.boot.img"
PADDED_BOOT = "boot2-padded.img"
BOOT2_SIZE = 16 * 1024 * 1024
RAW_SIZE = 7_555_072
RAW_SHA256 = "dd7a6ec45389dc87b658c7eb22ee7022230cb9f435439875b981903770c21bf0"
PADDED_SHA256 = "ca3c25889b92673aa341fa97fc347c3469bc3b532d81045659a3afa1f563636a"
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


def validate(repository: Path, package: Path, source: Path, candidate: Path) -> None:
    if subprocess.check_output(
        ["git", "-C", os.fspath(repository), "remote", "get-url", "origin"], text=True
    ).strip() != ORIGIN:
        raise CandidateError("origin URL changed")
    package_validator = repository / "experiments/2026-09-04-mt6797-thermal-stage-ledger/scripts/validate_package.py"
    if digest(regular(package_validator, "package validator")) != PACKAGE_VALIDATOR_SHA256:
        raise CandidateError("package validator changed")
    subprocess.run(
        [os.fspath(package_validator), "--repository", os.fspath(repository), "--package", os.fspath(package)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    runtime_proof = repository / "experiments/2026-09-04-mt6797-pwrap-reset-serviceability/results/runtime-attempt-1-pwrap-serviceable-20260904.txt"
    proof = regular(runtime_proof, "runtime-proven DT evidence")
    if digest(proof) != RUNTIME_PROOF_SHA256:
        raise CandidateError("runtime-proven DT evidence changed")
    for token in (
        b"candidate_padded_sha256=5c7429b297c718f5af61367588975e292a8c239854ffd5ba527eb86da1e4a5a6",
        b"corrected_classification=pwrap-reset-serviceability-pass",
        b"decision=permit-thermal-reset-attachment-after-changed-ID-recovery",
    ):
        if token not in proof:
            raise CandidateError("runtime-proven DT evidence lost required claim")
    if source.name != SOURCE_DIR or source.is_symlink() or not source.is_dir():
        raise CandidateError("source candidate identity changed")
    if digest(regular(source / "SHA256SUMS", "source manifest")) != SOURCE_MANIFEST_SHA256:
        raise CandidateError("source candidate manifest changed")
    source_dtb = regular(source / SOURCE_DTB, "source DT")
    source_initramfs = regular(source / SOURCE_INITRAMFS, "source initramfs")
    if digest(source_dtb) != SOURCE_DTB_SHA256 or digest(source_initramfs) != SOURCE_INITRAMFS_SHA256:
        raise CandidateError("runtime-proven source member changed")
    if candidate.name != CANDIDATE_DIR or candidate.is_symlink() or not candidate.is_dir():
        raise CandidateError("candidate directory identity changed")

    lines = regular(candidate / "SHA256SUMS", "candidate manifest").decode().splitlines()
    seen: set[str] = set()
    for line in lines:
        expected, marker, relative = line.partition("  ")
        path = PurePosixPath(relative)
        if marker != "  " or len(expected) != 64 or path.is_absolute() or ".." in path.parts or path.as_posix() in seen:
            raise CandidateError("candidate manifest is malformed")
        seen.add(path.as_posix())
        if digest(regular(candidate / path, f"candidate member {relative}")) != expected:
            raise CandidateError(f"candidate manifest mismatch: {relative}")
    expected_members = {
        "Image.gz", "System.map", "kernel.config", "source-build.json",
        "package-validation.txt", "dt-validation.txt", "container-validation.txt",
        "provenance.txt", CONTROL_DTB, CANDIDATE_DTB, CANDIDATE_INITRAMFS,
        CANDIDATE_BOOT, PADDED_BOOT,
    }
    if seen != expected_members:
        raise CandidateError("candidate manifest inventory changed")

    for name, expected, package_name in (
        ("Image.gz", IMAGE_GZ_SHA256, "Image.gz"),
        ("System.map", SYSTEM_MAP_SHA256, "System.map"),
        ("kernel.config", CONFIG_SHA256, "kernel.config"),
    ):
        data = regular(candidate / name, name)
        if digest(data) != expected or data != regular(package / package_name, f"package {name}"):
            raise CandidateError(f"candidate {name} identity changed")
    if regular(candidate / CONTROL_DTB, "control DT") != source_dtb:
        raise CandidateError("candidate control DT differs from runtime-proven source")
    repaired_dtb = regular(candidate / CANDIDATE_DTB, "candidate DT")
    if digest(repaired_dtb) != CANDIDATE_DTB_SHA256:
        raise CandidateError("candidate DT identity changed")
    if regular(candidate / CANDIDATE_INITRAMFS, "candidate initramfs") != source_initramfs:
        raise CandidateError("candidate initramfs differs from runtime-proven source")
    if regular(candidate / "source-build.json", "build provenance") != regular(
        package / "provenance/build.json", "package build provenance"
    ):
        raise CandidateError("candidate build provenance changed")
    subprocess.run(
        [
            os.fspath(repository / "experiments/2026-09-04-mt6797-thermal-serviceability-dt-repair/scripts/validate_dtb.py"),
            "--repository", os.fspath(repository), "--base", os.fspath(candidate / CONTROL_DTB),
            "--output", os.fspath(candidate / CANDIDATE_DTB),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    provenance = dict(
        line.split("=", 1)
        for line in regular(candidate / "provenance.txt", "candidate provenance").decode().splitlines()
    )
    expected_provenance = {
        "experiment": "2026-09-04-mt6797-thermal-serviceability-dt-repair",
        "profile": "mt6797-thermal-stage-ledger",
        "repository_commit": BUILD_COMMIT,
        "runtime_proven_source": SOURCE_DIR,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "control_dtb_sha256": SOURCE_DTB_SHA256,
        "candidate_dtb_sha256": CANDIDATE_DTB_SHA256,
        "candidate_initramfs_sha256": SOURCE_INITRAMFS_SHA256,
        "candidate_raw_sha256": RAW_SHA256,
        "candidate_raw_size": str(RAW_SIZE),
        "candidate_padded_sha256": PADDED_SHA256,
        "candidate_padded_size": str(BOOT2_SIZE),
        "dt_delta": "model-thermal-phandle-reset-enable-one-zone-only",
        "usb_keyboard_pwrap_emmc_simplefb": "runtime-proven-preserved",
        "thermal_reset_input": "0",
        "thermal_zones": "1",
        "thermal_trips": "0",
        "cooling_maps": "0",
        "standalone_auxadc": "disabled",
        "thermal_ledger_record": "5",
        "thermal_ledger_attempt_id": "0x54484d4c00000001",
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
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    validate(
        args.repository.resolve(strict=True), args.package.resolve(strict=True),
        args.source.resolve(strict=True), args.candidate.resolve(strict=True),
    )
    print("validation=mt6797-thermal-serviceability-dt-repair-candidate")
    print(f"candidate_raw_sha256={RAW_SHA256}")
    print(f"candidate_raw_size={RAW_SIZE}")
    print(f"candidate_padded_sha256={PADDED_SHA256}")
    print(f"candidate_dtb_sha256={CANDIDATE_DTB_SHA256}")
    print("runtime_proven_serviceability_preserved=yes")
    print("thermal_controller=enabled-one-policy-free-zone")
    print("standalone_auxadc=disabled")
    print("hardware_action=none")
    print("boot_candidate=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
