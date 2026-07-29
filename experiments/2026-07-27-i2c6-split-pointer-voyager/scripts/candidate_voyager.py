"""Pinned identities and safety boundaries for the Voyager split-read probe."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-27-i2c6-split-pointer-voyager"
CANDIDATE = "Voyager"
ACCEPTED_BOOT_ID = "cdd23c48-0bd3-4980-95c8-5e054be860d9"
PRE_COUNTER = 10
POST_COUNTER = 14
PRIOR_KEPLER_CAPTURE_SHA256 = (
    "43127dc409bfea80dbb7a7bccd8be2727aafa040207c3f5acd8df54f24b61ef6"
)
PROBE_SOURCE_SHA256 = (
    "53cef8eca6fc0aa7064bc34a16b97ddaf649603fe286ffd2b04026b5ea57d17b"
)
PROBE_BINARY_SHA256 = (
    "1a2a141a376661557610f2dd37b10a6a2da620cdbc35eab24b58129552adcd3e"
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
        raise ValueError("Voyager source identity is unresolved or malformed")
    if HEX256.fullmatch(PRIOR_KEPLER_CAPTURE_SHA256) is None:
        raise ValueError("prior Kepler capture identity is unresolved or malformed")
    if binary:
        if HEX256.fullmatch(PROBE_BINARY_SHA256) is None:
            raise ValueError("Voyager binary identity is unresolved or malformed")
        if PROBE_BINARY_SIZE <= 0:
            raise ValueError("Voyager binary size is unresolved or malformed")
