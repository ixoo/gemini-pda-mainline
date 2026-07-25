#!/usr/bin/env python3
"""Fail-closed validation of the exact exported Candidate W artifact."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import stat
import sys


BASELINE_BASENAME = "candidate-W-keyboard-wrrd-final-34c41fad"
MANIFEST_SHA256 = "257b17585c171e29ae3510fdab7602aa59e4da570aa906abb8b9e5b7e8da5851"
BOOT_SHA256 = "34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4"
DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
INITRAMFS_SHA256 = "3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6"
HELPER_SHA256 = "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
IMAGE_GZ_SHA256 = "e5da5fe6c1e4ae21e8005e0638abc938e37526ea872ede2c2163ee07397c8f21"
BOOT_SIZE = 6_866_944
DTB_SIZE = 26_259
INITRAMFS_SIZE = 1_307_029

BOOT_NAME = "gemini-keyboard-wrrd.boot.img"
DTB_NAME = "mt6797-gemini-pda-keyboard-wrrd.dtb"
INITRAMFS_NAME = "gemini-keyboard-wrrd-initramfs.img"
HELPER_NAME = "input-event-capture"

EXPECTED_INVENTORY = frozenset(
    {
        "analysis.txt",
        "boot-validation.txt",
        "controller-patch.txt",
        INITRAMFS_NAME,
        BOOT_NAME,
        "initramfs-build.txt",
        "initramfs-validation.txt",
        HELPER_NAME,
        "input-tree.sha256",
        DTB_NAME,
        "package-foundation.txt",
        "package-validation.txt",
        "provenance.txt",
        "serializer.txt",
        "source-build.json",
        "v-baseline-validation.txt",
    }
)
MANIFEST_LINE = re.compile(
    r"^([0-9a-f]{64})  \./([A-Za-z0-9][A-Za-z0-9._-]*)$"
)


def digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require_exact(
    path: pathlib.Path, expected_sha256: str, expected_size: int | None = None
) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required regular file is missing: {path.name}")
    if expected_size is not None and path.stat().st_size != expected_size:
        raise ValueError(f"unexpected size for {path.name}")
    if digest(path) != expected_sha256:
        raise ValueError(f"unexpected SHA-256 for {path.name}")


def parse_key_values(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        if "=" not in line:
            raise ValueError(f"malformed key/value line {number}: {path.name}")
        key, value = line.split("=", 1)
        if not key or key in values:
            raise ValueError(f"duplicate or empty key at line {number}: {path.name}")
        values[key] = value
    return values


def validate_manifest(baseline: pathlib.Path) -> None:
    manifest = baseline / "SHA256SUMS"
    require_exact(manifest, MANIFEST_SHA256)
    listed: dict[str, str] = {}
    for number, line in enumerate(
        manifest.read_text(encoding="ascii").splitlines(), start=1
    ):
        match = MANIFEST_LINE.fullmatch(line)
        if match is None:
            raise ValueError(f"malformed SHA256SUMS line {number}")
        checksum, relative = match.groups()
        if relative in listed:
            raise ValueError(f"duplicate SHA256SUMS entry: {relative}")
        listed[relative] = checksum
    if frozenset(listed) != EXPECTED_INVENTORY:
        raise ValueError("Candidate W SHA256SUMS inventory is not exact")

    children = list(baseline.iterdir())
    for child in children:
        mode = child.lstat().st_mode
        if child.is_symlink() or not stat.S_ISREG(mode):
            raise ValueError(f"unexpected non-regular artifact entry: {child.name}")
        expected_mode = 0o755 if child.name == HELPER_NAME else 0o600
        if stat.S_IMODE(mode) != expected_mode:
            raise ValueError(f"unexpected mode for Candidate W file: {child.name}")
    actual = {child.name for child in children if child.name != "SHA256SUMS"}
    if actual != EXPECTED_INVENTORY:
        raise ValueError("Candidate W on-disk inventory is not exact")
    for relative, expected in listed.items():
        if digest(baseline / relative) != expected:
            raise ValueError(f"SHA256SUMS verification failed: {relative}")


def validate_analysis(path: pathlib.Path) -> None:
    values = parse_key_values(path)
    expected = {
        "kernel_size": "5555889",
        "ramdisk_size": str(INITRAMFS_SIZE),
        "image_size": str(BOOT_SIZE),
        "image_sha256": BOOT_SHA256,
        "image_layout_exact": "yes",
        "payload_padding_zero": "yes",
        "page_size": "2048",
        "name": "gemini-obs-L",
        "cmdline": "bootopt=64S3,32N2,64N2",
        "canonical_sha1_id_matches": "yes",
        "appended_dtb_size": str(DTB_SIZE),
        "appended_dtb_sha256": DTB_SHA256,
        "expected_dtb_matches": "yes",
        "expected_image_gz_sha256": IMAGE_GZ_SHA256,
        "expected_image_gz_matches": "yes",
        "expected_ramdisk_sha256": INITRAMFS_SHA256,
        "expected_ramdisk_matches": "yes",
        "lk_validation": "passed",
        "lk_validation_failures": "none",
        "hardware_write": "none",
    }
    for key, expected_value in expected.items():
        if values.get(key) != expected_value:
            raise ValueError(f"Candidate W Android-v0 fact changed: {key}")
    if values.get("stored_sha1_id") != values.get("computed_sha1_id"):
        raise ValueError("Candidate W canonical Android ID is inconsistent")
    gates = {key: value for key, value in values.items() if key.startswith("gate_")}
    if len(gates) != 32 or set(gates.values()) != {"yes"}:
        raise ValueError("Candidate W Android-v0 gate set is not wholly passing")


def validate_provenance(path: pathlib.Path) -> None:
    values = parse_key_values(path)
    expected = {
        "experiment": "2026-07-19-keyboard-wrrd-diagnostic",
        "candidate_label": "W",
        "marker": "GEMINI_KEYBOARD_WRRD_20260719_W",
        "package": (
            "linux-7.1.3-gemini-observability-fbcon-rotation-"
            "keyboard-wrrd-4cd417ad-28a94091"
        ),
        "patchset_sha256": (
            "4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4"
        ),
        "image_gz_sha256": IMAGE_GZ_SHA256,
        "config_sha256": (
            "e143daa84127e2c04895c2576943dfb77ee10903c35f4d8cc9fe1dc90bf1bebb"
        ),
        "candidate_dtb_sha256": DTB_SHA256,
        "dtb_lineage": "byte-exact-candidate-v",
        "candidate_initramfs_sha256": INITRAMFS_SHA256,
        "candidate_sha256": BOOT_SHA256,
        "candidate_size": str(BOOT_SIZE),
        "simplefb": "exact-v-retained",
        "watchdog_irq": "exact-v-absent",
        "ramoops": "exact-v-retained",
        "i2c5_aw9523_matrix": "exact-v-retained",
        "storage_access": "none",
        "runtime_networking": "none",
        "hardware_write": "none",
        "flash": "none",
        "runtime_result": "not-tested",
    }
    for key, expected_value in expected.items():
        if values.get(key) != expected_value:
            raise ValueError(f"Candidate W provenance changed: {key}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if args.baseline.is_symlink():
            raise ValueError("selected Candidate W baseline must not be a symlink")
        baseline = args.baseline.resolve(strict=True)
        if baseline.name != BASELINE_BASENAME:
            raise ValueError("baseline basename is not exact Candidate W")
        if not baseline.is_dir():
            raise ValueError("baseline is not a regular directory")
        validate_manifest(baseline)
        require_exact(baseline / BOOT_NAME, BOOT_SHA256, BOOT_SIZE)
        require_exact(baseline / DTB_NAME, DTB_SHA256, DTB_SIZE)
        require_exact(
            baseline / INITRAMFS_NAME, INITRAMFS_SHA256, INITRAMFS_SIZE
        )
        require_exact(baseline / HELPER_NAME, HELPER_SHA256)
        if not (baseline / HELPER_NAME).stat().st_mode & stat.S_IXUSR:
            raise ValueError("Candidate W helper is not executable")
        validate_analysis(baseline / "analysis.txt")
        validate_provenance(baseline / "provenance.txt")
        print("validation=exact-candidate-w-baseline")
        print(f"baseline={BASELINE_BASENAME}")
        print(f"manifest_sha256={MANIFEST_SHA256}")
        print(f"boot_sha256={BOOT_SHA256}")
        print(f"dtb_sha256={DTB_SHA256}")
        print(f"initramfs_sha256={INITRAMFS_SHA256}")
        print(f"helper_sha256={HELPER_SHA256}")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
