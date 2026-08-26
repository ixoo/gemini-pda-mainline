#!/usr/bin/env python3
"""Replace one legacy netcat probe line with bounded in-memory commands."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
ENCODER_PATH = SCRIPT_DIR / "encode-netcat-payload.py"
ENCODER_SHA256 = "06a2ece3570440ec8194cc2568af3151abef9e7314480e960649a77b20ea7956"
WRAPPER_SHA256 = "124f15e09c9c2812b35e91a3a30d347458729a7b2333b216d730ff6824e2dc86"
MATERIALIZED_SHA256 = "de72e6cf61aec14c2deb56ee67a133ad323612d87812914e96a2644bca91d1c9"
LEGACY = re.compile(
    rb"printf '%s' '([A-Za-z0-9+/]+={0,2})' \| "
    rb"/bin/busybox base64 -d \| /bin/busybox sh\n"
)
MAX_INPUT = 100_000
MAX_COMMAND = 820


if hashlib.sha256(ENCODER_PATH.read_bytes()).hexdigest() != ENCODER_SHA256:
    raise SystemExit("bounded payload encoder changed")
SPEC = importlib.util.spec_from_file_location("bounded_payload_encoder", ENCODER_PATH)
assert SPEC is not None and SPEC.loader is not None
ENCODER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENCODER)


def bounded_command_stream(legacy: bytes, replacement: bytes | None = None) -> bytes:
    match = LEGACY.fullmatch(legacy)
    if match is None:
        raise ValueError("legacy probe command is not exact")
    payload = match.group(1)
    decoded = base64.b64decode(payload, validate=True)
    if not decoded:
        raise ValueError("probe payload is empty")
    if replacement is not None:
        if hashlib.sha256(decoded).hexdigest() != WRAPPER_SHA256:
            raise ValueError("legacy wrapper identity changed")
        if hashlib.sha256(replacement).hexdigest() != MATERIALIZED_SHA256:
            raise ValueError("materialized probe identity changed")
        payload = base64.b64encode(replacement)
    variable = ENCODER.VARIABLE
    lines = [f"{variable}=''" ]
    text = payload.decode("ascii")
    for offset in range(0, len(text), ENCODER.CHUNK_SIZE):
        chunk = text[offset:offset + ENCODER.CHUNK_SIZE]
        lines.append(f'{variable}="${{{variable}}}{chunk}"')
    lines.extend((
        "printf '\\n'; printf '%s' \"$__a72_probe_payload\" | "
        "/bin/busybox base64 -d | /bin/busybox sh",
        f"unset {variable}",
    ))
    if max(map(len, lines)) > MAX_COMMAND:
        raise ValueError("bounded command exceeds ceiling")
    return ("\n".join(lines) + "\n").encode("ascii")


def main() -> int:
    legacy = sys.stdin.buffer.read(MAX_INPUT + 1)
    if len(legacy) > MAX_INPUT:
        raise SystemExit("legacy probe command exceeds ceiling")
    replacement = None
    replacement_name = os.environ.get("GEMINI_MATERIALIZED_PROBE")
    if replacement_name:
        replacement_path = Path(replacement_name)
        if (
            not replacement_path.is_absolute()
            or replacement_path.is_symlink()
            or not replacement_path.is_file()
        ):
            raise SystemExit("materialized probe is missing or unsafe")
        replacement = replacement_path.read_bytes()
        if not replacement or len(replacement) > MAX_INPUT:
            raise SystemExit("materialized probe size is unsafe")
    try:
        commands = bounded_command_stream(legacy, replacement)
    except (ValueError, base64.binascii.Error) as error:
        raise SystemExit(str(error)) from error
    real_nc = Path(os.environ.get("GEMINI_REAL_NC", "/usr/bin/nc"))
    if not real_nc.is_absolute() or not real_nc.is_file() or not os.access(real_nc, os.X_OK):
        raise SystemExit("real netcat is missing or unsafe")
    return subprocess.run([str(real_nc), *sys.argv[1:]], input=commands, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
