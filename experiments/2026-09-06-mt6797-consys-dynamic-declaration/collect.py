#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run one bounded read-only Gemian DT declaration collector."""

from __future__ import annotations

import os
import selectors
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REMOTE_SCRIPT = HERE / "remote-collect.sh"
EXPECTED_RELEASE = "3.18.41+"
EXPECTED_BOOT_ID = "ce741f2c-462f-424e-aa90-49bada3a116f"
EXPECTED_MODEL = "MT6797X"
REMOTE_SECONDS = 10
LOCAL_SECONDS = 15
MAX_OUTPUT = 16 * 1024
PROPERTY_LABELS = (
    "root_address_cells", "root_size_cells", "reserved_address_cells",
    "reserved_size_cells", "reserved_ranges", "node_reg", "node_size",
    "node_alignment", "node_alloc_ranges",
)
PREAMBLE_PREFIXES = (
    "** WARNING: connection is not using a post-quantum key exchange algorithm.",
    "** This session may be vulnerable to \"store now, decrypt later\" attacks.",
    "** The server may need to be upgraded. See https://openssh.com/pq.html",
    "bash: warning: setlocale:",
)


class CollectionError(RuntimeError):
    pass


def remote_command() -> str:
    values = (EXPECTED_RELEASE, EXPECTED_BOOT_ID, EXPECTED_MODEL)
    return "exec timeout -s KILL 10 sh -s -- " + " ".join(
        map(shlex.quote, values))


def ssh_command() -> list[str]:
    return [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
        "-o", "ServerAliveInterval=3", "-o", "ServerAliveCountMax=2",
        "-o", "StrictHostKeyChecking=yes", "-o", "UpdateHostKeys=no",
        "gemini", remote_command(),
    ]


def validate_output(raw: bytes) -> str:
    if len(raw) > MAX_OUTPUT:
        raise CollectionError("collector output exceeded 16 KiB")
    lines = raw.decode("utf-8", errors="strict").splitlines()
    try:
        start = lines.index(f"release_start={EXPECTED_RELEASE}")
    except ValueError as error:
        raise CollectionError("missing exact identity field: release_start") from error
    if any(not line.startswith(PREAMBLE_PREFIXES) for line in lines[:start]):
        raise CollectionError("unexpected SSH preamble")
    lines = lines[start:]
    cursor = 0

    def take(expected: str) -> None:
        nonlocal cursor
        if cursor >= len(lines) or lines[cursor] != expected:
            raise CollectionError(f"missing or out-of-order field: {expected.split('=', 1)[0]}")
        cursor += 1

    take(f"release_start={EXPECTED_RELEASE}")
    take(f"boot_id_start={EXPECTED_BOOT_ID}")
    take(f"model_start={EXPECTED_MODEL}")
    take("declaration_begin")
    for label in PROPERTY_LABELS:
        prefix = f"{label}_status="
        if cursor >= len(lines) or not lines[cursor].startswith(prefix):
            raise CollectionError(f"missing or out-of-order field: {label}_status")
        status = lines[cursor][len(prefix):]
        cursor += 1
        if status not in {"present", "missing", "unreadable", "read-error"}:
            raise CollectionError(f"invalid property status: {label}")
        if status != "present":
            continue
        bytes_prefix = f"{label}_bytes="
        hex_prefix = f"{label}_hex="
        if cursor >= len(lines) or not lines[cursor].startswith(bytes_prefix):
            raise CollectionError(f"missing property byte count: {label}")
        try:
            byte_count = int(lines[cursor][len(bytes_prefix):], 10)
        except ValueError as error:
            raise CollectionError(f"invalid property byte count: {label}") from error
        cursor += 1
        if byte_count < 0 or cursor >= len(lines) or not lines[cursor].startswith(hex_prefix):
            raise CollectionError(f"missing or invalid property hex: {label}")
        value = lines[cursor][len(hex_prefix):]
        cursor += 1
        try:
            decoded = bytes.fromhex(value)
        except ValueError as error:
            raise CollectionError(f"invalid property hex: {label}") from error
        if len(decoded) != byte_count or len(value) != byte_count * 2:
            raise CollectionError(f"property byte/hex mismatch: {label}")
    take("node_no_map=yes" if cursor < len(lines) and lines[cursor] ==
         "node_no_map=yes" else "node_no_map=no")
    take("node_reusable=yes" if cursor < len(lines) and lines[cursor] ==
         "node_reusable=yes" else "node_reusable=no")
    take("declaration_end")
    take(f"release_end={EXPECTED_RELEASE}")
    take(f"boot_id_end={EXPECTED_BOOT_ID}")
    take(f"model_end={EXPECTED_MODEL}")
    if cursor != len(lines):
        raise CollectionError("unexpected trailing structured output")
    return "\n".join(lines) + "\n"


def accept_process_result(raw: bytes, returncode: int,
                          timed_out: bool = False) -> str:
    if timed_out:
        raise CollectionError("collector exceeded 15 second host deadline")
    if returncode != 0:
        raise CollectionError(f"collector exited {returncode}")
    return validate_output(raw)


def terminate(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def run_bounded(command: list[str], payload: bytes, *, local_seconds: float,
                max_output: int) -> tuple[bytes, int]:
    deadline = time.monotonic() + local_seconds
    proc = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, start_new_session=True,
    )
    assert proc.stdin is not None and proc.stdout is not None
    try:
        proc.stdin.write(payload)
        proc.stdin.close()
        os.set_blocking(proc.stdout.fileno(), False)
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        output = bytearray()
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                terminate(proc)
                raise CollectionError("collector exceeded 15 second host deadline")
            events = selector.select(remaining)
            if not events:
                continue
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 4096)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                output.extend(chunk)
                if len(output) > max_output:
                    terminate(proc)
                    raise CollectionError("collector output exceeded configured maximum")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            terminate(proc)
            raise CollectionError("collector exceeded 15 second host deadline")
        return bytes(output), proc.wait(timeout=remaining)
    finally:
        if proc.poll() is None:
            terminate(proc)


def collect() -> tuple[bytes, int]:
    return run_bounded(ssh_command(), REMOTE_SCRIPT.read_bytes(),
                       local_seconds=LOCAL_SECONDS, max_output=MAX_OUTPUT)


def main() -> int:
    try:
        raw, returncode = collect()
        text = accept_process_result(raw, returncode)
    except (CollectionError, OSError, subprocess.SubprocessError,
            UnicodeError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
