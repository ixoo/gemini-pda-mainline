#!/usr/bin/env python3
"""Require two independently assembled Candidate AL artifacts to match."""

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

import candidate_al as al


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
    al.BOOT_MEMBER,
    al.INITRAMFS_MEMBER,
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    "lineage-validation.txt",
    al.DTB_MEMBER,
    "provenance.txt",
    "serializer.txt",
    "source-build.json",
}
FIXED_PROVENANCE = {
    "experiment": al.EXPERIMENT,
    "candidate_label": al.CANDIDATE,
    "ah_raw_sha256": al.AH_RAW_SHA256,
    "ah_dtb_sha256": al.AH_DTB_SHA256,
    "image_gz_sha256": al.IMAGE_GZ_SHA256,
    "system_map_sha256": al.SYSTEM_MAP_SHA256,
    "config_sha256": al.CONFIG_SHA256,
    "initramfs_sha256": al.INITRAMFS_SHA256,
    "patch_0089_sha256": al.PATCH_0089_SHA256,
    "ak_installed_predecessor_sha256": al.AK_PADDED_SHA256,
    "functional_baseline": "byte-exact-hardware-passed-candidate-ah",
    "ak_functional_payload_reused": "no",
    "kernel_config_system_map_initramfs": "byte-exact-candidate-ah",
    "final_dtb_baseline": "exact-candidate-ah-final-dtb",
    "final_dtb_delta": "patch-0089-i2c6-da9214-only",
    "maxcpus": "8",
    "observer_initcall": "blacklisted",
    "a72_power_node": "absent",
    "cpu8_cpu9_request": "none",
    "storage_access": "none",
    "watchdog_userspace": "none",
    "artifact_builder_device_access": "none",
    "flash": "none",
    "runtime_result": "not-tested",
}
DYNAMIC_PROVENANCE = {
    "candidate_sha256",
    "candidate_size",
    "candidate_dtb_sha256",
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
            al.digest_path(path),
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
            raise ValueError("Candidate AL artifact manifest is malformed")
        member = fields[1].removeprefix("*").removeprefix("./")
        if member in seen or member == "SHA256SUMS" or member not in members:
            raise ValueError("Candidate AL manifest member is unsafe or duplicated")
        if fields[0] != members[member][1]:
            raise ValueError(f"Candidate AL artifact checksum differs: {member}")
        seen.add(member)
    if seen != EXPECTED_MEMBERS - {"SHA256SUMS"}:
        raise ValueError("Candidate AL manifest inventory changed")


def parse_provenance(path: pathlib.Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in output:
            raise ValueError("Candidate AL provenance is malformed or duplicated")
        output[key] = value
    return output


def padded_digest(path: pathlib.Path, raw_size: int) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    remaining = al.BOOT2_SIZE - raw_size
    zeros = b"\0" * (1024 * 1024)
    while remaining:
        block = zeros[: min(remaining, len(zeros))]
        hasher.update(block)
        remaining -= len(block)
    return hasher.hexdigest()


def run_validator(command: list[str]) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"validator rejected artifact: {detail}")


def validate_tree(
    root: pathlib.Path,
    members: dict[str, tuple[int, str, int]],
    ah_artifact: pathlib.Path,
) -> None:
    if set(members) != EXPECTED_MEMBERS:
        raise ValueError("Candidate AL artifact inventory changed")
    for member, (mode, _, _) in members.items():
        expected = 0o755 if member in EXECUTABLE_MEMBERS else 0o600
        if mode != expected:
            raise ValueError(f"Candidate AL artifact mode changed: {member}")
    parse_manifest(root, members)
    fixed = {
        "Image.gz": al.IMAGE_GZ_SHA256,
        "System.map": al.SYSTEM_MAP_SHA256,
        "kernel.config": al.CONFIG_SHA256,
        "source-build.json": al.SOURCE_BUILD_SHA256,
        al.INITRAMFS_MEMBER: al.INITRAMFS_SHA256,
        "gemini-us.bkeymap": al.KEYMAP_SHA256,
    }
    for member, wanted in fixed.items():
        if members[member][1] != wanted:
            raise ValueError(f"Candidate AL exact AH payload changed: {member}")
    for helper in EXECUTABLE_MEMBERS:
        if members[helper][1] != al.digest_path(ah_artifact / helper):
            raise ValueError(f"Candidate AL AH helper changed: {helper}")

    boot_hash = members[al.BOOT_MEMBER][1]
    expected_name = al.ARTIFACT_PREFIX + boot_hash[:8]
    if root.name != expected_name:
        raise ValueError("Candidate AL artifact basename does not match boot hash")
    provenance = parse_provenance(root / "provenance.txt")
    if set(provenance) != set(FIXED_PROVENANCE) | DYNAMIC_PROVENANCE:
        raise ValueError("Candidate AL provenance inventory changed")
    for key, wanted in FIXED_PROVENANCE.items():
        if provenance[key] != wanted:
            raise ValueError(f"Candidate AL provenance changed: {key}")
    if provenance["candidate_sha256"] != boot_hash:
        raise ValueError("Candidate AL provenance boot checksum changed")
    if provenance["candidate_size"] != str(members[al.BOOT_MEMBER][2]):
        raise ValueError("Candidate AL provenance boot size changed")
    if provenance["candidate_dtb_sha256"] != members[al.DTB_MEMBER][1]:
        raise ValueError("Candidate AL provenance DT checksum changed")


def calibration_state(
    raw_sha256: str,
    raw_size: int,
    dtb_sha256: str,
    manifest_sha256: str,
    padded_sha256: str,
) -> str:
    values = (
        al.FINAL_DTB_SHA256,
        al.RAW_SHA256,
        al.RAW_SIZE,
        al.ARTIFACT_MANIFEST_SHA256,
        al.PADDED_SHA256,
    )
    unresolved = [value.startswith("TO_PIN_") for value in values]
    if all(unresolved):
        return "ready-to-pin"
    if any(unresolved):
        raise ValueError("Candidate AL artifact calibration is only partially pinned")
    al.require_artifact_pins()
    expected = {
        "raw": (al.RAW_SHA256, raw_sha256),
        "raw size": (int(al.RAW_SIZE), raw_size),
        "DT": (al.FINAL_DTB_SHA256, dtb_sha256),
        "manifest": (al.ARTIFACT_MANIFEST_SHA256, manifest_sha256),
        "padded": (al.PADDED_SHA256, padded_sha256),
    }
    for label, (actual, wanted) in expected.items():
        if actual != wanted:
            raise ValueError(f"source-pinned Candidate AL {label} differs")
    return "source-pinned"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", required=True, type=pathlib.Path)
    parser.add_argument("--second", required=True, type=pathlib.Path)
    parser.add_argument("--ah-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--ak-artifact", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        roots = {
            "first": resolve_directory(args.first, "first AL artifact"),
            "second": resolve_directory(args.second, "second AL artifact"),
            "AH": resolve_directory(args.ah_artifact, "Candidate AH artifact"),
            "AK": resolve_directory(args.ak_artifact, "Candidate AK artifact"),
        }
        if roots["first"] == roots["second"] or roots["first"].samefile(
            roots["second"]
        ):
            raise ValueError("reproduction requires two independent AL trees")
        script_dir = pathlib.Path(__file__).resolve().parent
        run_validator(
            [
                sys.executable,
                os.fspath(script_dir / "validate-lineage.py"),
                "--ah-artifact",
                os.fspath(roots["AH"]),
                "--ak-artifact",
                os.fspath(roots["AK"]),
            ]
        )
        first = inventory(roots["first"])
        second = inventory(roots["second"])
        validate_tree(roots["first"], first, roots["AH"])
        validate_tree(roots["second"], second, roots["AH"])
        if first != second:
            raise ValueError("independent Candidate AL artifacts differ by byte or mode")

        for root in (roots["first"], roots["second"]):
            run_validator(
                [
                    sys.executable,
                    os.fspath(script_dir / "validate-dtb-delta.py"),
                    "--ah",
                    os.fspath(roots["AH"] / al.AH_DTB_MEMBER),
                    "--candidate",
                    os.fspath(root / al.DTB_MEMBER),
                ]
            )
            run_validator(
                [
                    sys.executable,
                    os.fspath(script_dir / "validate-boot.py"),
                    "--ah-artifact",
                    os.fspath(roots["AH"]),
                    "--candidate",
                    os.fspath(root / al.BOOT_MEMBER),
                    "--dtb",
                    os.fspath(root / al.DTB_MEMBER),
                    "--image-gz",
                    os.fspath(root / "Image.gz"),
                    "--system-map",
                    os.fspath(root / "System.map"),
                    "--kernel-config",
                    os.fspath(root / "kernel.config"),
                    "--initramfs",
                    os.fspath(root / al.INITRAMFS_MEMBER),
                ]
            )

        raw_sha256 = first[al.BOOT_MEMBER][1]
        raw_size = first[al.BOOT_MEMBER][2]
        dtb_sha256 = first[al.DTB_MEMBER][1]
        manifest_sha256 = first["SHA256SUMS"][1]
        if not 0 < raw_size <= al.BOOT2_SIZE:
            raise ValueError("Candidate AL raw size exceeds boot2")
        padded_sha256 = padded_digest(roots["first"] / al.BOOT_MEMBER, raw_size)
        if raw_sha256 in {al.AH_RAW_SHA256, al.AK_RAW_SHA256}:
            raise ValueError("Candidate AL raw identity equals a predecessor")
        if padded_sha256 in {al.AH_PADDED_SHA256, al.AK_PADDED_SHA256}:
            raise ValueError("Candidate AL padded identity equals a predecessor")
        state = calibration_state(
            raw_sha256,
            raw_size,
            dtb_sha256,
            manifest_sha256,
            padded_sha256,
        )

        print("validation=candidate-al-artifact-reproduction")
        print(f"members={len(first)}")
        print("bytes_identical=yes")
        print("modes_identical=yes")
        print(f"raw_sha256={raw_sha256}")
        print(f"raw_size={raw_size}")
        print(f"final_dtb_sha256={dtb_sha256}")
        print(f"artifact_manifest_sha256={manifest_sha256}")
        print(f"padded_sha256={padded_sha256}")
        print(f"padded_size={al.BOOT2_SIZE}")
        print(f"calibration_state={state}")
        print("functional_baseline=exact-candidate-ah")
        print("installed_predecessor=exact-candidate-ak")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
