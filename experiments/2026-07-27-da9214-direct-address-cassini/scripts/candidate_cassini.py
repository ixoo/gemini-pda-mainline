"""Pinned identities and safety boundaries for Candidate Cassini."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-27-da9214-direct-address-cassini"
CANDIDATE = "Cassini"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-i2cdev-cassini"
)
SERIES = "patches/series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve"
SERIES_SHA256 = "d851036118c3858c8e800d214c6fc7393e18ca6241fa6a6bff1fd31df184c32a"
CONFIG_FRAGMENT = "configs/gemini-da9214-cassini.fragment"
CONFIG_FRAGMENT_SHA256 = (
    "cf8f32294e98dc2027fd9d033c83de8f5e4447a36e0defd13ea989bb368615d2"
)

AO_ARTIFACT_DIR = "candidate-AO-mt6797-dvfsp-handoff-owner-44fc1e6a"
AO_BOOT_MEMBER = "gemini-mt6797-dvfsp-handoff-owner.boot.img"
AO_DTB_MEMBER = "mt6797-gemini-pda-dvfsp-handoff-owner.dtb"
AO_INITRAMFS_MEMBER = "gemini-dvfsp-handoff-owner-initramfs.img"
AO_MANIFEST_SHA256 = "6e8eb261d0a59807d20a605626c3ef8aff5799ac4f61494f77d6210be15acf85"
AO_RAW_SHA256 = "44fc1e6a74744ce546f86f47cfdc7a25f23b134ac59da902f8ac302033875c66"
AO_RAW_SIZE = "7387136"
AO_DTB_SHA256 = "de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7"
AO_INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
AO_KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
AO_PADDED_SHA256 = "3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb"
AO_INSTALLER_SHA256 = "cbb6b8da36ec7f6a48726b9e5304667068719bd406e9df642376b98c0e6bd730"

PIONEER_PADDED_SHA256 = (
    "c02244700fcd41a9b6a2d70e90ae2b83276f9dcdd843329643a3d9ced454779d"
)
FINAL_DTB_SHA256 = "8faee2918ce72b08907affa73bfbaf1c5bbbffafde0f4f4c2693977468291768"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
NORMALIZER_SHA256 = "242c9ebe9d9745f5f5c62926e322201e633ec2adfbbf7913e4fbb0effea94ce8"
AP_DTB_VALIDATOR_SHA256 = (
    "0f270da5901588bfe79f565779e301563fc37c67fc8c38605d51d9714f322165"
)

PROBE_SOURCE_SHA256 = "18a9609421d870566d3e8891ffbc902077ac7ac5f5aee9069071d2a573cfb016"
BOOT_MEMBER = "gemini-mt6797-da9214-cassini.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-da9214-cassini.dtb"
INITRAMFS_MEMBER = "gemini-da9214-cassini-initramfs.img"
PROBE_MEMBER = "cassini-probe"
ARTIFACT_PREFIX = "candidate-Cassini-da9214-direct-address-"
BOOT2_SIZE = 16 * 1024 * 1024

# Calibrate only after two independent packages and complete candidate trees
# reproduce. The installer deriver refuses every unresolved value.
IMAGE_GZ_SHA256 = "3e9eeb5a2d28f857a1bd25dca8f033f0a19f854a0c8e1839a98bb1aba0df06dc"
SYSTEM_MAP_SHA256 = "ea78ced1f70b98803058289bd1cd701c699d41e025713a0a0acc4f6ef99f4052"
CONFIG_SHA256 = "83c85429cdcb7d66cb96df2c9005456afd67fc5c7dbfe5d76e9879bf45c1759b"
INITRAMFS_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
PROBE_BINARY_SHA256 = "30073f6ea7d0b57d3654ece5c6212da1c94ff4d24514b62d07331136a4efaf0e"
RAW_SHA256 = "e02e2673ca054d3e4081f5234d26a394617777e8496417fd75196a948d55fa4d"
RAW_SIZE = "7645184"
ARTIFACT_MANIFEST_SHA256 = "0d1a954827f5ebd31abc12b4d0a207105c5e270403a9b3a66cbd70626e5b2306"
PADDED_SHA256 = "febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1"

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


def require_artifact_pins() -> None:
    hashes = {
        "IMAGE_GZ_SHA256": IMAGE_GZ_SHA256,
        "SYSTEM_MAP_SHA256": SYSTEM_MAP_SHA256,
        "CONFIG_SHA256": CONFIG_SHA256,
        "INITRAMFS_SHA256": INITRAMFS_SHA256,
        "PROBE_BINARY_SHA256": PROBE_BINARY_SHA256,
        "RAW_SHA256": RAW_SHA256,
        "ARTIFACT_MANIFEST_SHA256": ARTIFACT_MANIFEST_SHA256,
        "PADDED_SHA256": PADDED_SHA256,
    }
    for name, value in hashes.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Cassini {name} is unresolved or malformed")
    if not RAW_SIZE.isdecimal() or not 0 < int(RAW_SIZE) <= BOOT2_SIZE:
        raise ValueError("Candidate Cassini RAW_SIZE is unresolved or malformed")
    if PADDED_SHA256 == PIONEER_PADDED_SHA256:
        raise ValueError("Cassini padded identity equals Pioneer")
