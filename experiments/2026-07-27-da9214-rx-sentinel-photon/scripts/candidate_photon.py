"""Pinned identities and safety boundaries for Candidate Photon."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-27-da9214-rx-sentinel-photon"
CANDIDATE = "Photon"
REVISION = "r2"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-i2cdev-cassini"
)
SERIES = "patches/series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve"

CASSINI_ARTIFACT_DIR = "candidate-Cassini-da9214-direct-address-e02e2673"
CASSINI_MANIFEST_SHA256 = (
    "0d1a954827f5ebd31abc12b4d0a207105c5e270403a9b3a66cbd70626e5b2306"
)
CASSINI_BOOT_MEMBER = "gemini-mt6797-da9214-cassini.boot.img"
CASSINI_BOOT_SHA256 = (
    "e02e2673ca054d3e4081f5234d26a394617777e8496417fd75196a948d55fa4d"
)
CASSINI_BOOT_SIZE = 7_645_184
CASSINI_PADDED_SHA256 = (
    "febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1"
)
CASSINI_DTB_MEMBER = "mt6797-gemini-pda-da9214-cassini.dtb"
CASSINI_DTB_SHA256 = (
    "8faee2918ce72b08907affa73bfbaf1c5bbbffafde0f4f4c2693977468291768"
)
CASSINI_INITRAMFS_MEMBER = "gemini-da9214-cassini-initramfs.img"
CASSINI_INITRAMFS_SHA256 = (
    "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
)
CASSINI_IMAGE_GZ_SHA256 = (
    "3e9eeb5a2d28f857a1bd25dca8f033f0a19f854a0c8e1839a98bb1aba0df06dc"
)
CASSINI_SYSTEM_MAP_SHA256 = (
    "ea78ced1f70b98803058289bd1cd701c699d41e025713a0a0acc4f6ef99f4052"
)
CASSINI_CONFIG_SHA256 = (
    "83c85429cdcb7d66cb96df2c9005456afd67fc5c7dbfe5d76e9879bf45c1759b"
)
CASSINI_SOURCE_BUILD_SHA256 = (
    "219f3e15ac0df1277d6de4cb3e97ebc605afdb2da9b3170ab4b7888eab0dead4"
)
CASSINI_KERNEL_FIELD_SHA256 = (
    "9bdda4ae8a20ad215fc53bd3ef3e8c6c5e92171e3e6613415f460bc22f63f85c"
)
CASSINI_KERNEL_FIELD_SIZE = 5_566_892
CASSINI_RAMDISK_OFFSET = 5_570_560

# Installed and full-readback-verified but deliberately unbooted Photon r0.
PHOTON_R0_SOURCE_SHA256 = (
    "6beb3d04ad29429f53d22c48e0c1821059822d16a73a2b26907094df8cb0c60c"
)
PHOTON_R0_PROBE_BINARY_SHA256 = (
    "aca14971f9286e5dfd220e9aca4890c9d3822e067954878c31babb6a20058b52"
)
PHOTON_R0_INITRAMFS_SHA256 = (
    "f4649af93e93064d4dfb450e5d0a56d39a03c8409d00918cb871c7f7533e3084"
)
PHOTON_R0_RAW_SHA256 = (
    "b69f8b399a73861f06b7318d335d1def8f8cc2a16e953fdab97238894e4a2ef4"
)
PHOTON_R0_PADDED_SHA256 = (
    "5c044fc3d2ccecf399d6ccb058f354b43e9d14b3fb98f9eb448016ab7f9e8e04"
)
PHOTON_R0_MANIFEST_SHA256 = (
    "b75ccd98dc6c0ce8934c837c582b76503a85ee32eb4f2e1257594eb9fb7e1b53"
)

# Reproduced but deliberately uninstalled and unbooted Photon r1. Its paired
# control flow was correct, but the output vocabulary overclaimed overwrite
# causality where it had observed only post-byte differences from prefills.
PHOTON_R1_SOURCE_SHA256 = (
    "e4c59607d7cd2f63cac9e4ec9931672a9bdaf2c352e8757d4a7cb87ab425a87b"
)
PHOTON_R1_PROBE_BINARY_SHA256 = (
    "2a224fd1fd5575bc411b498ee6c671845d4945d93d3deaefeacb600daa0101bb"
)
PHOTON_R1_INITRAMFS_SHA256 = (
    "91992207671fdf2bbf0f40fd1fa4b5f83f9a03bc08aead48a6f8c92677a5becb"
)
PHOTON_R1_RAW_SHA256 = (
    "005228ce67698445091869b8e9d248fd610e5f3ee28251a7e385398306fba97b"
)
PHOTON_R1_PADDED_SHA256 = (
    "4c0a46960b1956aae2800e44e8e8064869f4a12fb8c96e30e03d6acf21aa2c1b"
)
PHOTON_R1_MANIFEST_SHA256 = (
    "ca903f26248faf0dd688c8e386cdc2bba0be0901c422f21299077b19e2e3db63"
)
PHOTON_R1_INSTALLER_SHA256 = (
    "5df8304e93ffef893488a8449e15cda76d9c8ab0968f64db96fcbe247815659a"
)

PROBE_SOURCE_SHA256 = (
    "029fbe15270eada880e3ac74d73de20029743b06fffa44f7fa7b75f105cad62b"
)
BOOT_MEMBER = "gemini-mt6797-da9214-photon.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-da9214-photon.dtb"
INITRAMFS_MEMBER = "gemini-da9214-photon-initramfs.img"
PROBE_MEMBER = "photon-probe"
EMBEDDED_PROBE_MEMBER = "bin/cassini-probe"
ARTIFACT_PREFIX = "candidate-Photon-r2-da9214-rx-sentinel-"

BOOT_NAME = "gemini-cassini"
BOOT_CMDLINE = "bootopt=64S3,32N2,64N2"
BOOT_PAGE_SIZE = 2048
BOOT2_SIZE = 16 * 1024 * 1024
SERIALIZER_SHA256 = (
    "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
)
ANALYZER_SHA256 = (
    "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
)
CASSINI_INITRAMFS_VALIDATOR_SHA256 = (
    "9e0ec3a6d9d1b9cd6f4ca63161d05ef398ebf964ff4de777e4babf37c628539f"
)
CASSINI_DERIVER_SHA256 = (
    "789e509544d5d26a82bd7d606a2dc5ec4939e9a5c36ff497987d026c57715112"
)

# Calibrated only after two independent complete Candidate Photon r2 trees
# reproduced. Installed-but-unbooted r0 and uninstalled r1 are pinned above.
PROBE_BINARY_SHA256 = (
    "b36cefe50227f8fe6a838cba0c8757279dcd0766b804afa77de5518c263cbdf4"
)
INITRAMFS_SHA256 = (
    "6269c04ae5fc29f77986e774faa3b667351357dace98420882e0f5d86ca9c77f"
)
RAW_SHA256 = (
    "75b9081c013408c2358ec3c4cafcf7381294c22215432add98739f72033e8ad6"
)
RAW_SIZE = "7647232"
PADDED_SHA256 = (
    "0ffe1ee750ff219c9ee6f9d4809ecb8748bdd2a35ba63d68a99b3d74e599c2f7"
)
ARTIFACT_MANIFEST_SHA256 = (
    "5b036d5234ab8d27eddcf152f44d5627de2ba669cb0571491f186cd977f2a551"
)
INSTALLER_SHA256 = (
    "6d98d9a807687567f91513466587ce2b644e5935f841292205fd4a3d25820d5c"
)

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
        "PROBE_BINARY_SHA256": PROBE_BINARY_SHA256,
        "INITRAMFS_SHA256": INITRAMFS_SHA256,
        "RAW_SHA256": RAW_SHA256,
        "PADDED_SHA256": PADDED_SHA256,
        "ARTIFACT_MANIFEST_SHA256": ARTIFACT_MANIFEST_SHA256,
    }
    for name, value in hashes.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Photon {name} is unresolved or malformed")
    if not RAW_SIZE.isdecimal() or not 0 < int(RAW_SIZE) <= BOOT2_SIZE:
        raise ValueError("Candidate Photon RAW_SIZE is unresolved or malformed")
    if PADDED_SHA256 == CASSINI_PADDED_SHA256:
        raise ValueError("Photon padded identity equals Cassini")
