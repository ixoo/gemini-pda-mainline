#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run the one-shot Gemian metadata collector with hard host bounds."""

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
MAX_OUTPUT = 64 * 1024


class CollectionError(RuntimeError):
    pass


def remote_command() -> str:
    args = (EXPECTED_RELEASE, EXPECTED_BOOT_ID, EXPECTED_MODEL)
    quoted = " ".join(shlex.quote(value) for value in args)
    return f"exec timeout {REMOTE_SECONDS} sh -s -- {quoted}"


def ssh_command() -> list[str]:
    return [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
        "-o", "ServerAliveInterval=3", "-o", "ServerAliveCountMax=2",
        "-o", "StrictHostKeyChecking=yes", "-o", "UpdateHostKeys=no",
        "gemini", remote_command(),
    ]


def validate_output(raw: bytes) -> str:
    if len(raw) > MAX_OUTPUT:
        raise CollectionError("collector output exceeded 64 KiB")
    text = raw.decode("utf-8", errors="strict")
    lines = text.splitlines()
    expected = {
        "release_start": EXPECTED_RELEASE,
        "boot_id_start": EXPECTED_BOOT_ID,
        "model_start": EXPECTED_MODEL,
        "release_end": EXPECTED_RELEASE,
        "boot_id_end": EXPECTED_BOOT_ID,
        "model_end": EXPECTED_MODEL,
    }
    for key, value in expected.items():
        if lines.count(f"{key}={value}") != 1:
            raise CollectionError(f"missing or duplicate exact identity field: {key}")
    for marker in (
        "reserved_context_begin", "reserved_context_end",
        "reserved_nodes_begin", "reserved_nodes_end",
        "platform_owners_begin", "platform_owners_end",
        "iomem_begin", "iomem_end",
    ):
        if lines.count(marker) != 1:
            raise CollectionError(f"missing or duplicate section marker: {marker}")
    return text


def accept_process_result(raw: bytes, returncode: int, timed_out: bool = False) -> str:
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


def collect() -> tuple[bytes, int]:
    script = REMOTE_SCRIPT.read_bytes()
    proc = subprocess.Popen(
        ssh_command(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    assert proc.stdin is not None and proc.stdout is not None
    try:
        proc.stdin.write(script)
        proc.stdin.close()
        os.set_blocking(proc.stdout.fileno(), False)
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        output = bytearray()
        deadline = time.monotonic() + LOCAL_SECONDS
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                terminate(proc)
                accept_process_result(bytes(output), -1, timed_out=True)
            events = selector.select(remaining)
            if not events:
                continue
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 4096)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                output.extend(chunk)
                if len(output) > MAX_OUTPUT:
                    terminate(proc)
                    raise CollectionError("collector output exceeded 64 KiB")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            terminate(proc)
            accept_process_result(bytes(output), -1, timed_out=True)
        returncode = proc.wait(timeout=remaining)
        return bytes(output), returncode
    finally:
        if proc.poll() is None:
            terminate(proc)


def main() -> int:
    try:
        raw, returncode = collect()
        text = accept_process_result(raw, returncode)
    except (CollectionError, OSError, subprocess.SubprocessError, UnicodeError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
