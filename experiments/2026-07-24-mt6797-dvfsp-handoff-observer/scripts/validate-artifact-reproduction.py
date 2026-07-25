#!/usr/bin/env python3
"""Require two independently assembled Candidate AN artifacts to match."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import subprocess
import sys

sys.dont_write_bytecode = True

import candidate_an as an


EXECUTABLE_MEMBERS = {
    "console-keymap-verify",
    "console-unicode-mode",
    "input-event-capture",
}
EXPECTED_MEMBERS = {
    "Image.gz",
    "SHA256SUMS",
    "System.map",
    "analysis.txt",
    "boot-validation.txt",
    "console-keymap-verify",
    "console-unicode-mode",
    "dtb-validation.txt",
    an.BOOT_MEMBER,
    an.INITRAMFS_MEMBER,
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    an.DTB_MEMBER,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "source-build.json",
}
FIXED_PROVENANCE = {
    "experiment": an.EXPERIMENT,
    "candidate_label": an.CANDIDATE,
    "kernel_profile": an.PROFILE,
    "ah_raw_sha256": an.AH_RAW_SHA256,
    "ah_dtb_sha256": an.AH_DTB_SHA256,
    "candidate_initramfs_sha256": an.INITRAMFS_SHA256,
    "candidate_keymap_sha256": an.KEYMAP_SHA256,
    "patch_0094_sha256": an.PATCH_0094_SHA256,
    "patch_0095_sha256": an.PATCH_0095_SHA256,
    # Frozen reproduced-artifact label. It denotes AH's hardware contract,
    # not whole-artifact byte identity; AN necessarily has a different kernel.
    # README.md records the correction without changing the installed bytes.
    "functional_baseline": "byte-exact-hardware-passed-candidate-ah",
    "final_dtb_baseline": "exact-candidate-ah-final-dtb",
    "final_dtb_delta": "one-read-only-dvfsp-observer-node",
    "initramfs_keyboard_console_usb_reboot": "byte-exact-candidate-ah",
    "observer_snapshots": "3",
    "observer_mmio": "read-only",
    "i2c6": "disabled",
    "da9214_node": "absent",
    "a72_power_node": "absent",
    "maxcpus": "8",
    "a72_observer_initcall": "blacklisted",
    "dvfsp_observer_initcall": "enabled",
    "cpu8_cpu9_request": "none",
    "regulator_operation": "none",
    "storage_access": "none",
    "watchdog_userspace": "none",
    "automatic_reboot": "none",
    "artifact_builder_device_access": "none",
    "flash": "none",
    "runtime_result": "not-tested",
}
DYNAMIC_PROVENANCE = {
    "candidate_sha256",
    "candidate_size",
    "candidate_image_gz_sha256",
    "candidate_system_map_sha256",
    "candidate_dtb_sha256",
    "candidate_config_sha256",
    "candidate_source_build_sha256",
}


def resolve_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe {label} directory")
    return path.resolve(strict=True)


def inventory(root: pathlib.Path) -> dict[str, tuple[int, str, int]]:
    output: dict[str, tuple[int, str, int]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise ValueError(f"unexpected non-regular artifact member: {relative}")
        output[relative] = (
            stat.S_IMODE(info.st_mode),
            an.digest_path(path),
            info.st_size,
        )
    return output


def parse_manifest(
    root: pathlib.Path, members: dict[str, tuple[int, str, int]]
) -> None:
    seen: set[str] = set()
    for line in (root / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("Candidate AN artifact manifest is malformed")
        member = fields[1].removeprefix("*").removeprefix("./")
        if member in seen or member == "SHA256SUMS" or member not in members:
            raise ValueError("Candidate AN manifest member is unsafe or duplicated")
        if fields[0] != members[member][1]:
            raise ValueError(f"Candidate AN artifact checksum differs: {member}")
        seen.add(member)
    if seen != EXPECTED_MEMBERS - {"SHA256SUMS"}:
        raise ValueError("Candidate AN manifest inventory changed")


def parse_provenance(path: pathlib.Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in output:
            raise ValueError("Candidate AN provenance is malformed or duplicated")
        output[key] = value
    return output


def padded_digest(path: pathlib.Path, raw_size: int) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    remaining = an.BOOT2_SIZE - raw_size
    zeros = b"\0" * (1024 * 1024)
    while remaining:
        block = zeros[: min(remaining, len(zeros))]
        hasher.update(block)
        remaining -= len(block)
    return hasher.hexdigest()


def run_boot_validator(
    root: pathlib.Path, ah_artifact: pathlib.Path, script_dir: pathlib.Path
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            os.fspath(script_dir / "validate-boot.py"),
            "--candidate",
            os.fspath(root / an.BOOT_MEMBER),
            "--image-gz",
            os.fspath(root / "Image.gz"),
            "--system-map",
            os.fspath(root / "System.map"),
            "--kernel-config",
            os.fspath(root / "kernel.config"),
            "--dtb",
            os.fspath(root / an.DTB_MEMBER),
            "--ah-dtb",
            os.fspath(ah_artifact / an.AH_DTB_MEMBER),
            "--initramfs",
            os.fspath(root / an.INITRAMFS_MEMBER),
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError("Candidate AN boot validator rejected artifact: " + detail)


def validate_tree(
    root: pathlib.Path,
    members: dict[str, tuple[int, str, int]],
    ah_artifact: pathlib.Path,
    script_dir: pathlib.Path,
) -> None:
    if set(members) != EXPECTED_MEMBERS:
        raise ValueError("Candidate AN artifact inventory changed")
    for member, (mode, _, _) in members.items():
        expected = 0o755 if member in EXECUTABLE_MEMBERS else 0o600
        if mode != expected:
            raise ValueError(f"Candidate AN artifact mode changed: {member}")
    parse_manifest(root, members)

    fixed = {
        an.DTB_MEMBER: an.FINAL_DTB_SHA256,
        an.INITRAMFS_MEMBER: an.INITRAMFS_SHA256,
        "gemini-us.bkeymap": an.KEYMAP_SHA256,
    }
    for member, wanted in fixed.items():
        if members[member][1] != wanted:
            raise ValueError(f"Candidate AN fixed payload changed: {member}")
    for helper in EXECUTABLE_MEMBERS:
        if members[helper][1] != an.digest_path(ah_artifact / helper):
            raise ValueError(f"Candidate AN Candidate AH helper changed: {helper}")

    boot_hash = members[an.BOOT_MEMBER][1]
    if root.name != an.ARTIFACT_PREFIX + boot_hash[:8]:
        raise ValueError("Candidate AN artifact basename disagrees with boot hash")
    provenance = parse_provenance(root / "provenance.txt")
    if set(provenance) != set(FIXED_PROVENANCE) | DYNAMIC_PROVENANCE:
        raise ValueError("Candidate AN provenance inventory changed")
    for key, wanted in FIXED_PROVENANCE.items():
        if provenance[key] != wanted:
            raise ValueError(f"Candidate AN provenance changed: {key}")
    dynamic = {
        "candidate_sha256": boot_hash,
        "candidate_size": str(members[an.BOOT_MEMBER][2]),
        "candidate_image_gz_sha256": members["Image.gz"][1],
        "candidate_system_map_sha256": members["System.map"][1],
        "candidate_dtb_sha256": members[an.DTB_MEMBER][1],
        "candidate_config_sha256": members["kernel.config"][1],
        "candidate_source_build_sha256": members["source-build.json"][1],
    }
    for key, wanted in dynamic.items():
        if provenance[key] != wanted:
            raise ValueError(f"Candidate AN dynamic provenance changed: {key}")
    run_boot_validator(root, ah_artifact, script_dir)


def validate_calibration(
    members: dict[str, tuple[int, str, int]], root: pathlib.Path
) -> tuple[str, str]:
    boot_hash = members[an.BOOT_MEMBER][1]
    boot_size = members[an.BOOT_MEMBER][2]
    padded = padded_digest(root / an.BOOT_MEMBER, boot_size)
    state = an.artifact_pin_state()
    if state == "source-pinned":
        wanted = {
            "Image.gz": (an.IMAGE_GZ_SHA256, members["Image.gz"][1]),
            "System.map": (an.SYSTEM_MAP_SHA256, members["System.map"][1]),
            "kernel.config": (an.CONFIG_SHA256, members["kernel.config"][1]),
            "source-build.json": (
                an.SOURCE_BUILD_SHA256,
                members["source-build.json"][1],
            ),
            "raw": (an.RAW_SHA256, boot_hash),
            "raw size": (int(an.RAW_SIZE), boot_size),
            "artifact manifest": (
                an.ARTIFACT_MANIFEST_SHA256,
                members["SHA256SUMS"][1],
            ),
            "padded": (an.PADDED_SHA256, padded),
        }
        for label, (expected, actual) in wanted.items():
            if expected != actual:
                raise ValueError(f"source-pinned Candidate AN {label} differs")
    return state, padded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", required=True, type=pathlib.Path)
    parser.add_argument("--second", required=True, type=pathlib.Path)
    parser.add_argument("--ah-artifact", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        first_root = resolve_directory(args.first, "first AN artifact")
        second_root = resolve_directory(args.second, "second AN artifact")
        ah_artifact = resolve_directory(args.ah_artifact, "Candidate AH artifact")
        if first_root == second_root or first_root.samefile(second_root):
            raise ValueError("reproduction requires two independent AN trees")
        if ah_artifact.name != an.AH_ARTIFACT_DIR:
            raise ValueError("Candidate AH artifact basename changed")
        if an.digest_path(ah_artifact / "SHA256SUMS") != an.AH_MANIFEST_SHA256:
            raise ValueError("Candidate AH artifact manifest changed")

        script_dir = pathlib.Path(__file__).resolve().parent
        first = inventory(first_root)
        second = inventory(second_root)
        validate_tree(first_root, first, ah_artifact, script_dir)
        validate_tree(second_root, second, ah_artifact, script_dir)
        if first != second:
            names = sorted(set(first) | set(second))
            changed = [name for name in names if first.get(name) != second.get(name)]
            raise ValueError(
                "Candidate AN artifacts differ: " + ",".join(changed[:3])
            )
        calibration, padded = validate_calibration(first, first_root)

        print("validation=candidate-an-artifact-reproduction")
        print(f"first_artifact={first_root}")
        print(f"second_artifact={second_root}")
        print(f"members={len(first)}")
        print(f"boot_sha256={first[an.BOOT_MEMBER][1]}")
        print(f"boot_size={first[an.BOOT_MEMBER][2]}")
        print(f"image_gz_sha256={first['Image.gz'][1]}")
        print(f"system_map_sha256={first['System.map'][1]}")
        print(f"config_sha256={first['kernel.config'][1]}")
        print(f"source_build_sha256={first['source-build.json'][1]}")
        print(f"dtb_sha256={first[an.DTB_MEMBER][1]}")
        print(f"manifest_sha256={first['SHA256SUMS'][1]}")
        print(f"padded_sha256={padded}")
        print(f"calibration={calibration}")
        print("bytes_identical=yes")
        print("modes_identical=yes")
        print("device_access=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
