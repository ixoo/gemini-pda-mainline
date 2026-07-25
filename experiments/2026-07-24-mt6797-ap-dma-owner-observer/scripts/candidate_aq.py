#!/usr/bin/env python3
"""Pinned identities for the AP_DMA clock-observer candidate."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat

EXPERIMENT = "2026-07-24-mt6797-ap-dma-owner-observer"
CANDIDATE = "AQ"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-ap-dma-observer"
)
AO_ARTIFACT_DIR = "candidate-AO-mt6797-dvfsp-handoff-owner-44fc1e6a"
AO_DTB_MEMBER = "mt6797-gemini-pda-dvfsp-handoff-owner.dtb"
AO_INITRAMFS_MEMBER = "gemini-dvfsp-handoff-owner-initramfs.img"
AO_MANIFEST_SHA256 = "6e8eb261d0a59807d20a605626c3ef8aff5799ac4f61494f77d6210be15acf85"
AO_DTB_SHA256 = "de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7"
AO_INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
AO_KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
AO_PADDED_SHA256 = "3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb"
AO_INSTALLER_SHA256 = "3504a5b591ad4b952c577b5ecb08eaedac5027c97431152023a2d28afef7b937"
AP_PADDED_SHA256 = "602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9"
AP_DERIVER_SHA256 = "a20198cb8e5cc8804a2fa218f9187ff30ab8cfac6e370a4f6792b86ba632918e"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
BOOT_MEMBER = "gemini-mt6797-dvfsp-ap-dma-owner-observer.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-ap-dma-owner-observer.dtb"
INITRAMFS_MEMBER = "gemini-ap-dma-owner-observer-initramfs.img"
ARTIFACT_PREFIX = "candidate-AQ-mt6797-ap-dma-owner-observer-"
BOOT2_SIZE = 16 * 1024 * 1024

FINAL_DTB_SHA256 = "de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7"
IMAGE_GZ_SHA256 = "428fcc0cd028f3f7854baab2aca3e4927b7fc4c483651f069b124001b2753c02"
SYSTEM_MAP_SHA256 = "8693c3d2c867be57138450a98609c0fd6132aa2ac5dde801c18601c10820e6ee"
CONFIG_SHA256 = "550ab140e8748aef36da1f02e56bc774b3296dba3648f9013679caedb31e216b"
SOURCE_BUILD_SHA256 = "2f15082fd4e8564deb74210da7b34776f58a3c03afd6edf6448ab2bd67a3bf88"
INITRAMFS_SHA256 = "c3d4b1fb7ef8bd14f0c99de3c89b3997fea78c97cb98bf10490e63d1813f95e1"
RAW_SHA256 = "96633efeb1c6197017cb6e03064ecd3a812b37d4c685244513c3930f638b6970"
RAW_SIZE = "7489536"
ARTIFACT_MANIFEST_SHA256 = "3aeca7a2ee5016ae593260efd1d407ecb15053547261e4fe9c34860a3fe99efc"
PADDED_SHA256 = "4ad3f29c07a243108f50f3a70049336b116fed80dcb694b2d9e0f872591255c4"
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest_path(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def require_artifact_pins() -> None:
    values = {
        "IMAGE_GZ_SHA256": IMAGE_GZ_SHA256,
        "SYSTEM_MAP_SHA256": SYSTEM_MAP_SHA256,
        "CONFIG_SHA256": CONFIG_SHA256,
        "SOURCE_BUILD_SHA256": SOURCE_BUILD_SHA256,
        "INITRAMFS_SHA256": INITRAMFS_SHA256,
        "RAW_SHA256": RAW_SHA256,
        "ARTIFACT_MANIFEST_SHA256": ARTIFACT_MANIFEST_SHA256,
        "PADDED_SHA256": PADDED_SHA256,
    }
    if any(value.startswith("TO_PIN_") for value in values.values()):
        raise ValueError("Candidate AQ artifact calibration is unresolved")
    for name, value in values.items():
        if name != "RAW_SIZE" and HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate AQ {name} is malformed")
    if not RAW_SIZE.isdecimal() or not 0 < int(RAW_SIZE) <= BOOT2_SIZE:
        raise ValueError("Candidate AQ raw size is malformed")
    if RAW_SHA256 in {AO_PADDED_SHA256, AP_PADDED_SHA256}:
        raise ValueError("Candidate AQ raw identity equals a predecessor")
