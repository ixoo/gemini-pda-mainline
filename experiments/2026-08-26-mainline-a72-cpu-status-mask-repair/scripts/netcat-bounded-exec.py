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


def bounded_command_stream(legacy: bytes) -> bytes:
    match = LEGACY.fullmatch(legacy)
    if match is None:
        raise ValueError("legacy probe command is not exact")
    payload = match.group(1)
    decoded = base64.b64decode(payload, validate=True)
    if not decoded:
        raise ValueError("probe payload is empty")
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
    try:
        commands = bounded_command_stream(legacy)
    except (ValueError, base64.binascii.Error) as error:
        raise SystemExit(str(error)) from error
    real_nc = Path(os.environ.get("GEMINI_REAL_NC", "/usr/bin/nc"))
    if not real_nc.is_absolute() or not real_nc.is_file() or not os.access(real_nc, os.X_OK):
        raise SystemExit("real netcat is missing or unsafe")
    return subprocess.run([str(real_nc), *sys.argv[1:]], input=commands, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
