#!/usr/bin/env python3
"""Pinned identities for storage-inert Candidate AO."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-24-mt6797-dvfsp-one-way-handoff"
CANDIDATE = "AO"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner"
)

AH_ARTIFACT_DIR = "candidate-AH-ad-contract-af-kernel-split-e5ba6ee0"
AH_DTB_MEMBER = "mt6797-gemini-pda-ad-contract-af-kernel-split.dtb"
AH_INITRAMFS_MEMBER = "gemini-ad-contract-af-kernel-split-initramfs.img"
AH_MANIFEST_SHA256 = "04b25bfc5e72645318273e03adc80191df7d52994acc7ade8202a64d95223997"
AH_RAW_SHA256 = "e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197"
AH_DTB_SHA256 = "27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845"
INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"

AN_ARTIFACT_DIR = "candidate-AN-mt6797-dvfsp-handoff-observer-b30bd183"
AN_RAW_SHA256 = "b30bd1830ac8b6d01a6d030815969c89239a40a742f008338899925508987933"
AN_RAW_SIZE = "7387136"
AN_ARTIFACT_MANIFEST_SHA256 = (
    "5c4210cf657928c8d487fb720ac55ad80bb3b3bfe5afa98018582d2cd667a3e9"
)
AN_PADDED_SHA256 = "1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb"
AN_INSTALLER_SHA256 = (
    "7f86e620aaa2410954ea01d93241d6f8e21f2b94e1811646cbe7f672fa9f052d"
)

PATCH_0094_SHA256 = "2e20664ff4cb08a4f2296bdafb84148d4e4cf79b1eb17b3e92f6a7bb145abe59"
PATCH_0095_SHA256 = "4ac79ec2653e829fef973e85176cc00c7be908983cb5261d940b3395332ae764"
PATCH_0097_SHA256 = "11b5fb7c0cf8ef034fa3e1db706d05e3bab7f5aeade0d7592a2213ed7e3ac910"
PATCH_0098_SHA256 = "260f84c885d9f25524162ab097f1377137b55b5461af2b429d4508f1cfe58748"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"

BOOT_MEMBER = "gemini-mt6797-dvfsp-handoff-owner.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-dvfsp-handoff-owner.dtb"
INITRAMFS_MEMBER = "gemini-dvfsp-handoff-owner-initramfs.img"
ARTIFACT_PREFIX = "candidate-AO-mt6797-dvfsp-handoff-owner-"
BOOT2_SIZE = 16 * 1024 * 1024

# Pinned only after two independent packages and assembled artifacts compared.
FINAL_DTB_SHA256 = "de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7"
IMAGE_GZ_SHA256 = "f077c0196cdf0678671f5672beb41bef698626d9c9b6be9720d7f1a56e9ffc05"
SYSTEM_MAP_SHA256 = "6f34cb0c656569777932e45aae9c895234c4b8acf5f7fd2a425bd7aae9badadf"
CONFIG_SHA256 = "4aab63bad14a689a450395de0c33636ee2946df79a9df3b7993f5db4da5b8318"
SOURCE_BUILD_SHA256 = "0a414ce1e25414e6001fbc81046ff799bcb88d259fd224634a136768a15dd5ce"
RAW_SHA256 = "44fc1e6a74744ce546f86f47cfdc7a25f23b134ac59da902f8ac302033875c66"
RAW_SIZE = "7387136"
ARTIFACT_MANIFEST_SHA256 = (
    "6e8eb261d0a59807d20a605626c3ef8aff5799ac4f61494f77d6210be15acf85"
)
PADDED_SHA256 = "3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb"

HEX256 = re.compile(r"^[0-9a-f]{64}$")


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


def artifact_pin_state() -> str:
    values = (
        FINAL_DTB_SHA256,
        IMAGE_GZ_SHA256,
        SYSTEM_MAP_SHA256,
        CONFIG_SHA256,
        SOURCE_BUILD_SHA256,
        RAW_SHA256,
        RAW_SIZE,
        ARTIFACT_MANIFEST_SHA256,
        PADDED_SHA256,
    )
    unresolved = [value.startswith("TO_PIN_") for value in values]
    if all(unresolved):
        return "ready-to-pin"
    if any(unresolved):
        raise ValueError("Candidate AO artifact calibration is only partially pinned")
    require_artifact_pins()
    return "source-pinned"


def require_artifact_pins() -> None:
    hashes = {
        "FINAL_DTB_SHA256": FINAL_DTB_SHA256,
        "IMAGE_GZ_SHA256": IMAGE_GZ_SHA256,
        "SYSTEM_MAP_SHA256": SYSTEM_MAP_SHA256,
        "CONFIG_SHA256": CONFIG_SHA256,
        "SOURCE_BUILD_SHA256": SOURCE_BUILD_SHA256,
        "RAW_SHA256": RAW_SHA256,
        "ARTIFACT_MANIFEST_SHA256": ARTIFACT_MANIFEST_SHA256,
        "PADDED_SHA256": PADDED_SHA256,
    }
    for name, value in hashes.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate AO {name} is unresolved or malformed")
    if not RAW_SIZE.isdecimal() or not 0 < int(RAW_SIZE) <= BOOT2_SIZE:
        raise ValueError("Candidate AO RAW_SIZE is unresolved or malformed")
    if RAW_SHA256 in {AH_RAW_SHA256, AN_RAW_SHA256}:
        raise ValueError("Candidate AO raw identity equals a predecessor")
    if PADDED_SHA256 == AN_PADDED_SHA256:
        raise ValueError("Candidate AO padded identity equals Candidate AN")
