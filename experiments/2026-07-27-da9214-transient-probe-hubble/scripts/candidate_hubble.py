"""Pinned identities and safety boundaries for Candidate Hubble."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-27-da9214-transient-probe-hubble"
CANDIDATE = "Hubble"

# Hubble deliberately republishes the complete hardware-passed Cassini
# artifact without changing any member bytes or modes. Only the enclosing
# directory name changes.
CASSINI_ARTIFACT_DIR = "candidate-Cassini-da9214-direct-address-e02e2673"
ARTIFACT_DIR = "candidate-Hubble-cassini-rollback-e02e2673"
BOOT_MEMBER = "gemini-mt6797-da9214-cassini.boot.img"
PADDED_MEMBER = "boot2-padded.img"
MANIFEST_MEMBER = "SHA256SUMS"

CASSINI_MANIFEST_SHA256 = (
    "0d1a954827f5ebd31abc12b4d0a207105c5e270403a9b3a66cbd70626e5b2306"
)
CASSINI_RAW_SHA256 = (
    "e02e2673ca054d3e4081f5234d26a394617777e8496417fd75196a948d55fa4d"
)
CASSINI_RAW_SIZE = 7_645_184
CASSINI_PADDED_SHA256 = (
    "febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1"
)
BOOT2_SIZE = 16 * 1024 * 1024

# Exact installed/readback-verified Photon r2. Its first intended boot reached
# a white screen and automatically returned to Gemian before serviceability.
PHOTON_R2_PADDED_SHA256 = (
    "0ffe1ee750ff219c9ee6f9d4809ecb8748bdd2a35ba63d68a99b3d74e599c2f7"
)
PHOTON_R2_RAW_SHA256 = (
    "75b9081c013408c2358ec3c4cafcf7381294c22215432add98739f72033e8ad6"
)

# Source-pinned installer foundation.
PHOTON_DERIVER_SHA256 = (
    "4529282f1fa549168784681575281900c91724da76d29950e8ae7e2cdb27b865"
)
PHOTON_INSTALLER_SHA256 = (
    "6d98d9a807687567f91513466587ce2b644e5935f841292205fd4a3d25820d5c"
)

# Calibrated after exact derivation and shell validation.
INSTALLER_SHA256 = (
    "3adaf33fbb4567ac9ef3fd2030f85a24f69f5349f812d49493c56ded716a2452"
)

EXECUTABLE_MEMBERS = frozenset(
    {
        "cassini-probe",
        "console-keymap-verify",
        "console-unicode-mode",
        "input-event-capture",
    }
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


def require_pins(*, installer: bool = False) -> None:
    hashes = {
        "CASSINI_MANIFEST_SHA256": CASSINI_MANIFEST_SHA256,
        "CASSINI_RAW_SHA256": CASSINI_RAW_SHA256,
        "CASSINI_PADDED_SHA256": CASSINI_PADDED_SHA256,
        "PHOTON_R2_PADDED_SHA256": PHOTON_R2_PADDED_SHA256,
        "PHOTON_R2_RAW_SHA256": PHOTON_R2_RAW_SHA256,
        "PHOTON_DERIVER_SHA256": PHOTON_DERIVER_SHA256,
        "PHOTON_INSTALLER_SHA256": PHOTON_INSTALLER_SHA256,
    }
    if installer:
        hashes["INSTALLER_SHA256"] = INSTALLER_SHA256
    for name, value in hashes.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Hubble {name} is unresolved or malformed")
    if not 0 < CASSINI_RAW_SIZE < BOOT2_SIZE:
        raise ValueError("Candidate Hubble raw size is invalid")
    if CASSINI_PADDED_SHA256 == PHOTON_R2_PADDED_SHA256:
        raise ValueError("Hubble target identity equals its Photon r2 predecessor")
