"""Pinned inputs and safety boundaries for Candidate Quasar."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-27-mt6797-i2c6-quasar"
CANDIDATE = "Quasar"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-quasar"
)
SERIES = "patches/series-quasar-i2c6-native-fifo"
SERIES_SHA256 = "4a50d98812c5f1f21298e3114b1bfa99e4f8435ba544706e4ee1a83d0babb72d"
CONFIG_FRAGMENT = "configs/gemini-i2c6-quasar.fragment"
CONFIG_FRAGMENT_SHA256 = (
    "dc93e8c65a46b5474bb9135eca64eb71ffd48e4a3ab6db2e09808c8483e8ba38"
)

ORION_PATCHES = (
    "v7.1.3/0114-dt-bindings-i2c-mediatek-add-MT6797-iDVFS-controller.patch",
    "v7.1.3/0115-i2c-mediatek-support-MT6797-iDVFS-transfer-format.patch",
    "v7.1.3/0116-arm64-dts-mediatek-identify-Gemini-I2C6-iDVFS-block.patch",
    "v7.1.3/0117-i2c-mediatek-add-fixed-Orion-I2C6-diagnostic.patch",
)
ORION_PATCH_SHA256 = (
    "a07b01ef74b034e92d591e4e65045ed47cde6ad44ee79faa19e4d4f93f1706d3",
    "f273374f16aba3125b83973d207a94998639cf90a63bf26955de1460c7a59845",
    "e480cd51743be1b57ef6f5c021fd29fae1a386c8254f0299b1c40d564f3500c7",
    "d3e98aca8a95b68ebd6b4558200e8af12b61ae16b71ca745af0e3a1b294d9188",
)
VEGA_PATCH = (
    "v7.1.3/0118-i2c-mediatek-fix-Orion-I2C6-node-identity-check.patch"
)
VEGA_PATCH_SHA256 = (
    "a1fc1a02ca7f45deab52acbef3e433b193b2846f8bb84250b8a03cb33d1595e3"
)
QUASAR_PATCH = (
    "v7.1.3/0119-i2c-mediatek-add-fixed-Quasar-native-path-canary.patch"
)
QUASAR_PATCH_SHA256 = (
    "35a928b92004b0445e2e2001406a2e13768f0a937c2fab1611a85a03f753baaf"
)
QUASAR_PATCHES = ORION_PATCHES + (VEGA_PATCH, QUASAR_PATCH)
QUASAR_PATCH_SHA256S = ORION_PATCH_SHA256 + (
    VEGA_PATCH_SHA256,
    QUASAR_PATCH_SHA256,
)

# Exact pre-Orion compiled-DT baseline and exact Orion/Vega compiled DT.
CASSINI_PACKAGE_DIR = (
    "linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-"
    "manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-"
    "owner-i2c6-consumer-ap-dma-preserve-i2cdev-cassini-"
    "9b31918e-f2429dc6"
)
CASSINI_PROVENANCE_SHA256 = (
    "219f3e15ac0df1277d6de4cb3e97ebc605afdb2da9b3170ab4b7888eab0dead4"
)
CASSINI_COMPILED_DTB_SHA256 = (
    "bf17ba0461512f8d638a79ca1705582e375314445cc1698ac11242dbc6122657"
)
ORION_COMPILED_DTB_SHA256 = (
    "0a2aa671dd17e9daf5ce5e3de3d92917129ce639a0a02e0a5041ecf3e3441168"
)
CASSINI_PACKAGE_VALIDATOR_SHA256 = (
    "ca1f44c9b73e4ff831c848c36d2081be758f3b9eb933942f3de7e9d7a5e7cc0a"
)
CASSINI_PINS_SHA256 = (
    "88420754f4ea2aad64cf4e6c71462669d0dd8a24f706c2160452bf08bba9d804"
)
ORION_DTB_VALIDATOR_SHA256 = (
    "99670c0bcde91e26d59139448c762e1a8348556074928da3ff5e17c89c9b74eb"
)
ORION_DTB_BUILDER_SHA256 = (
    "f2faf16cc87483711a09d6c1d8ba3dfea4a350ebaee20575d3d8cd426db3c864"
)
DTB_LINEAGE_VALIDATOR_SHA256 = (
    "92997fbfecd82384556c9ab01bcb41cebd9609202f9d7a3fa13fcb172b83724e"
)

# Quasar deliberately retains the exact hardware-passed Hubble
# serviceability payload and exact Orion/Vega Hubble-derived boot DT.
HUBBLE_ARTIFACT_DIR = "candidate-Hubble-cassini-rollback-e02e2673"
HUBBLE_MANIFEST_SHA256 = (
    "0d1a954827f5ebd31abc12b4d0a207105c5e270403a9b3a66cbd70626e5b2306"
)
HUBBLE_RAW_SHA256 = (
    "e02e2673ca054d3e4081f5234d26a394617777e8496417fd75196a948d55fa4d"
)
HUBBLE_RAW_SIZE = 7_645_184
HUBBLE_PADDED_SHA256 = (
    "febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1"
)
HUBBLE_BOOT_MEMBER = "gemini-mt6797-da9214-cassini.boot.img"
HUBBLE_DTB_MEMBER = "mt6797-gemini-pda-da9214-cassini.dtb"
HUBBLE_DTB_SHA256 = (
    "8faee2918ce72b08907affa73bfbaf1c5bbbffafde0f4f4c2693977468291768"
)
ORION_BOOT_DTB_SHA256 = (
    "e189b4741806432af456a2f9a4aa7e250f3e629dcad41726bf221bf2611ccae7"
)
HUBBLE_INITRAMFS_MEMBER = "gemini-da9214-cassini-initramfs.img"
HUBBLE_INITRAMFS_SHA256 = (
    "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
)
HUBBLE_VALIDATOR_SHA256 = (
    "bdae711e7c0ecf9e3957e1a1a3e259b843813247848410edf0a88939b64dc5de"
)
HUBBLE_PINS_SHA256 = (
    "1e1775a833974e53ab057893fd5b9ec45e026818471533bc7f077479b3dd6213"
)

SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
NORMALIZER_SHA256 = "242c9ebe9d9745f5f5c62926e322201e633ec2adfbbf7913e4fbb0effea94ce8"

BOOT_MEMBER = "gemini-mt6797-i2c6-quasar.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-i2c6-quasar.dtb"
INITRAMFS_MEMBER = HUBBLE_INITRAMFS_MEMBER
PADDED_MEMBER = "boot2-padded.img"
ARTIFACT_PREFIX = "candidate-Quasar-mt6797-i2c6-"
BOOT2_SIZE = 16 * 1024 * 1024
I2C6_PATH = "/i2c@1100e000"
I2C6_COMPATIBLE = ("mediatek,mt6797-idvfs-i2c",)
PASSES = 2
REGISTERS = (0x05, 0x06, 0x47)
EXPECTED = (0xD9, 0xD0, 0xC0)
PREFILLS = (0xA5, 0x5A, 0x3C, 0x96, 0x69, 0xC3)

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


def require_input_pins() -> None:
    hashes = {
        "SERIES_SHA256": SERIES_SHA256,
        "CONFIG_FRAGMENT_SHA256": CONFIG_FRAGMENT_SHA256,
        "HUBBLE_MANIFEST_SHA256": HUBBLE_MANIFEST_SHA256,
        "HUBBLE_RAW_SHA256": HUBBLE_RAW_SHA256,
        "HUBBLE_PADDED_SHA256": HUBBLE_PADDED_SHA256,
        "HUBBLE_DTB_SHA256": HUBBLE_DTB_SHA256,
        "ORION_BOOT_DTB_SHA256": ORION_BOOT_DTB_SHA256,
        "HUBBLE_INITRAMFS_SHA256": HUBBLE_INITRAMFS_SHA256,
        "HUBBLE_VALIDATOR_SHA256": HUBBLE_VALIDATOR_SHA256,
        "HUBBLE_PINS_SHA256": HUBBLE_PINS_SHA256,
        "SERIALIZER_SHA256": SERIALIZER_SHA256,
        "ANALYZER_SHA256": ANALYZER_SHA256,
        "NORMALIZER_SHA256": NORMALIZER_SHA256,
        "CASSINI_PROVENANCE_SHA256": CASSINI_PROVENANCE_SHA256,
        "CASSINI_COMPILED_DTB_SHA256": CASSINI_COMPILED_DTB_SHA256,
        "ORION_COMPILED_DTB_SHA256": ORION_COMPILED_DTB_SHA256,
        "CASSINI_PACKAGE_VALIDATOR_SHA256": CASSINI_PACKAGE_VALIDATOR_SHA256,
        "CASSINI_PINS_SHA256": CASSINI_PINS_SHA256,
        "ORION_DTB_VALIDATOR_SHA256": ORION_DTB_VALIDATOR_SHA256,
        "ORION_DTB_BUILDER_SHA256": ORION_DTB_BUILDER_SHA256,
        "DTB_LINEAGE_VALIDATOR_SHA256": DTB_LINEAGE_VALIDATOR_SHA256,
    }
    hashes.update(
        {
            f"QUASAR_PATCH_SHA256S[{index}]": value
            for index, value in enumerate(QUASAR_PATCH_SHA256S)
        }
    )
    for name, value in hashes.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Quasar {name} is uncalibrated or malformed")
    if len(QUASAR_PATCHES) != len(QUASAR_PATCH_SHA256S):
        raise ValueError("Candidate Quasar patch-pin inventory is inconsistent")
    if not 0 < HUBBLE_RAW_SIZE < BOOT2_SIZE:
        raise ValueError("Candidate Quasar Hubble raw size is invalid")
