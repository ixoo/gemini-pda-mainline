"""Pinned identities and safety boundaries for the Mariner API-path probe."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-27-i2c6-api-path-mariner"
CANDIDATE = "Mariner"
ACCEPTED_BOOT_ID = "cdd23c48-0bd3-4980-95c8-5e054be860d9"
PRE_COUNTER = 14
POST_COUNTER = 18
PRIOR_VOYAGER_CAPTURE_SHA256 = (
    "aae3626d0cbd5275908ff2aaa3f9507709c591b2a0aa2bd996ca0ccf4c46adc1"
)
PROBE_SOURCE_SHA256 = (
    "101154791c4a9918afe8438101eeb16eb8eeb2ef8dfe6032f348f6d114a1f0bc"
)
PROBE_BINARY_SHA256 = (
    "958ce2a16b6716f550e38667b2bc4c61e04bc0be977c9bf31f594fc30a9bf93c"
)
PROBE_BINARY_SIZE = 537_584
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def require_pins(*, binary: bool = True) -> None:
    if HEX256.fullmatch(PROBE_SOURCE_SHA256) is None:
        raise ValueError("Mariner source identity is unresolved or malformed")
    if HEX256.fullmatch(PRIOR_VOYAGER_CAPTURE_SHA256) is None:
        raise ValueError("prior Voyager capture identity is unresolved or malformed")
    if binary:
        if HEX256.fullmatch(PROBE_BINARY_SHA256) is None:
            raise ValueError("Mariner binary identity is unresolved or malformed")
        if PROBE_BINARY_SIZE <= 0:
            raise ValueError("Mariner binary size is unresolved or malformed")
