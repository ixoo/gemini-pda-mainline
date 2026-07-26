"""Pinned identities for the PMIC-wrapper eMMC probe candidate AW.

The common AO inputs and source pins remain inherited from ``candidate_emmc``;
only the candidate label and newly assembled artifact identities differ.
"""

from __future__ import annotations

import re

from candidate_emmc import *  # noqa: F401,F403 - retain the exact AO contract
import candidate_emmc as _base


CANDIDATE = "AW"
ARTIFACT_PREFIX = "candidate-AW-emmc-pmic-wrap-"

# The initramfs and final DT are intentionally unchanged from AV. The kernel
# package changes only the PMIC-wrapper configuration symbol.
INITRAMFS_SHA256 = _base.INITRAMFS_SHA256
FINAL_DTB_SHA256 = _base.FINAL_DTB_SHA256

# Filled after two independent AW assemblies are compared.
IMAGE_GZ_SHA256 = "a7a7196aa7f8888fe957fd731063939f7d6b0fa97802c79cbece6d6589b22dd0"
SYSTEM_MAP_SHA256 = "b8ffc32d7dbdc260dee5a2430866bb4f92f1008e8df44c342ee8402b38e4c9e2"
CONFIG_SHA256 = "a9a28726fd23b1c4b28fb6fb9b11bbf3cd9ee69072b8d1ac2421d8c46a000a26"
SOURCE_BUILD_SHA256 = "0fff0fab9072c2c8b9700edf7d7b396b7cf4332d48739a11d47f0c9e52b62302"
RAW_SHA256 = "42c5c40333379a5445de80a2300bd1b7325f7e7948429c70a2ffaa4d8fca97d2"
RAW_SIZE = "7497728"
ARTIFACT_MANIFEST_SHA256 = "22b2cc789c0ac39792617f693b8852ff1a8ad25d71e733cb6f8727716f34171b"
PADDED_SHA256 = "216daa467231d7a191b918584fa12fed6904429a020c1a2283fbf7ed82f74a0f"
PREVIOUS_AS_PADDED_SHA256 = _base.PADDED_SHA256
INSTALLER_SHA256 = "239cc3dae69da31111df161180fa9b911871eeb99e303a4c0c5bf275f7eb3c0f"

_HEX256 = re.compile(r"^[0-9a-f]{64}$")


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
    if all(unresolved[1:]):
        return "ready-to-pin"
    if any(unresolved):
        raise ValueError("Candidate AW artifact calibration is only partially pinned")
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
        if _HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate AW {name} is unresolved or malformed")
    if not RAW_SIZE.isdecimal() or not 0 < int(RAW_SIZE) <= BOOT2_SIZE:
        raise ValueError("Candidate AW RAW_SIZE is unresolved or malformed")
    if RAW_SHA256 == AO_RAW_SHA256:
        raise ValueError("Candidate AW raw identity equals Candidate AO")
    if PADDED_SHA256 == AO_PADDED_SHA256:
        raise ValueError("Candidate AW padded identity equals Candidate AO")
