#!/usr/bin/env python3
"""Validate the exact hardware-passed Candidate AA r1 artifact foundation."""

from __future__ import annotations

import argparse
import pathlib
import re
import stat
import struct
import sys

from ab_contract import (
    AA_ARTIFACT_NAME,
    AA_BOOT_SHA256,
    AA_BOOT_SIZE,
    AA_DTB_SHA256,
    AA_DTB_SIZE,
    AA_EXECUTABLE_FILES,
    AA_EXPECTED_FILES,
    AA_IMAGE_GZ_SHA256,
    AA_INITRAMFS_SHA256,
    AA_INITRAMFS_SIZE,
    AA_INPUT_HELPER_SHA256,
    AA_KEYMAP_SHA256,
    AA_KEYMAP_VERIFIER_SHA256,
    AA_MANIFEST_SHA256,
    AA_SOURCE_BUILD_SHA256,
    AA_UNICODE_HELPER_SHA256,
    digest_bytes,
    read_regular,
)


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def parse_provenance(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        if "=" not in line:
            raise ValueError("malformed AA provenance line")
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in result:
            raise ValueError("invalid or duplicate AA provenance key")
        result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        artifact = args.artifact
        if artifact.is_symlink() or not artifact.is_dir():
            raise ValueError("AA artifact is not a regular directory")
        if artifact.name != AA_ARTIFACT_NAME:
            raise ValueError("AA artifact basename is not the hardware-passed revision")
        if stat.S_IMODE(artifact.stat().st_mode) != 0o700:
            raise ValueError("AA artifact directory mode is not 0700")
        if {entry.name for entry in artifact.iterdir()} != AA_EXPECTED_FILES:
            raise ValueError("AA artifact inventory changed")

        contents: dict[str, bytes] = {}
        for name in AA_EXPECTED_FILES:
            mode = 0o755 if name in AA_EXECUTABLE_FILES else 0o600
            contents[name] = read_regular(artifact / name, f"AA {name}", mode)
        if digest_bytes(contents["SHA256SUMS"]) != AA_MANIFEST_SHA256:
            raise ValueError("AA manifest identity changed")

        manifest: dict[str, str] = {}
        for line in contents["SHA256SUMS"].decode("ascii").splitlines():
            fields = line.split(maxsplit=1)
            if len(fields) != 2:
                raise ValueError("malformed AA manifest line")
            checksum, name = fields
            name = name.removeprefix("*").removeprefix("./")
            if not re.fullmatch(r"[0-9a-f]{64}", checksum) or name in manifest:
                raise ValueError("invalid or duplicate AA manifest entry")
            manifest[name] = checksum
        if set(manifest) != AA_EXPECTED_FILES - {"SHA256SUMS"}:
            raise ValueError("AA manifest inventory changed")
        for name, expected in manifest.items():
            if digest_bytes(contents[name]) != expected:
                raise ValueError(f"AA manifest checksum mismatch: {name}")

        exact = (
            ("gemini-keyboard-console-map.boot.img", AA_BOOT_SHA256, AA_BOOT_SIZE),
            (
                "gemini-keyboard-console-map-initramfs.img",
                AA_INITRAMFS_SHA256,
                AA_INITRAMFS_SIZE,
            ),
            ("Image.gz", AA_IMAGE_GZ_SHA256, None),
            ("mt6797-gemini-pda-keyboard-console-map.dtb", AA_DTB_SHA256, AA_DTB_SIZE),
            ("gemini-us.bkeymap", AA_KEYMAP_SHA256, 2311),
            ("console-unicode-mode", AA_UNICODE_HELPER_SHA256, None),
            ("console-keymap-verify", AA_KEYMAP_VERIFIER_SHA256, None),
            ("input-event-capture", AA_INPUT_HELPER_SHA256, None),
            ("source-build.json", AA_SOURCE_BUILD_SHA256, None),
        )
        for name, checksum, size in exact:
            if digest_bytes(contents[name]) != checksum:
                raise ValueError(f"exact AA identity changed: {name}")
            if size is not None and len(contents[name]) != size:
                raise ValueError(f"exact AA size changed: {name}")

        boot = contents["gemini-keyboard-console-map.boot.img"]
        ramdisk = contents["gemini-keyboard-console-map-initramfs.img"]
        image_gz = contents["Image.gz"]
        dtb = contents["mt6797-gemini-pda-keyboard-console-map.dtb"]
        if boot[:8] != b"ANDROID!":
            raise ValueError("AA boot image is not Android v0")
        fields = struct.unpack_from("<10I", boot, 8)
        kernel_size, _kernel_addr, ramdisk_size = fields[:3]
        second_size, page_size, dt_size = fields[4], fields[7], fields[8]
        if page_size != 2048 or second_size or dt_size:
            raise ValueError("AA Android-v0 layout changed")
        kernel_offset = page_size
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end, page_size)
        ramdisk_end = ramdisk_offset + ramdisk_size
        if kernel_size != len(image_gz) + len(dtb):
            raise ValueError("AA appended-DTB kernel size changed")
        if boot[kernel_offset:kernel_end] != image_gz + dtb:
            raise ValueError("AA kernel field differs from its pinned Image.gz plus DTB")
        if ramdisk_size != len(ramdisk) or boot[ramdisk_offset:ramdisk_end] != ramdisk:
            raise ValueError("AA ramdisk field differs from its pinned initramfs")
        if any(boot[kernel_end:ramdisk_offset]) or any(boot[ramdisk_end:]):
            raise ValueError("AA Android-v0 padding is not zero")
        if len(boot) != align(ramdisk_end, page_size):
            raise ValueError("AA Android-v0 length is not canonical")

        provenance = parse_provenance(contents["provenance.txt"])
        required = {
            "experiment": "2026-07-20-keyboard-console-map-diagnostic",
            "candidate_label": "AA",
            "candidate_revision": "r1",
            "marker": "GEMINI_KEYBOARD_CONSOLE_MAP_20260720_AA_R1",
            "candidate_sha256": AA_BOOT_SHA256,
            "candidate_size": str(AA_BOOT_SIZE),
            "candidate_initramfs_sha256": AA_INITRAMFS_SHA256,
            "keymap_sha256": AA_KEYMAP_SHA256,
            "keymap_verifier_sha256": AA_KEYMAP_VERIFIER_SHA256,
            "keyboard_matrix": "byte-exact-candidate-z",
            "reboot_dispatch": "byte-exact-candidate-z",
            "deterministic_replica": (
                "helpers-keymap-initramfs-and-android-v0-byte-identical"
            ),
            "storage_access": "none",
            "runtime_networking": "none",
            "hardware_write": "none",
        }
        for key, expected in required.items():
            if provenance.get(key) != expected:
                raise ValueError(f"AA provenance mismatch: {key}")

        print("validation=exact-hardware-passed-candidate-aa-r1")
        print(f"artifact={AA_ARTIFACT_NAME}")
        print(f"boot_sha256={AA_BOOT_SHA256}")
        print(f"initramfs_sha256={AA_INITRAMFS_SHA256}")
        print(f"image_gz_sha256={AA_IMAGE_GZ_SHA256}")
        print(f"dtb_sha256={AA_DTB_SHA256}")
        print(f"keymap_sha256={AA_KEYMAP_SHA256}")
        print(f"keymap_verifier_sha256={AA_KEYMAP_VERIFIER_SHA256}")
        print("hardware_result=keyboard-map-working-reboot-via-watchdog-working")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
