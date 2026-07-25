#!/usr/bin/env python3
"""Validate the exact Candidate Y artifact used as Candidate Z's foundation."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import stat
import struct
import sys


Y_BASENAME = "candidate-Y-keyboard-typed-watchdog-reboot-final-94edd593"
Y_MANIFEST_SHA256 = "310ac503b4bbd8c5a3d5c31bcecb473064d5207ff30ad73111325ffe1a1c56a6"
Y_BOOT_SHA256 = "94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee"
Y_BOOT_SIZE = 6_866_944
Y_INITRAMFS_SHA256 = "11b0a8ecb144ebde0c9802e0cf7357b2d74b95e8ba44fbf6007a9f4d0d8bf3e2"
Y_INITRAMFS_SIZE = 1_307_003
Y_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
Y_DTB_SIZE = 26_259
Y_IMAGE_GZ_SHA256 = "d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41"
Y_IMAGE_GZ_SIZE = 5_529_675
Y_HELPER_SHA256 = "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
Y_HELPER_SIZE = 710_808

BOOT_NAME = "gemini-keyboard-typed-watchdog-reboot.boot.img"
RAMDISK_NAME = "gemini-keyboard-typed-watchdog-reboot-initramfs.img"
DTB_NAME = "mt6797-gemini-pda-keyboard-typed-watchdog-reboot.dtb"
HELPER_NAME = "input-event-capture"
EXPECTED_INVENTORY = {
    "SHA256SUMS",
    "Image.gz",
    "boot-build.txt",
    "boot-validation.txt",
    BOOT_NAME,
    RAMDISK_NAME,
    "initramfs-build.txt",
    "initramfs-validation.txt",
    HELPER_NAME,
    "input-tree.sha256",
    DTB_NAME,
    "lk-analysis.txt",
    "provenance.txt",
    "source-build.json",
    "x-baseline-validation.txt",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def read_regular(path: pathlib.Path, mode: int = 0o600) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError(f"not a regular non-symlink file: {path.name}")
    if stat.S_IMODE(info.st_mode) != mode:
        raise ValueError(f"unexpected mode for {path.name}")
    return path.read_bytes()


def parse_manifest(data: bytes) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw in data.decode("ascii").splitlines():
        fields = raw.split(maxsplit=1)
        if len(fields) != 2:
            raise ValueError("malformed Candidate Y SHA256SUMS")
        checksum, name = fields
        name = name.removeprefix("*").removeprefix("./")
        if len(checksum) != 64 or name in entries:
            raise ValueError("invalid or duplicate Candidate Y manifest entry")
        entries[name] = checksum
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        root = args.baseline
        if root.is_symlink() or not root.is_dir() or root.name != Y_BASENAME:
            raise ValueError("baseline is not the named exact Candidate Y artifact")
        if stat.S_IMODE(root.stat().st_mode) != 0o700:
            raise ValueError("Candidate Y artifact directory mode changed")
        inventory = {item.name for item in root.iterdir()}
        if inventory != EXPECTED_INVENTORY:
            raise ValueError("Candidate Y artifact inventory changed")

        manifest_data = read_regular(root / "SHA256SUMS")
        if digest(manifest_data) != Y_MANIFEST_SHA256:
            raise ValueError("Candidate Y SHA256SUMS hash mismatch")
        manifest = parse_manifest(manifest_data)
        if set(manifest) != EXPECTED_INVENTORY - {"SHA256SUMS"}:
            raise ValueError("Candidate Y manifest inventory changed")
        for name, expected in manifest.items():
            mode = 0o755 if name == HELPER_NAME else 0o600
            if digest(read_regular(root / name, mode)) != expected:
                raise ValueError(f"Candidate Y manifest mismatch: {name}")

        boot = read_regular(root / BOOT_NAME)
        ramdisk = read_regular(root / RAMDISK_NAME)
        dtb = read_regular(root / DTB_NAME)
        helper = read_regular(root / HELPER_NAME, 0o755)
        for data, expected_hash, expected_size, label in (
            (boot, Y_BOOT_SHA256, Y_BOOT_SIZE, "boot"),
            (ramdisk, Y_INITRAMFS_SHA256, Y_INITRAMFS_SIZE, "initramfs"),
            (dtb, Y_DTB_SHA256, Y_DTB_SIZE, "DTB"),
            (helper, Y_HELPER_SHA256, Y_HELPER_SIZE, "helper"),
        ):
            if len(data) != expected_size or digest(data) != expected_hash:
                raise ValueError(f"Candidate Y {label} identity mismatch")

        if boot[:8] != b"ANDROID!":
            raise ValueError("Candidate Y Android magic changed")
        fields = struct.unpack_from("<10I", boot, 8)
        kernel_size, kernel_addr, ramdisk_size, ramdisk_addr = fields[:4]
        second_size, second_addr, tags_addr, page_size, dt_size, unused = fields[4:]
        if (kernel_addr, ramdisk_addr, second_addr, tags_addr, page_size) != (
            0x40200000, 0x45000000, 0x40F00000, 0x44000000, 2048
        ):
            raise ValueError("Candidate Y Android address/page contract changed")
        if second_size or dt_size or unused or ramdisk_size != len(ramdisk):
            raise ValueError("Candidate Y Android payload-size contract changed")
        kernel_offset = page_size
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end, page_size)
        ramdisk_end = ramdisk_offset + ramdisk_size
        if kernel_size != Y_IMAGE_GZ_SIZE + Y_DTB_SIZE:
            raise ValueError("Candidate Y kernel field size changed")
        kernel = boot[kernel_offset:kernel_end]
        image_gz = kernel[:-Y_DTB_SIZE]
        if digest(image_gz) != Y_IMAGE_GZ_SHA256 or kernel[-Y_DTB_SIZE:] != dtb:
            raise ValueError("Candidate Y kernel is not exact Image.gz plus exact DTB")
        if boot[ramdisk_offset:ramdisk_end] != ramdisk:
            raise ValueError("Candidate Y ramdisk bytes changed")
        if len(boot) != align(ramdisk_end, page_size):
            raise ValueError("Candidate Y container length changed")

        build = json.loads(read_regular(root / "source-build.json"))
        expected_build = {
            "build_profile": "observability-fbcon-rotation-keyboard-wrrd-manual-reboot",
            "config_inputs_sha256": "c811a1595510716777871637672f4298f4808b1d4fcea5c5da1d05d37676baa2",
            "config_sha256": "0a0e4ef39d5d89d0d54f55be44da753c93779d88bb94b35623679d1b08b66e74",
            "patchset_sha256": "4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4",
            "source_sha256": "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc",
            "modules_built": False,
        }
        for name, expected in expected_build.items():
            if build.get(name) != expected:
                raise ValueError(f"Candidate Y package provenance changed: {name}")

        print("validation=candidate-z-exact-y-baseline")
        print(f"y_boot_sha256={Y_BOOT_SHA256}")
        print(f"y_initramfs_sha256={Y_INITRAMFS_SHA256}")
        print(f"y_image_gz_sha256={Y_IMAGE_GZ_SHA256}")
        print(f"y_dtb_sha256={Y_DTB_SHA256}")
        print("kernel_package=exact-candidate-y")
        print("tty1_background_policy=exact-candidate-y")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
