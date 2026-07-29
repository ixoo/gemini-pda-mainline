"""Pinned identities and safety boundaries for the Kepler split-read probe."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-27-i2c6-split-read-kepler"
CANDIDATE = "Kepler"
ACCEPTED_BOOT_ID = "cdd23c48-0bd3-4980-95c8-5e054be860d9"
PRE_COUNTER = 6
POST_COUNTER = 10
PROBE_SOURCE_SHA256 = (
    "1ff0c574ee8e02290a6f53234d2f22652ce25c385b31442e8ff2411d094e0765"
)
PROBE_BINARY_SHA256 = (
    "3afdaeea3f913706a0ee3f44732c37b6c0fced01f940f6d68a8356dfad946fa7"
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
        raise ValueError("Kepler source identity is unresolved or malformed")
    if binary:
        if HEX256.fullmatch(PROBE_BINARY_SHA256) is None:
            raise ValueError("Kepler binary identity is unresolved or malformed")
        if PROBE_BINARY_SIZE <= 0:
            raise ValueError("Kepler binary size is unresolved or malformed")
