"""Pinned identities and safety boundaries for Orion's boot2 installer."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import pathlib
import re
import stat

import candidate_orion as co


# Final identities reproduced by the complete two-build by two-baseline
# assembly matrix.
ORION_RAW_SHA256 = (
    "6724eb7bccc5179955681a156468af53ec60557242b50e555cb50a02769a04db"
)
ORION_RAW_SIZE = 7_747_584
ORION_PADDED_SHA256 = (
    "74f9d9c8cae1213665db2100dda72e0531e0b221cd74a660fc183edcd7bb50d4"
)
ORION_MANIFEST_SHA256 = (
    "d72975f4953bfeeff8b9a7da7c1afa931630838ef5c1773c50ba1efe0f7d51e0"
)

# This may remain unresolved for the first calibrated derivation. Fill it with
# that derivation's printed SHA-256, then derive again to pin the installer
# itself.
INSTALLER_SHA256 = (
    "392a1fa9616ca501db0a4af5d49e1542fb3bf23cd8ecfff7ab3b2d082e280c14"
)

BOOT2_SIZE = 16 * 1024 * 1024
TARGET = "gemini@192.168.1.50"

# Exact hardware-passed Hubble predecessor required on the complete live boot2
# partition immediately before Orion is written.
HUBBLE_PADDED_SHA256 = (
    "febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1"
)

# Source-pinned Hubble installer foundation.
HUBBLE_DERIVER_SHA256 = (
    "762c53d5e79e6d837aa74b3c20e80b9d5c064c8db92ddb37b9ba1b9fb4b57e38"
)
HUBBLE_PINS_SHA256 = (
    "1e1775a833974e53ab057893fd5b9ec45e026818471533bc7f077479b3dd6213"
)
HUBBLE_INSTALLER_SHA256 = (
    "3adaf33fbb4567ac9ef3fd2030f85a24f69f5349f812d49493c56ded716a2452"
)

EXPERIMENT = co.EXPERIMENT
BOOT_MEMBER = co.BOOT_MEMBER
ARTIFACT_PREFIX = co.ARTIFACT_PREFIX
HEX256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ArtifactPins:
    raw_sha256: str
    raw_size: int
    padded_sha256: str
    manifest_sha256: str

    @property
    def artifact_dir(self) -> str:
        return f"{ARTIFACT_PREFIX}{self.raw_sha256[:8]}"


def production_pins() -> ArtifactPins:
    return ArtifactPins(
        raw_sha256=ORION_RAW_SHA256,
        raw_size=ORION_RAW_SIZE,
        padded_sha256=ORION_PADDED_SHA256,
        manifest_sha256=ORION_MANIFEST_SHA256,
    )


def pins_resolved(pins: ArtifactPins) -> bool:
    return (
        HEX256.fullmatch(pins.raw_sha256) is not None
        and HEX256.fullmatch(pins.padded_sha256) is not None
        and HEX256.fullmatch(pins.manifest_sha256) is not None
        and isinstance(pins.raw_size, int)
        and not isinstance(pins.raw_size, bool)
        and 0 < pins.raw_size <= BOOT2_SIZE
    )


def require_artifact_pins(pins: ArtifactPins) -> None:
    values = {
        "ORION_RAW_SHA256": pins.raw_sha256,
        "ORION_PADDED_SHA256": pins.padded_sha256,
        "ORION_MANIFEST_SHA256": pins.manifest_sha256,
    }
    for name, value in values.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Orion {name} is unresolved or malformed")
    if (
        not isinstance(pins.raw_size, int)
        or isinstance(pins.raw_size, bool)
        or not 0 < pins.raw_size <= BOOT2_SIZE
    ):
        raise ValueError("Candidate Orion ORION_RAW_SIZE is unresolved or invalid")
    if pins.padded_sha256 == HUBBLE_PADDED_SHA256:
        raise ValueError("Orion padded identity equals its Hubble predecessor")
    if len({pins.raw_sha256, pins.padded_sha256, pins.manifest_sha256}) != 3:
        raise ValueError("Orion raw, padded, and manifest identities are not distinct")


def require_installer_pin() -> None:
    if INSTALLER_SHA256 != "UNRESOLVED" and HEX256.fullmatch(INSTALLER_SHA256) is None:
        raise ValueError("Candidate Orion INSTALLER_SHA256 is malformed")


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
