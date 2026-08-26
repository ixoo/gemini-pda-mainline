#!/usr/bin/env python3
"""Prove bounded transport round-trips exact payload bytes without device I/O."""

from __future__ import annotations

import base64
from pathlib import Path
import re
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
ENCODER = SCRIPT_DIR / "encode-netcat-payload.py"

with tempfile.TemporaryDirectory(prefix="a72-bounded-transport-") as temp:
    probe = Path(temp) / "probe.sh"
    original = b"#!/bin/sh\n" + b"printf x\\n\n" * 2048
    probe.write_bytes(original)
    output = subprocess.run(
        ["python3", str(ENCODER), str(probe)], check=True, text=True,
        stdout=subprocess.PIPE,
    ).stdout
    lines = output.splitlines()
    if max(map(len, lines)) > 820:
        raise SystemExit("FAIL: transport line exceeds bound")
    chunks = []
    pattern = re.compile(r'^__a72_probe_payload="\$\{__a72_probe_payload\}([A-Za-z0-9+/=]+)"$')
    for line in lines:
        match = pattern.fullmatch(line)
        if match:
            chunks.append(match.group(1))
    if base64.b64decode("".join(chunks), validate=True) != original:
        raise SystemExit("FAIL: payload round trip")
    if not lines[0] == "__a72_probe_payload=''":
        raise SystemExit("FAIL: initializer")
    if lines[-1] != "unset __a72_probe_payload":
        raise SystemExit("FAIL: cleanup")
    for forbidden in ("/tmp/", "reboot", "/dev/mmc", "dd ", "writel"):
        if forbidden in output:
            raise SystemExit(f"FAIL: forbidden transport token: {forbidden}")

print("transport_validation=pass")
print("chunk_size=768")
print("maximum_command_line=820")
print("remote_temporary_file=none")
print("device_storage_write=none")
print("reboot_request=none")
