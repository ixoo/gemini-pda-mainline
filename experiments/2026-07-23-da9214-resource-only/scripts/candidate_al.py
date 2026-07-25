#!/usr/bin/env python3
"""Storage-inert identities for Candidate AL's DA9214 resource-only split."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-23-da9214-resource-only"
CANDIDATE = "AL"

AH_ARTIFACT_DIR = "candidate-AH-ad-contract-af-kernel-split-e5ba6ee0"
AH_BOOT_MEMBER = "gemini-ad-contract-af-kernel-split.boot.img"
AH_DTB_MEMBER = "mt6797-gemini-pda-ad-contract-af-kernel-split.dtb"
AH_INITRAMFS_MEMBER = "gemini-ad-contract-af-kernel-split-initramfs.img"
AH_MANIFEST_SHA256 = "04b25bfc5e72645318273e03adc80191df7d52994acc7ade8202a64d95223997"
AH_RAW_SHA256 = "e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197"
AH_RAW_SIZE = 7_385_088
AH_PADDED_SHA256 = "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012"
AH_DTB_SHA256 = "27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845"
IMAGE_GZ_SHA256 = "b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912"
SYSTEM_MAP_SHA256 = "a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d"
CONFIG_SHA256 = "bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63"
SOURCE_BUILD_SHA256 = "57ea75dd81ac7389c6a34d47cf9dc6a7300476f7ad85b00d782190585e686094"
INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"

AK_ARTIFACT_DIR = "candidate-AK-a72-reject-cpu9-e8fd45b4"
AK_BOOT_MEMBER = "gemini-a72-reject-cpu9-request.boot.img"
AK_RAW_SHA256 = "e8fd45b4c6b3626330d49c84b13f6c7147ab5d324422bff5901c35545f5b6d28"
AK_RAW_SIZE = 7_380_992
AK_MANIFEST_SHA256 = "8910caa303b69555fb792d061b19dc0fdb9f25108e55212135e8d099be84c93b"
AK_PADDED_SHA256 = "66902cb2f2faa5c4c6457ce89ff67aa25e5345ac43ee0ca8062a55e0fbac870e"

PATCH_0089_SHA256 = "5626670d4d4b39e8b8e9b1e803bcb9a847068690046531a7132a4dda6936248b"
AH_ARTIFACT_VALIDATOR_SHA256 = "f27498cf6858817ed72d51eac4247a86d575fa4b92eedbc414ec4d2ab2481ef4"
AH_DTB_VALIDATOR_SHA256 = "8dd73ac13d0aa6bd90754ff0061a7c1d0c19f561f7029a6ca6a4dde7fdfcb28f"
AH_BOOT_VALIDATOR_SHA256 = "c78f26c8615f0e778371b157a75d74101736742ca6ebbe62bcafe1f745989e37"
AH_RUNTIME_COLLECTOR_SHA256 = "13f27efd9de671759c900639f9541a3851b6d13aebdddf5270e91f37f044ddd4"
AH_RUNTIME_VALIDATOR_SHA256 = "981c241b76eb7d6b5b8450f755033a0ee109bfb4c05af78318737127b6a55321"
AH_CYCLE_COLLECTOR_SHA256 = "b5664f6d883207af9bcb80c6d731dfc8d568e62d203daa38afc9163ba33ca12a"
AK_IDENTITY_SHA256 = "c52e133767f305045664b2274883e8f145170ee4fd8ae34418b7a14ed42360a0"
AK_DERIVER_SHA256 = "e26859c81e58767aafa28183b3f6ff3d6f6635ee820c7bfabeadf9659d471e0d"
AK_INSTALLER_SHA256 = "771bc1300abf02771fd046083a4eb18ec233dcd06a92c11681633fd8d1149b31"
SERIALIZER_SHA256 = "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"

BOOT_MEMBER = "gemini-da9214-resource-only.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-da9214-resource-only.dtb"
INITRAMFS_MEMBER = "gemini-da9214-resource-only-initramfs.img"
ARTIFACT_PREFIX = "candidate-AL-da9214-resource-only-"
BOOT2_SIZE = 16 * 1024 * 1024
PINCTRL_PHANDLE = 0x2C

# Pinned only after validate-artifact-reproduction.py accepted two
# independently assembled trees. Every device-affecting helper calls
# require_artifact_pins() before inspecting private evidence or probing a host.
FINAL_DTB_SHA256 = "ea80e7a835fee94c7eb985165aaca7d074ab99f0878f9f07f2ef67b0954afea1"
RAW_SHA256 = "a19877ad5f2c5a8515b6f3b64aec9b5bf036820ef35452e3e7009803fa3848da"
RAW_SIZE = "7387136"
ARTIFACT_MANIFEST_SHA256 = "591bc166f1992b5b1152ba87703b61ca5b8cb3f35b5f087af12c27cb47a5e5ba"
PADDED_SHA256 = "5f022a8b4d6ed19a248d21b8cebdbfa2190e86675714eab49adfc57de9a7f794"

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
    values = {
        "FINAL_DTB_SHA256": FINAL_DTB_SHA256,
        "RAW_SHA256": RAW_SHA256,
        "RAW_SIZE": RAW_SIZE,
        "ARTIFACT_MANIFEST_SHA256": ARTIFACT_MANIFEST_SHA256,
        "PADDED_SHA256": PADDED_SHA256,
    }
    unresolved = [name for name, value in values.items() if value.startswith("TO_PIN_")]
    if unresolved:
        raise ValueError(
            "Candidate AL artifact calibration remains unresolved: "
            + ",".join(unresolved)
        )
    for name in (
        "FINAL_DTB_SHA256",
        "RAW_SHA256",
        "ARTIFACT_MANIFEST_SHA256",
        "PADDED_SHA256",
    ):
        if HEX256.fullmatch(values[name]) is None:
            raise ValueError(f"Candidate AL {name} is malformed")
    if not RAW_SIZE.isdecimal() or not 0 < int(RAW_SIZE) <= BOOT2_SIZE:
        raise ValueError("Candidate AL RAW_SIZE is malformed or exceeds boot2")
    if RAW_SHA256 in {AH_RAW_SHA256, AK_RAW_SHA256}:
        raise ValueError("Candidate AL raw identity equals a predecessor")
    if PADDED_SHA256 in {AH_PADDED_SHA256, AK_PADDED_SHA256}:
        raise ValueError("Candidate AL padded identity equals a predecessor")
