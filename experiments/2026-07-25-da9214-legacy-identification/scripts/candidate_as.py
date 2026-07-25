#!/usr/bin/env python3
"""Pinned identities for storage-inert Candidate AS."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-25-da9214-legacy-identification"
CANDIDATE = "AS"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-da9214-legacy-readonly"
)
PM_AUDIT_PROFILE = PROFILE + "-pm-audit"

AO_ARTIFACT_DIR = "candidate-AO-mt6797-dvfsp-handoff-owner-44fc1e6a"
AO_BOOT_MEMBER = "gemini-mt6797-dvfsp-handoff-owner.boot.img"
AO_DTB_MEMBER = "mt6797-gemini-pda-dvfsp-handoff-owner.dtb"
AO_INITRAMFS_MEMBER = "gemini-dvfsp-handoff-owner-initramfs.img"
AO_MANIFEST_SHA256 = "6e8eb261d0a59807d20a605626c3ef8aff5799ac4f61494f77d6210be15acf85"
AO_RAW_SHA256 = "44fc1e6a74744ce546f86f47cfdc7a25f23b134ac59da902f8ac302033875c66"
AO_RAW_SIZE = "7387136"
AO_DTB_SHA256 = "de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7"
AO_CONFIG_SHA256 = "4aab63bad14a689a450395de0c33636ee2946df79a9df3b7993f5db4da5b8318"
AO_PADDED_SHA256 = "3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb"
AO_INSTALLER_SHA256 = "cbb6b8da36ec7f6a48726b9e5304667068719bd406e9df642376b98c0e6bd730"
INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"

PATCH_0094_SHA256 = "2e20664ff4cb08a4f2296bdafb84148d4e4cf79b1eb17b3e92f6a7bb145abe59"
PATCH_0095_SHA256 = "4ac79ec2653e829fef973e85176cc00c7be908983cb5261d940b3395332ae764"
PATCH_0097_SHA256 = "11b5fb7c0cf8ef034fa3e1db706d05e3bab7f5aeade0d7592a2213ed7e3ac910"
PATCH_0098_SHA256 = "260f84c885d9f25524162ab097f1377137b55b5461af2b429d4508f1cfe58748"
PATCH_0099_SHA256 = "11c6f09cdc02bfcf82a20946af40ef05e935f8679a34a01e6145728e8420115f"
PATCH_0100_SHA256 = "c3b1f67ef13a8b694af2d7e99b57bea68928b1e25f94898b4137cc1a629a7313"
PATCH_0101_SHA256 = "f2427527f16b75c9abd4578d1a235278e7ac1ac7311ed9e68803e5ac395487aa"
PATCH_0102_SHA256 = "b18ed3111ca3035180b4ce5b45556618c0a8295a471c0c5b11caf114be677094"
PATCH_0103_SHA256 = "fd9311de9614a8ccef404cc821785f95b651983078be42e4903834c322d747b2"
PATCH_0096_SHA256 = "dae5933e959ee220aea8cd9e950236ac7967cd5a8cfe04b4ee21220c53712df6"
PATCH_0104_SHA256 = "c38231bf3508861acf62941ad979f3884e3105300d46df433b886c50908a8c50"
PATCH_0105_SHA256 = "44ed34468b82915245e8e58f0af7f8ea5a6b0478d7ab2afefc8224a42f9f277c"
PATCH_0106_SHA256 = "b04776c58b02ebf2c59206710ab9ef8bc1b3f1ae953db3a1a47b296c2c9f7192"
PATCH_0107_SHA256 = "3d99ff3c874e28e03ae696473d89759928a324d5c51b38abc485118648c4c842"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
COMPILED_HANDOFF_AUDITOR_SHA256 = (
    "0510f0695e3a5fe0045da15cc5b839c7de1779d249938edf72778273144b2341"
)

BOOT_MEMBER = "gemini-mt6797-da9214-legacy-identification.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-da9214-legacy-identification.dtb"
INITRAMFS_MEMBER = "gemini-da9214-legacy-identification-initramfs.img"
ARTIFACT_PREFIX = "candidate-AS-da9214-legacy-identification-"
BOOT2_SIZE = 16 * 1024 * 1024

# Pinned after two independent packages and assembled artifacts compared.
FINAL_DTB_SHA256 = "e51891c839ab5e40e591346cb78ac66f1c5e0179a1cc30c4a33acf0b9c0667f7"
IMAGE_GZ_SHA256 = "83b4ad9aa70881e5ca0af08224234c196730b18dde7f2f25aca7769153ad4696"
SYSTEM_MAP_SHA256 = "7f25faf9572b84a3c3cb5a26d8c8b540280f93e22144ce3d5be00f1024ba1ac1"
CONFIG_SHA256 = "af4e641b24915e64b6cc045b207e8f665c55cd6314d29e37be8784c9d2f513c0"
SOURCE_BUILD_SHA256 = "70eb1f53faa3a37682d924bdf70a2648b4fef595df66040fc9fad0bb16476a71"
RAW_SHA256 = "7b090b7d7081df20f74f37a46dcfa2cc177e3f92adf2a3465d8b983582c1a4d4"
RAW_SIZE = "7393280"
ARTIFACT_MANIFEST_SHA256 = "571df4d781b5d477d545e0b4fea02df5ac32657f88f8efe288607201c7ae4c10"
PADDED_SHA256 = "82a5248120ad3201d95e25c1604e45e450e61230db7d8c8b3ec4238a22183aa0"

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
        raise ValueError("Candidate AS artifact calibration is only partially pinned")
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
            raise ValueError(f"Candidate AS {name} is unresolved or malformed")
    if not RAW_SIZE.isdecimal() or not 0 < int(RAW_SIZE) <= BOOT2_SIZE:
        raise ValueError("Candidate AS RAW_SIZE is unresolved or malformed")
    if RAW_SHA256 == AO_RAW_SHA256:
        raise ValueError("Candidate AS raw identity equals a predecessor")
    if PADDED_SHA256 == AO_PADDED_SHA256:
        raise ValueError("Candidate AS padded identity equals Candidate AO")
