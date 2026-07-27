"""Pinned identity for Candidate Pioneer."""

from __future__ import annotations

import hashlib
import pathlib
import stat


EXPERIMENT = "2026-07-26-a72-active-pioneer"
CANDIDATE = "Pioneer"
PROFILE = "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-active-pioneer"
SERIES = "patches/series-a72-active-pioneer"
AO_ARTIFACT_DIR = "candidate-AO-mt6797-dvfsp-handoff-owner-44fc1e6a"
AO_DTB_MEMBER = "mt6797-gemini-pda-dvfsp-handoff-owner.dtb"
AO_INITRAMFS_MEMBER = "gemini-dvfsp-handoff-owner-initramfs.img"
AO_MANIFEST_SHA256 = "6e8eb261d0a59807d20a605626c3ef8aff5799ac4f61494f77d6210be15acf85"
AO_DTB_SHA256 = "de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7"
AO_INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
AO_KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
BOOT_MEMBER = "gemini-mt6797-a72-active-pioneer.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-a72-active-pioneer.dtb"
INITRAMFS_MEMBER = "gemini-a72-active-pioneer-initramfs.img"
ARTIFACT_PREFIX = "candidate-Pioneer-a72-active-"
BOOT2_SIZE = 16 * 1024 * 1024


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()
