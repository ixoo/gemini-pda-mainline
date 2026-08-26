#!/usr/bin/env python3
"""Test exact conversion from the legacy probe line to bounded commands."""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "netcat_bounded_exec", SCRIPT_DIR / "netcat-bounded-exec.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

source = (b"#!/bin/sh\nprintf 'bounded transport test\\n'\n" * 512)
payload = base64.b64encode(source)
legacy = (
    b"printf '%s' '" + payload +
    b"' | /bin/busybox base64 -d | /bin/busybox sh\n"
)
bounded = MODULE.bounded_command_stream(legacy)
lines = bounded.decode("ascii").splitlines()
assert max(map(len, lines)) <= MODULE.MAX_COMMAND
chunks = []
prefix = f'{MODULE.ENCODER.VARIABLE}="${{{MODULE.ENCODER.VARIABLE}}}'
for line in lines:
    if line.startswith(prefix):
        assert line.endswith('"')
        chunks.append(line[len(prefix):-1])
assert base64.b64decode("".join(chunks), validate=True) == source
assert len(chunks) > 20

for mutation in (
    legacy + b"echo extra\n",
    legacy.replace(b"/bin/busybox sh", b"sh"),
    b"printf '%s' '!!!!' | /bin/busybox base64 -d | /bin/busybox sh\n",
):
    try:
        MODULE.bounded_command_stream(mutation)
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe legacy-command mutation accepted")

print(f"bounded_chunks={len(chunks)}")
print(f"maximum_command_line={max(map(len, lines))}")
print("legacy_command_mutations_rejected=3")
print("remote_temporary_file=false")
print("result=pass")
