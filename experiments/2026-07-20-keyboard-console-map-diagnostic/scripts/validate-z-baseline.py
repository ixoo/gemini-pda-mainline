#!/usr/bin/env python3
"""Validate the exact Candidate Z artifact used as Candidate AA's basis."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import stat
import sys


BASELINE_NAME = "candidate-Z-keyboard-reboot-dispatch-final-985a6472"
MANIFEST_SHA256 = "534484e5362e1e4c73ec8438bd36656b444e88199dbd17724a160c75403dbaaa"
BOOT_SHA256 = "985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9"
BOOT_SIZE = 6_866_944
INITRAMFS_SHA256 = "a21cc6bed9024bba9e01864aeb0c6c3339231d217f77ff5fa733ea33e6a0e7d2"
DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
IMAGE_GZ_SHA256 = "d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41"
HELPER_SHA256 = "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
SOURCE_BUILD_SHA256 = "6c04e871811902799ff4fc68d2b4440ba2e42026b4ca8142e7bfbd425a0ce071"
EXPECTED_FILES = {
    "SHA256SUMS",
    "Image.gz",
    "ash-dispatch-validation.txt",
    "boot-build.txt",
    "boot-validation.txt",
    "gemini-keyboard-reboot-dispatch-initramfs.img",
    "gemini-keyboard-reboot-dispatch.boot.img",
    "initramfs-build.txt",
    "initramfs-validation.txt",
    "input-event-capture",
    "input-tree.sha256",
    "lk-analysis.txt",
    "mt6797-gemini-pda-keyboard-reboot-dispatch.dtb",
    "provenance.txt",
    "source-build.json",
    "y-baseline-validation.txt",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, mode: int = 0o600) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"not a regular non-symlink file: {path.name}")
    if stat.S_IMODE(info.st_mode) != mode:
        raise ValueError(f"unexpected mode for {path.name}")
    return path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        root = args.baseline
        if root.is_symlink() or not root.is_dir() or root.name != BASELINE_NAME:
            raise ValueError("baseline is not the named exact Candidate Z artifact")
        if stat.S_IMODE(root.stat().st_mode) != 0o700:
            raise ValueError("Candidate Z artifact directory mode changed")
        if {item.name for item in root.iterdir()} != EXPECTED_FILES:
            raise ValueError("Candidate Z artifact inventory changed")

        manifest_data = read_regular(root / "SHA256SUMS")
        if digest(manifest_data) != MANIFEST_SHA256:
            raise ValueError("Candidate Z manifest identity mismatch")
        manifest: dict[str, str] = {}
        for line in manifest_data.decode("ascii").splitlines():
            fields = line.split(maxsplit=1)
            if len(fields) != 2:
                raise ValueError("malformed Candidate Z manifest")
            checksum, name = fields
            name = name.removeprefix("*").removeprefix("./")
            if len(checksum) != 64 or name in manifest:
                raise ValueError("invalid or duplicate Candidate Z manifest entry")
            manifest[name] = checksum
        if set(manifest) != EXPECTED_FILES - {"SHA256SUMS"}:
            raise ValueError("Candidate Z manifest inventory changed")
        for name, expected in manifest.items():
            mode = 0o755 if name == "input-event-capture" else 0o600
            if digest(read_regular(root / name, mode)) != expected:
                raise ValueError(f"Candidate Z manifest mismatch: {name}")

        identities = (
            ("gemini-keyboard-reboot-dispatch.boot.img", BOOT_SHA256, BOOT_SIZE),
            ("gemini-keyboard-reboot-dispatch-initramfs.img", INITRAMFS_SHA256, None),
            ("mt6797-gemini-pda-keyboard-reboot-dispatch.dtb", DTB_SHA256, None),
            ("Image.gz", IMAGE_GZ_SHA256, None),
            ("input-event-capture", HELPER_SHA256, None),
            ("source-build.json", SOURCE_BUILD_SHA256, None),
        )
        for name, expected_hash, expected_size in identities:
            mode = 0o755 if name == "input-event-capture" else 0o600
            data = read_regular(root / name, mode)
            if digest(data) != expected_hash or (
                expected_size is not None and len(data) != expected_size
            ):
                raise ValueError(f"Candidate Z identity mismatch: {name}")

        print("validation=candidate-aa-exact-z-baseline")
        print(f"z_manifest_sha256={MANIFEST_SHA256}")
        print(f"z_boot_sha256={BOOT_SHA256}")
        print(f"z_initramfs_sha256={INITRAMFS_SHA256}")
        print(f"z_dtb_sha256={DTB_SHA256}")
        print("kernel_dtb_config=byte-exact-candidate-z")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
