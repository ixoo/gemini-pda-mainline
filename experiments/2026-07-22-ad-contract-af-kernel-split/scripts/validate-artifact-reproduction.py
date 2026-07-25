#!/usr/bin/env python3
"""Require two independently built Candidate AH artifacts to match exactly."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import subprocess
import sys


BOOT_MEMBER = "gemini-ad-contract-af-kernel-split.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-ad-contract-af-kernel-split.dtb"
INITRAMFS_MEMBER = "gemini-ad-contract-af-kernel-split-initramfs.img"
IMAGE_GZ_SHA256 = "b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912"
SYSTEM_MAP_SHA256 = "a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d"
CONFIG_SHA256 = "bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63"
INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
SOURCE_BUILD_SHA256 = "57ea75dd81ac7389c6a34d47cf9dc6a7300476f7ad85b00d782190585e686094"
KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
AD_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
AF_BOOT_SHA256 = "fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3"
AG_BOOT_SHA256 = "0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91"
AD_BOOT_SHA256 = "a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b"

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
    BOOT_MEMBER,
    INITRAMFS_MEMBER,
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    "lineage-validation.txt",
    DTB_MEMBER,
    "provenance.txt",
    "serializer.txt",
    "source-build.json",
}
FIXED_PROVENANCE = {
    "experiment": "2026-07-22-ad-contract-af-kernel-split",
    "candidate_label": "AH",
    "af_boot_sha256": AF_BOOT_SHA256,
    "ag_boot_sha256": AG_BOOT_SHA256,
    "ad_boot_sha256": AD_BOOT_SHA256,
    "image_gz_sha256": IMAGE_GZ_SHA256,
    "system_map_sha256": SYSTEM_MAP_SHA256,
    "config_sha256": CONFIG_SHA256,
    "initramfs_sha256": INITRAMFS_SHA256,
    "ad_dtb_sha256": AD_DTB_SHA256,
    "kernel_config_system_map_initramfs_helpers": "byte-exact-candidate-af-and-ag",
    "initramfs_keymap_helpers_also": "byte-exact-candidate-ad",
    "dtb_baseline": "byte-exact-hardware-passed-candidate-ad",
    "dtb_delta": "cpu8-and-cpu9-enable-method-only",
    "cpu8_cpu9_enable_method": "mediatek,mt6797-psci-rejecting",
    "simplefb_usb_keyboard_scp_reserved_memory": "byte-exact-candidate-ad",
    "a72_power_da9214_static_lk_framebuffer_nodes": "absent",
    "blacklisted_initcall": "mt6797_a72_power_driver_init",
    "patch_profile_manifest": "unchanged-file-only-component-split",
    "storage_access": "none",
    "watchdog_userspace": "none",
    "active_a72_operation": "none",
    "raw_framebuffer_write": "none",
    "artifact_builder_device_access": "none",
    "flash": "none",
    "runtime_result": "not-tested",
}
DYNAMIC_PROVENANCE = {
    "candidate_sha256",
    "candidate_size",
    "candidate_dtb_sha256",
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: pathlib.Path) -> dict[str, tuple[int, str]]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe artifact directory: {root}")
    output: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        path_info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(path_info.st_mode):
            raise ValueError(f"unexpected non-regular artifact member: {relative}")
        output[relative] = (stat.S_IMODE(path_info.st_mode), digest(path))
    return output


def parse_manifest(
    root: pathlib.Path, members: dict[str, tuple[int, str]]
) -> None:
    seen: set[str] = set()
    for line in (root / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("malformed Candidate AH artifact manifest")
        member = fields[1].removeprefix("*").removeprefix("./")
        if member in seen or member == "SHA256SUMS" or member not in members:
            raise ValueError("unsafe or duplicate Candidate AH manifest member")
        if fields[0] != members[member][1]:
            raise ValueError(f"Candidate AH artifact checksum mismatch: {member}")
        seen.add(member)
    if seen != EXPECTED_MEMBERS - {"SHA256SUMS"}:
        raise ValueError("Candidate AH manifest is not the exact artifact inventory")


def parse_provenance(path: pathlib.Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in output:
            raise ValueError("Candidate AH provenance is malformed or duplicated")
        output[key] = value
    return output


def validate_tree(
    root: pathlib.Path,
    members: dict[str, tuple[int, str]],
    ag_artifact: pathlib.Path,
) -> None:
    if set(members) != EXPECTED_MEMBERS:
        raise ValueError("Candidate AH artifact inventory changed")
    for member, (mode, _) in members.items():
        expected_mode = 0o755 if member in EXECUTABLE_MEMBERS else 0o600
        if mode != expected_mode:
            raise ValueError(f"Candidate AH artifact mode changed: {member}")
    parse_manifest(root, members)
    fixed_hashes = {
        "Image.gz": IMAGE_GZ_SHA256,
        "System.map": SYSTEM_MAP_SHA256,
        "kernel.config": CONFIG_SHA256,
        INITRAMFS_MEMBER: INITRAMFS_SHA256,
        "source-build.json": SOURCE_BUILD_SHA256,
        "gemini-us.bkeymap": KEYMAP_SHA256,
    }
    for member, expected in fixed_hashes.items():
        if members[member][1] != expected:
            raise ValueError(f"Candidate AH exact payload changed: {member}")
    for member in EXECUTABLE_MEMBERS:
        if members[member][1] != digest(ag_artifact / member):
            raise ValueError(f"Candidate AH userspace helper changed: {member}")

    boot_hash = members[BOOT_MEMBER][1]
    expected_name = f"candidate-AH-ad-contract-af-kernel-split-{boot_hash[:8]}"
    if root.name != expected_name:
        raise ValueError("Candidate AH artifact basename does not match boot hash")
    provenance = parse_provenance(root / "provenance.txt")
    if set(provenance) != set(FIXED_PROVENANCE) | DYNAMIC_PROVENANCE:
        raise ValueError("Candidate AH provenance inventory changed")
    for key, value in FIXED_PROVENANCE.items():
        if provenance[key] != value:
            raise ValueError(f"Candidate AH provenance changed: {key}")
    if provenance["candidate_sha256"] != boot_hash:
        raise ValueError("Candidate AH provenance boot checksum changed")
    if provenance["candidate_size"] != str((root / BOOT_MEMBER).stat().st_size):
        raise ValueError("Candidate AH provenance boot size changed")
    if provenance["candidate_dtb_sha256"] != members[DTB_MEMBER][1]:
        raise ValueError("Candidate AH provenance DTB checksum changed")


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=pathlib.Path, required=True)
    parser.add_argument("--second", type=pathlib.Path, required=True)
    parser.add_argument("--af-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ag-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ad-artifact", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        roots: dict[str, pathlib.Path] = {}
        for label, supplied in (
            ("first", args.first),
            ("second", args.second),
            ("AF", args.af_artifact),
            ("AG", args.ag_artifact),
            ("AD", args.ad_artifact),
        ):
            info = supplied.lstat()
            if supplied.is_symlink() or not stat.S_ISDIR(info.st_mode):
                raise ValueError(f"unsafe {label} artifact path")
            roots[label] = supplied.resolve(strict=True)
        if roots["first"] == roots["second"] or roots["first"].samefile(
            roots["second"]
        ):
            raise ValueError("reproduction requires two independent artifact trees")

        script_dir = pathlib.Path(__file__).resolve().parent
        lineage_validator = script_dir / "validate-lineage.py"
        dtb_validator = script_dir / "validate-dtb-delta.py"
        boot_validator = script_dir / "validate-boot.py"
        run_validator(
            [
                sys.executable,
                os.fspath(lineage_validator),
                "--af-artifact",
                os.fspath(roots["AF"]),
                "--ag-artifact",
                os.fspath(roots["AG"]),
                "--ad-artifact",
                os.fspath(roots["AD"]),
            ]
        )
        first = inventory(roots["first"])
        second = inventory(roots["second"])
        for root, members in ((roots["first"], first), (roots["second"], second)):
            validate_tree(root, members, roots["AG"])
            run_validator(
                [
                    sys.executable,
                    os.fspath(dtb_validator),
                    "--ad",
                    os.fspath(roots["AD"] / "mt6797-gemini-pda-smp8.dtb"),
                    "--candidate",
                    os.fspath(root / DTB_MEMBER),
                ]
            )
            run_validator(
                [
                    sys.executable,
                    os.fspath(boot_validator),
                    "--af-boot",
                    os.fspath(
                        roots["AF"]
                        / "gemini-a72-observer-initcall-diagnostic.boot.img"
                    ),
                    "--ag-boot",
                    os.fspath(
                        roots["AG"]
                        / "gemini-simplefb-observation-restoration.boot.img"
                    ),
                    "--ad-boot",
                    os.fspath(roots["AD"] / "gemini-smp8.boot.img"),
                    "--candidate",
                    os.fspath(root / BOOT_MEMBER),
                    "--image-gz",
                    os.fspath(root / "Image.gz"),
                    "--ad-dtb",
                    os.fspath(roots["AD"] / "mt6797-gemini-pda-smp8.dtb"),
                    "--ah-dtb",
                    os.fspath(root / DTB_MEMBER),
                    "--initramfs",
                    os.fspath(root / INITRAMFS_MEMBER),
                ]
            )
        if first != second:
            names = set(first) | set(second)
            changed = sorted(name for name in names if first.get(name) != second.get(name))
            raise ValueError("Candidate AH artifacts differ: " + ",".join(changed[:4]))

        print("validation=candidate-ah-artifact-reproduction")
        print(f"members={len(first)}")
        print(f"boot_sha256={first[BOOT_MEMBER][1]}")
        print(f"dtb_sha256={first[DTB_MEMBER][1]}")
        print("bytes_identical=yes")
        print("modes_identical=yes")
        print("whole_fdt_validated_twice=yes")
        print("android_v0_validated_twice=yes")
        print("device_access=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
