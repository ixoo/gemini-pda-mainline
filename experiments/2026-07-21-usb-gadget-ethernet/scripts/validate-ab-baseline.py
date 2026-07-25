#!/usr/bin/env python3
"""Validate the exact hardware-passed Candidate AB artifact foundation."""

from __future__ import annotations

import argparse
import gzip
import pathlib
import re
import stat
import struct
import sys
from dataclasses import dataclass

# Importing the local contract must not create a bytecode cache: this validator
# is a read-only gate even when its caller omits PYTHONDONTWRITEBYTECODE.
sys.dont_write_bytecode = True

from ac_contract import (
    AB_ARTIFACT_NAME,
    AB_BOOT_FILE,
    AB_BOOT_SHA256,
    AB_BOOT_SIZE,
    AB_DTB_FILE,
    AB_DTB_SHA256,
    AB_DTB_SIZE,
    AB_EXECUTABLE_FILES,
    AB_EXPECTED_FILES,
    AB_IMAGE_GZ_FILE,
    AB_IMAGE_GZ_SHA256,
    AB_IMAGE_GZ_SIZE,
    AB_INITRAMFS_CRITICAL,
    AB_INITRAMFS_DIRECTORIES,
    AB_INITRAMFS_EXPECTED_MEMBERS,
    AB_INITRAMFS_FILE,
    AB_INITRAMFS_REGULAR_MODES,
    AB_INITRAMFS_SHA256,
    AB_INITRAMFS_SIZE,
    AB_INITRAMFS_SYMLINKS,
    AB_INPUT_HELPER_SHA256,
    AB_KEYMAP_FILE,
    AB_KEYMAP_SHA256,
    AB_KEYMAP_SIZE,
    AB_KEYMAP_VERIFIER_SHA256,
    AB_MANIFEST_SHA256,
    AB_PROVENANCE_SHA256,
    AB_SOURCE_BUILD_SHA256,
    AB_SYSTEM_MAP_SHA256,
    AB_UNICODE_HELPER_SHA256,
    BUSYBOX_SHA256,
    DISPATCH_ENV_SHA256,
    digest_bytes,
    read_regular,
)


@dataclass(frozen=True)
class Member:
    mode: int
    uid: int
    gid: int
    nlink: int
    mtime: int
    devmajor: int
    devminor: int
    rdevmajor: int
    rdevminor: int
    data: bytes


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) // boundary * boundary


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_newc(compressed: bytes) -> dict[str, Member]:
    """Parse the pinned canonical gzip/newc stream without extracting it."""

    canonical_gzip_header = b"\x1f\x8b\x08\0\0\0\0\0\x02\x03"
    if len(compressed) < len(canonical_gzip_header) or not compressed.startswith(
        canonical_gzip_header
    ):
        raise ValueError("AB initramfs is not a canonical gzip -n -9 stream")
    raw = gzip.decompress(compressed)
    offset = 0
    previous = ""
    members: dict[str, Member] = {}
    while True:
        if offset + 110 > len(raw):
            raise ValueError("truncated AB newc header")
        header = raw[offset : offset + 110]
        if header[:6] != b"070701":
            raise ValueError("AB initramfs is not crc-free newc")
        try:
            fields = [
                int(header[6 + index * 8 : 14 + index * 8], 16)
                for index in range(13)
            ]
        except ValueError as exc:
            raise ValueError("invalid AB newc numeric field") from exc
        (
            _ino,
            mode,
            uid,
            gid,
            nlink,
            mtime,
            size,
            devmajor,
            devminor,
            rdevmajor,
            rdevminor,
            namesize,
            check,
        ) = fields
        if check or namesize < 2:
            raise ValueError("invalid AB newc checksum or name size")
        name_start = offset + 110
        name_end = name_start + namesize
        if name_end > len(raw) or raw[name_end - 1] != 0:
            raise ValueError("truncated or unterminated AB newc name")
        stored_name = raw[name_start : name_end - 1].decode("utf-8")
        data_start = align4(name_end)
        data_end = data_start + size
        if data_end > len(raw):
            raise ValueError("truncated AB newc member")
        if stored_name == "TRAILER!!!":
            if size or any(raw[align4(data_end) :]):
                raise ValueError("invalid AB newc trailer or trailing bytes")
            break
        name = stored_name.removeprefix("./") or "."
        parts = pathlib.PurePosixPath(name).parts
        if stored_name.startswith("/") or ".." in parts or name in members:
            raise ValueError("unsafe or duplicate AB newc member")
        if stored_name != "." and stored_name not in {name, f"./{name}"}:
            raise ValueError("non-canonical AB newc member name")
        if previous and name < previous:
            raise ValueError("AB newc members are not canonically sorted")
        previous = name
        members[name] = Member(
            mode=mode,
            uid=uid,
            gid=gid,
            nlink=nlink,
            mtime=mtime,
            devmajor=devmajor,
            devminor=devminor,
            rdevmajor=rdevmajor,
            rdevminor=rdevminor,
            data=raw[data_start:data_end],
        )
        offset = align4(data_end)
    return members


def parse_manifest(data: bytes) -> dict[str, str]:
    text = data.decode("ascii")
    if not text or not text.endswith("\n") or "\r" in text:
        raise ValueError("AB manifest is not canonical newline-terminated ASCII")
    manifest: dict[str, str] = {}
    line_pattern = re.compile(r"([0-9a-f]{64})  \./([A-Za-z0-9][A-Za-z0-9._-]*)")
    for line in text.splitlines():
        match = line_pattern.fullmatch(line)
        if match is None:
            raise ValueError("malformed AB manifest line")
        checksum, name = match.groups()
        if name in manifest:
            raise ValueError("duplicate AB manifest entry")
        manifest[name] = checksum
    expected = AB_EXPECTED_FILES - {"SHA256SUMS"}
    if set(manifest) != expected:
        raise ValueError("AB manifest inventory changed")
    canonical = "".join(
        f"{manifest[name]}  ./{name}\n" for name in sorted(manifest)
    )
    if text != canonical:
        raise ValueError("AB manifest ordering or formatting changed")
    return manifest


def parse_provenance(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        if "=" not in line:
            raise ValueError("malformed AB provenance line")
        key, value = line.split("=", 1)
        if re.fullmatch(r"[a-z0-9_]+", key) is None or key in result:
            raise ValueError("invalid or duplicate AB provenance key")
        result[key] = value
    return result


def validate_initramfs(data: bytes, contents: dict[str, bytes]) -> None:
    if digest_bytes(data) != AB_INITRAMFS_SHA256 or len(data) != AB_INITRAMFS_SIZE:
        raise ValueError("exact AB initramfs identity changed")
    members = parse_newc(data)
    if set(members) != AB_INITRAMFS_EXPECTED_MEMBERS:
        raise ValueError("AB initramfs inventory changed")

    for name, member in members.items():
        if any(
            (
                member.uid,
                member.gid,
                member.mtime,
                member.devmajor,
                member.devminor,
                member.rdevmajor,
                member.rdevminor,
            )
        ):
            raise ValueError(f"AB initramfs metadata changed: {name}")
        if name in AB_INITRAMFS_DIRECTORIES:
            if member.mode != stat.S_IFDIR | 0o755 or member.nlink != 2 or member.data:
                raise ValueError(f"AB initramfs directory changed: {name}")
        elif name in AB_INITRAMFS_SYMLINKS:
            if (
                member.mode != stat.S_IFLNK | 0o777
                or member.nlink != 1
                or member.data != AB_INITRAMFS_SYMLINKS[name]
            ):
                raise ValueError(f"AB initramfs symlink changed: {name}")
        else:
            expected_mode = AB_INITRAMFS_REGULAR_MODES[name]
            if member.mode != stat.S_IFREG | expected_mode or member.nlink != 1:
                raise ValueError(f"AB initramfs regular member changed: {name}")

    for name, (checksum, size) in AB_INITRAMFS_CRITICAL.items():
        member = members[name]
        if digest_bytes(member.data) != checksum or len(member.data) != size:
            raise ValueError(f"exact AB initramfs member changed: {name}")

    if members["bin/reboot-dispatch.env"].data != b"alias reboot='/bin/reboot'\n":
        raise ValueError("AB reboot dispatch bytes changed")
    if digest_bytes(members["bin/busybox"].data) != BUSYBOX_SHA256:
        raise ValueError("AB BusyBox identity changed")
    if digest_bytes(members["bin/reboot-dispatch.env"].data) != DISPATCH_ENV_SHA256:
        raise ValueError("AB reboot dispatch identity changed")

    inherited_pairs = (
        ("bin/console-keymap-verify", "console-keymap-verify"),
        ("bin/console-unicode-mode", "console-unicode-mode"),
        ("bin/input-event-capture", "input-event-capture"),
        ("etc/gemini-us.bkeymap", AB_KEYMAP_FILE),
    )
    for member_name, artifact_name in inherited_pairs:
        if members[member_name].data != contents[artifact_name]:
            raise ValueError(
                f"AB initramfs member differs from artifact companion: {member_name}"
            )


def validate_android_v0(contents: dict[str, bytes]) -> None:
    boot = contents[AB_BOOT_FILE]
    ramdisk = contents[AB_INITRAMFS_FILE]
    image_gz = contents[AB_IMAGE_GZ_FILE]
    dtb = contents[AB_DTB_FILE]
    if boot[:8] != b"ANDROID!":
        raise ValueError("AB boot image is not Android v0")
    fields = struct.unpack_from("<10I", boot, 8)
    kernel_size, _kernel_addr, ramdisk_size = fields[:3]
    second_size, page_size, dt_size = fields[4], fields[7], fields[8]
    if page_size != 2048 or second_size or dt_size:
        raise ValueError("AB Android-v0 layout changed")
    kernel_offset = page_size
    kernel_end = kernel_offset + kernel_size
    ramdisk_offset = align(kernel_end, page_size)
    ramdisk_end = ramdisk_offset + ramdisk_size
    if kernel_size != len(image_gz) + len(dtb):
        raise ValueError("AB appended-DTB kernel size changed")
    if boot[kernel_offset:kernel_end] != image_gz + dtb:
        raise ValueError("AB kernel field differs from exact Image.gz plus DTB")
    if ramdisk_size != len(ramdisk) or boot[ramdisk_offset:ramdisk_end] != ramdisk:
        raise ValueError("AB ramdisk field differs from exact initramfs")
    if any(boot[kernel_end:ramdisk_offset]) or any(boot[ramdisk_end:]):
        raise ValueError("AB Android-v0 padding is not zero")
    if len(boot) != align(ramdisk_end, page_size):
        raise ValueError("AB Android-v0 length is not canonical")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        artifact = args.artifact
        info = artifact.lstat()
        if artifact.is_symlink() or not stat.S_ISDIR(info.st_mode):
            raise ValueError("AB artifact is not a regular directory")
        if artifact.name != AB_ARTIFACT_NAME:
            raise ValueError("AB artifact basename is not the hardware-passed revision")
        if stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError("AB artifact directory mode is not 0700")
        if {entry.name for entry in artifact.iterdir()} != AB_EXPECTED_FILES:
            raise ValueError("AB artifact inventory changed")

        contents: dict[str, bytes] = {}
        for name in AB_EXPECTED_FILES:
            mode = 0o755 if name in AB_EXECUTABLE_FILES else 0o600
            contents[name] = read_regular(artifact / name, f"AB {name}", mode)

        manifest_data = contents["SHA256SUMS"]
        if digest_bytes(manifest_data) != AB_MANIFEST_SHA256:
            raise ValueError("AB manifest identity changed")
        manifest = parse_manifest(manifest_data)
        for name, expected in manifest.items():
            if digest_bytes(contents[name]) != expected:
                raise ValueError(f"AB manifest checksum mismatch: {name}")

        exact = (
            (AB_BOOT_FILE, AB_BOOT_SHA256, AB_BOOT_SIZE),
            (AB_INITRAMFS_FILE, AB_INITRAMFS_SHA256, AB_INITRAMFS_SIZE),
            (AB_IMAGE_GZ_FILE, AB_IMAGE_GZ_SHA256, AB_IMAGE_GZ_SIZE),
            (AB_DTB_FILE, AB_DTB_SHA256, AB_DTB_SIZE),
            (AB_KEYMAP_FILE, AB_KEYMAP_SHA256, AB_KEYMAP_SIZE),
            ("System.map", AB_SYSTEM_MAP_SHA256, None),
            ("source-build.json", AB_SOURCE_BUILD_SHA256, None),
            ("provenance.txt", AB_PROVENANCE_SHA256, None),
            ("console-keymap-verify", AB_KEYMAP_VERIFIER_SHA256, 537_576),
            ("console-unicode-mode", AB_UNICODE_HELPER_SHA256, 537_584),
            ("input-event-capture", AB_INPUT_HELPER_SHA256, 710_808),
        )
        for name, checksum, size in exact:
            if digest_bytes(contents[name]) != checksum:
                raise ValueError(f"exact AB identity changed: {name}")
            if size is not None and len(contents[name]) != size:
                raise ValueError(f"exact AB size changed: {name}")

        validate_initramfs(contents[AB_INITRAMFS_FILE], contents)
        validate_android_v0(contents)

        provenance = parse_provenance(contents["provenance.txt"])
        required_provenance = {
            "experiment": "2026-07-20-mt6797-kernel-restart-diagnostic",
            "candidate_label": "AB",
            "marker": "GEMINI_MT6797_KERNEL_RESTART_20260720_AB",
            "image_gz_sha256": AB_IMAGE_GZ_SHA256,
            "candidate_dtb_sha256": AB_DTB_SHA256,
            "candidate_initramfs_sha256": AB_INITRAMFS_SHA256,
            "candidate_sha256": AB_BOOT_SHA256,
            "candidate_size": str(AB_BOOT_SIZE),
            "aa_keymap_sha256": AB_KEYMAP_SHA256,
            "dtb_lineage": "byte-exact-hardware-passed-aa-r1",
            "keymap_and_gate": "exact-aa-r1-with-attribution-only-shell-transform",
            "reboot_dispatch": "ENV-alias-absolute-wrapper",
            "manual_reboot": "busybox-reboot-no-sync-force",
            "watchdog_userspace": "start-none,open-none,ping-none,countdown-none,fallback-none",
            "automatic_reboot": "none",
            "deterministic_replica": "initramfs-and-android-v0-byte-identical",
            "storage_access": "none",
            "runtime_networking": "none",
            "hardware_write": "none",
            "runtime_result": "not-tested",
        }
        for key, expected in required_provenance.items():
            if provenance.get(key) != expected:
                raise ValueError(f"AB provenance mismatch: {key}")

        print("validation=exact-hardware-passed-candidate-ab")
        print(f"artifact={AB_ARTIFACT_NAME}")
        print(f"manifest_sha256={AB_MANIFEST_SHA256}")
        print(f"boot_sha256={AB_BOOT_SHA256}")
        print(f"initramfs_sha256={AB_INITRAMFS_SHA256}")
        print(f"image_gz_sha256={AB_IMAGE_GZ_SHA256}")
        print(f"dtb_sha256={AB_DTB_SHA256}")
        print(f"keymap_sha256={AB_KEYMAP_SHA256}")
        print(f"busybox_sha256={BUSYBOX_SHA256}")
        print("hardware_result=boot-keyboard-idle-and-kernel-reboot-pass-once")
        print("baseline_runtime_networking=none")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
