#!/usr/bin/env python3
"""Test exact conversion from the legacy probe line to bounded commands."""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
import subprocess
import tempfile


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

wrapper = (SCRIPT_DIR / "remote-live-probe.sh").read_bytes()
assert MODULE.hashlib.sha256(wrapper).hexdigest() == MODULE.WRAPPER_SHA256
with tempfile.TemporaryDirectory(prefix="gemini-netcat-materialized-") as directory:
    materialized_path = Path(directory) / "probe.sh"
    subprocess.run(
        [str(SCRIPT_DIR / "materialize-live-probe.sh"), "--output", str(materialized_path)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    materialized = materialized_path.read_bytes()
wrapper_legacy = (
    b"printf '%s' '" + base64.b64encode(wrapper) +
    b"' | /bin/busybox base64 -d | /bin/busybox sh\n"
)
materialized_bounded = MODULE.bounded_command_stream(wrapper_legacy, materialized)
materialized_chunks = []
for line in materialized_bounded.decode("ascii").splitlines():
    if line.startswith(prefix):
        materialized_chunks.append(line[len(prefix):-1])
assert base64.b64decode("".join(materialized_chunks), validate=True) == materialized

mutated_wrapper = wrapper.replace(b"#!/usr/bin/env bash", b"#!/bin/sh", 1)
mutated_wrapper_legacy = (
    b"printf '%s' '" + base64.b64encode(mutated_wrapper) +
    b"' | /bin/busybox base64 -d | /bin/busybox sh\n"
)
for legacy_mutation, replacement_mutation in (
    (mutated_wrapper_legacy, materialized),
    (wrapper_legacy, materialized + b"\n"),
):
    try:
        MODULE.bounded_command_stream(legacy_mutation, replacement_mutation)
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe materialization identity mutation accepted")

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
print(f"materialized_chunks={len(materialized_chunks)}")
print("materialization_identity_mutations_rejected=2")
print("remote_temporary_file=false")
print("result=pass")
