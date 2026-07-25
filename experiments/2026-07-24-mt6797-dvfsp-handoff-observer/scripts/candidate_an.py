#!/usr/bin/env python3
"""Pinned identities for the storage-inert Candidate AN observer."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-24-mt6797-dvfsp-handoff-observer"
CANDIDATE = "AN"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-observer"
)

AH_ARTIFACT_DIR = "candidate-AH-ad-contract-af-kernel-split-e5ba6ee0"
AH_DTB_MEMBER = "mt6797-gemini-pda-ad-contract-af-kernel-split.dtb"
AH_INITRAMFS_MEMBER = "gemini-ad-contract-af-kernel-split-initramfs.img"
AH_MANIFEST_SHA256 = "04b25bfc5e72645318273e03adc80191df7d52994acc7ade8202a64d95223997"
AH_RAW_SHA256 = "e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197"
AH_DTB_SHA256 = "27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845"
INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"

AL_ARTIFACT_DIR = "candidate-AL-da9214-resource-only-a19877ad"
AL_RAW_SHA256 = "a19877ad5f2c5a8515b6f3b64aec9b5bf036820ef35452e3e7009803fa3848da"
AL_RAW_SIZE = "7387136"
AL_ARTIFACT_MANIFEST_SHA256 = (
    "591bc166f1992b5b1152ba87703b61ca5b8cb3f35b5f087af12c27cb47a5e5ba"
)
AL_PADDED_SHA256 = "5f022a8b4d6ed19a248d21b8cebdbfa2190e86675714eab49adfc57de9a7f794"

PATCH_0094_SHA256 = "2e20664ff4cb08a4f2296bdafb84148d4e4cf79b1eb17b3e92f6a7bb145abe59"
PATCH_0095_SHA256 = "4ac79ec2653e829fef973e85176cc00c7be908983cb5261d940b3395332ae764"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"

BOOT_MEMBER = "gemini-mt6797-dvfsp-handoff-observer.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-dvfsp-handoff-observer.dtb"
INITRAMFS_MEMBER = "gemini-dvfsp-handoff-observer-initramfs.img"
ARTIFACT_PREFIX = "candidate-AN-mt6797-dvfsp-handoff-observer-"
BOOT2_SIZE = 16 * 1024 * 1024

# The final-DT identity is deterministic and already reproduced from the exact
# hardware-passed Candidate AH final DT.
FINAL_DTB_SHA256 = "1a934e999c288459089e33ef19ec2bd2105b1de6cf5d808b08ba4569601a924b"

# Pin these only after validate-package-reproduction.py and
# validate-artifact-reproduction.py accept two independent trees.
IMAGE_GZ_SHA256 = "ade304261204b328c4c26f99964aa46c9a2456de5e14f1598cf26c6c71684815"
SYSTEM_MAP_SHA256 = "dfb8fb97f403379991de6c07f04fe24936b0fea391bdd65efea421589c202383"
CONFIG_SHA256 = "5c3a9537ce91de3c58039974c5671a091a59cf685b659c7298142751e4294bc5"
SOURCE_BUILD_SHA256 = (
    "9addea0158420a5114ea689eecdaf701cccc18479b072b601f769df134fbea38"
)
RAW_SHA256 = "b30bd1830ac8b6d01a6d030815969c89239a40a742f008338899925508987933"
RAW_SIZE = "7387136"
ARTIFACT_MANIFEST_SHA256 = (
    "5c4210cf657928c8d487fb720ac55ad80bb3b3bfe5afa98018582d2cd667a3e9"
)
PADDED_SHA256 = "1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb"

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
        raise ValueError("Candidate AN artifact calibration is only partially pinned")
    require_artifact_pins()
    return "source-pinned"


def require_artifact_pins() -> None:
    hashes = {
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
            raise ValueError(f"Candidate AN {name} is unresolved or malformed")
    if not RAW_SIZE.isdecimal() or not 0 < int(RAW_SIZE) <= BOOT2_SIZE:
        raise ValueError("Candidate AN RAW_SIZE is unresolved or malformed")
    if RAW_SHA256 in {AH_RAW_SHA256, AL_RAW_SHA256}:
        raise ValueError("Candidate AN raw identity equals a predecessor")
    if PADDED_SHA256 == AL_PADDED_SHA256:
        raise ValueError("Candidate AN padded identity equals Candidate AL")
