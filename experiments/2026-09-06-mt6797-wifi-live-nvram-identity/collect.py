#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""One bounded, read-only live Gemian Wi-Fi identity collection.

The remote stream contains private identity and digest fields.  This module
never prints that stream: it writes only the three digest tokens to a
mode-0700 ignored attempt directory and emits a fixed sanitized JSON record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import shlex
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REMOTE_SCRIPT = HERE / "remote-collect.sh"
EXPECTED_RELEASE = "3.18.41+"
EXPECTED_ARCH = "aarch64"
REMOTE_SECONDS = 15
LOCAL_SECONDS = 20
MAX_OUTPUT = 8 * 1024
MAX_MOUNTINFO = 256 * 1024
MAX_BINARY = 4 * 1024 * 1024
WIFI_SIZE = 514
KEY_RELATIVE = Path("artifacts/credentials/gemini_ed25519")
RECOVERY_HOSTS_RELATIVE = Path("artifacts/credentials/a53-recovery-known_hosts")
RECOVERY_HOSTS_SHA256 = "d43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f"
REMOTE_HOST = "gemini@192.168.1.50"
PREAMBLE_PREFIXES = (
    "** WARNING: connection is not using a post-quantum key exchange algorithm.",
    "** This session may be vulnerable to \"store now, decrypt later\" attacks.",
    "** The server may need to be upgraded. See https://openssh.com/pq.html",
    "bash: warning: setlocale:",
)
ADMISSION_FIELDS = {
    "release", "architecture", "boot_id", "wifi_sha256",
    "nvram_daemon_sha256", "libnvram_sha256",
}
HEX64 = set("0123456789abcdef")


class CollectionError(RuntimeError):
    """A fixed, non-sensitive refusal reason."""


def _regular_owner_only(path: Path, expected_mode: int) -> None:
    st = path.lstat()
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise CollectionError("required input is not a regular file")
    if stat.S_IMODE(st.st_mode) != expected_mode or st.st_uid != os.getuid() or st.st_nlink != 1:
        raise CollectionError("required input has unsafe mode")


def load_admission(path: Path) -> dict[str, str]:
    """Load the private admission without ever echoing its values."""
    _regular_owner_only(path, 0o600)
    if path.stat().st_size > 4096:
        raise CollectionError("admission is too large")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CollectionError("malformed admission") from error
    if not isinstance(value, dict) or set(value) != ADMISSION_FIELDS:
        raise CollectionError("admission schema mismatch")
    for key, item in value.items():
        if not isinstance(item, str) or not item:
            raise CollectionError("admission value is not a string")
        if key == "release":
            if item != EXPECTED_RELEASE:
                raise CollectionError("admission release mismatch")
        elif key == "architecture":
            if item != EXPECTED_ARCH:
                raise CollectionError("admission architecture mismatch")
        elif key == "boot_id":
            parts = item.split("-")
            if [len(part) for part in parts] != [8, 4, 4, 4, 12]:
                raise CollectionError("admission boot identity malformed")
            if any(ch not in "0123456789abcdef" for ch in item.lower().replace("-", "")):
                raise CollectionError("admission boot identity malformed")
        elif len(item) != 64 or set(item.lower()) - HEX64 or item != item.lower():
            raise CollectionError("admission digest malformed")
    return value


def remote_command(expected_boot_id: str) -> str:
    args = (EXPECTED_RELEASE, EXPECTED_ARCH, expected_boot_id)
    script = REMOTE_SCRIPT.read_text(encoding="utf-8")
    return f"exec timeout -s KILL {REMOTE_SECONDS} sh -c {shlex.quote(script)} -- " + \
        " ".join(map(shlex.quote, args))


def ssh_command(repo_root: Path, expected_boot_id: str) -> list[str]:
    key = repo_root / KEY_RELATIVE
    known_hosts = repo_root / RECOVERY_HOSTS_RELATIVE
    return [
        "ssh", "-o", "BatchMode=yes", "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=3",
        "-o", "ServerAliveCountMax=2", "-o", "IdentitiesOnly=yes",
        "-o", "IdentityAgent=none", "-o", "StrictHostKeyChecking=yes",
        "-o", "UpdateHostKeys=no", "-o", "GlobalKnownHostsFile=/dev/null",
        "-o", f"UserKnownHostsFile={known_hosts}", "-F", "/dev/null",
        "-i", str(key), REMOTE_HOST, remote_command(expected_boot_id),
    ]


def _hex_digest(value: str, label: str) -> str:
    if len(value) != 64 or value.lower() != value or set(value) - HEX64:
        raise CollectionError(f"malformed {label} digest")
    return value


def parse_output(raw: bytes, expected_boot_id: str | None = None) -> dict[str, Any]:
    """Validate the private stream and return its non-secret fields."""
    if len(raw) > MAX_OUTPUT:
        raise CollectionError("collector output exceeded 8 KiB")
    try:
        all_lines = raw.decode("utf-8", errors="strict").splitlines()
    except UnicodeError as error:
        raise CollectionError("collector output is not UTF-8") from error
    try:
        start = all_lines.index(f"release_start={EXPECTED_RELEASE}")
    except ValueError as error:
        raise CollectionError("initial identity admission missing") from error
    if any(not line.startswith(PREAMBLE_PREFIXES) for line in all_lines[:start]):
        raise CollectionError("unexpected SSH preamble")
    lines = all_lines[start:]
    pos = 0

    def take(prefix: str, *, allowed: set[str] | None = None) -> str:
        nonlocal pos
        if pos >= len(lines) or not lines[pos].startswith(prefix):
            raise CollectionError(f"missing or out-of-order field: {prefix[:-1]}")
        value = lines[pos][len(prefix):]
        pos += 1
        if not value or (allowed is not None and value not in allowed):
            raise CollectionError(f"invalid field: {prefix[:-1]}")
        return value

    def integer(prefix: str, upper: int) -> int:
        value = take(prefix)
        try:
            parsed = int(value, 10)
        except ValueError as error:
            raise CollectionError(f"invalid numeric field: {prefix[:-1]}") from error
        if parsed < 0 or parsed > upper:
            raise CollectionError(f"numeric field outside bound: {prefix[:-1]}")
        return parsed

    take("release_start=", allowed={EXPECTED_RELEASE})
    take("arch_start=", allowed={EXPECTED_ARCH})
    boot_start = take("boot_id_start=")
    if not boot_start or len(boot_start) != 36:
        raise CollectionError("malformed start boot identity")
    take("container_state=", allowed={"running"})
    take("pid_status=", allowed={"one"})
    take("admission_ready=", allowed={"yes"})
    mountinfo_status = take("mountinfo_status=", allowed={"valid", "invalid", "unreadable"})
    nv_count = integer("mount_nvdata_count=", 2)
    data_count = integer("mount_data_nvram_count=", 2)
    mount_relation = take("mount_relation=", allowed={"yes", "no"})
    wifi_status = take("wifi_status=", allowed={
        "present", "missing", "unreadable", "nonregular", "symlink", "read-error",
    })
    wifi_size = integer("wifi_size=", MAX_BINARY)
    wifi_envelope = take("wifi_envelope=", allowed={"valid", "invalid", "not-checked"})
    wifi_digest = None
    if wifi_status == "present":
        if wifi_size != WIFI_SIZE or wifi_envelope not in {"valid", "invalid"}:
            raise CollectionError("present WIFI record has invalid framing")
        wifi_digest = _hex_digest(take("wifi_digest="), "WIFI")
    elif wifi_envelope != "not-checked":
        raise CollectionError("absent WIFI record has envelope result")

    def parse_binary(label: str) -> tuple[str, int, str | None]:
        status = take(f"{label}_status=", allowed={
            "present", "missing", "unreadable", "nonregular", "symlink", "read-error",
            "oversize",
            "zero", "multiple",
        })
        size = integer(f"{label}_size=", MAX_BINARY + 1)
        if status == "present" and not 1 <= size <= MAX_BINARY:
            raise CollectionError(f"{label} present size outside bound")
        if status == "oversize" and size != MAX_BINARY + 1:
            raise CollectionError(f"{label} oversize marker mismatch")
        digest = _hex_digest(take(f"{label}_digest="), label) if status == "present" else None
        if status != "present" and pos < len(lines) and lines[pos].startswith(f"{label}_digest="):
            raise CollectionError(f"unexpected {label} digest")
        return status, size, digest

    daemon_status, daemon_size, daemon_digest = parse_binary("daemon")
    lib_status, lib_size, lib_digest = parse_binary("lib")
    take("release_end=", allowed={EXPECTED_RELEASE})
    take("arch_end=", allowed={EXPECTED_ARCH})
    boot_end = take("boot_id_end=")
    if boot_end != boot_start:
        raise CollectionError("boot identity changed")
    if expected_boot_id is not None and (boot_start != expected_boot_id or boot_end != expected_boot_id):
        raise CollectionError("boot identity does not match admission")
    if pos != len(lines):
        raise CollectionError("unexpected trailing structured output")
    return {
        "boot_start": boot_start, "boot_end": boot_end,
        "mountinfo_status": mountinfo_status,
        "mount_nvdata_count": nv_count, "mount_data_nvram_count": data_count,
        "mount_relation": mount_relation == "yes",
        "wifi_status": wifi_status, "wifi_size": wifi_size,
        "wifi_envelope": wifi_envelope, "wifi_digest": wifi_digest,
        "daemon_status": daemon_status, "daemon_size": daemon_size,
        "daemon_digest": daemon_digest, "lib_status": lib_status,
        "lib_size": lib_size, "lib_digest": lib_digest,
    }


def validate_process(raw: bytes, returncode: int, timed_out: bool = False,
                     expected_boot_id: str | None = None) -> dict[str, Any]:
    if timed_out:
        raise CollectionError("collector exceeded 20 second host deadline")
    if returncode != 0:
        if b"admission_ready=yes\n" in raw:
            raise CollectionError("collector failed after identity admission")
        raise CollectionError("identity or authenticated SSH refusal")
    return parse_output(raw, expected_boot_id)


def _terminate(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def run_bounded(command: list[str], payload: bytes, *, local_seconds: float = LOCAL_SECONDS,
                max_output: int = MAX_OUTPUT, on_admission=None) -> tuple[bytes, int, bool]:
    deadline = time.monotonic() + local_seconds
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, start_new_session=True)
    assert proc.stdin is not None and proc.stdout is not None
    timed_out = False
    output = bytearray()
    selector = selectors.DefaultSelector()
    try:
        if payload:
            proc.stdin.write(payload)
        if on_admission is None:
            proc.stdin.close()
        os.set_blocking(proc.stdout.fileno(), False)
        selector.register(proc.stdout, selectors.EVENT_READ)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                _terminate(proc)
                break
            events = selector.select(remaining)
            if not events:
                timed_out = True
                _terminate(proc)
                break
            for key, _ in events:
                remaining_cap = max_output - len(output)
                chunk = os.read(key.fileobj.fileno(), min(4096, remaining_cap + 1))
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if len(chunk) > remaining_cap:
                    output.extend(chunk[:remaining_cap])
                    _terminate(proc)
                    return bytes(output), proc.wait(), False
                output.extend(chunk)
                if on_admission is not None and b"admission_ready=yes\n" in output:
                    on_admission(proc.stdin)
                    on_admission = None
        return bytes(output), proc.wait(), timed_out
    finally:
        selector.close()
        if proc.poll() is None:
            _terminate(proc)


def create_attempt_dir(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise CollectionError("attempt directory already exists")
    path.mkdir(parents=True, mode=0o700)
    os.chmod(path, 0o700)
    st = path.lstat()
    if stat.S_IMODE(st.st_mode) != 0o700 or st.st_uid != os.getuid() or st.st_nlink < 2:
        raise CollectionError("attempt directory has unsafe mode")
    _fsync_directory(path)
    _fsync_directory(path.parent)


def _write_private(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(path.parent)
        st = path.lstat()
        if (stat.S_IMODE(st.st_mode), st.st_uid, st.st_nlink) != (0o600, os.getuid(), 1):
            raise CollectionError("private output metadata changed")
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def sanitized_record(info: dict[str, Any], admission: dict[str, str], *, consumed: bool) -> dict[str, Any]:
    matches = {
        "wifi": info["wifi_digest"] is not None and info["wifi_digest"] == admission["wifi_sha256"],
        "daemon": info["daemon_digest"] is not None and info["daemon_digest"] == admission["nvram_daemon_sha256"],
        "lib": info["lib_digest"] is not None and info["lib_digest"] == admission["libnvram_sha256"],
    }
    narrow_pass = bool(
        info["boot_start"] == admission["boot_id"] and
        info["boot_end"] == admission["boot_id"] and
        info["mountinfo_status"] == "valid" and
        info["mount_nvdata_count"] == 1 and info["mount_data_nvram_count"] == 1 and
        info["mount_relation"] and info["wifi_status"] == "present" and
        info["wifi_size"] == WIFI_SIZE and info["wifi_envelope"] == "valid" and
        info["daemon_status"] == "present" and info["lib_status"] == "present" and
        all(matches.values())
    )
    return {
        "schema": "gemini-wifi-live-nvram-identity-v1",
        "identity_stable": info["boot_start"] == info["boot_end"] == admission["boot_id"],
        "container_running": True, "pid_count": 1,
        "mountinfo_valid": info["mountinfo_status"] == "valid",
        "mount_nvdata_count": info["mount_nvdata_count"],
        "mount_data_nvram_count": info["mount_data_nvram_count"],
        "mount_relation": info["mount_relation"],
        "wifi_present": info["wifi_status"] == "present",
        "wifi_size": info["wifi_size"],
        "wifi_envelope_valid": info["wifi_envelope"] == "valid",
        "daemon_present": info["daemon_status"] == "present",
        "daemon_size": info["daemon_size"], "lib_present": info["lib_status"] == "present",
        "lib_size": info["lib_size"], "wifi_digest_match": matches["wifi"],
        "daemon_digest_match": matches["daemon"], "lib_digest_match": matches["lib"],
        "narrow_pass": narrow_pass, "attempt_consumed": consumed,
    }


def collect(admission_path: Path, attempt_dir: Path, repo_root: Path) -> dict[str, Any]:
    admission = load_admission(admission_path)
    key = repo_root / KEY_RELATIVE
    _regular_owner_only(key, 0o600)
    known_hosts = repo_root / RECOVERY_HOSTS_RELATIVE
    _regular_owner_only(known_hosts, 0o600)
    if hashlib.sha256(known_hosts.read_bytes()).hexdigest() != RECOVERY_HOSTS_SHA256:
        raise CollectionError("pinned known-host file changed")
    attempt_root = (repo_root / "artifacts" / "live-nvram-identity").resolve()
    try:
        if attempt_dir.resolve().parent != attempt_root:
            raise CollectionError("attempt directory is outside ignored output root")
    except OSError as error:
        raise CollectionError("attempt directory cannot be resolved") from error
    create_attempt_dir(attempt_dir)
    consumed_marker = False
    def mark_consumed(stream) -> None:
        nonlocal consumed_marker
        _write_private(attempt_dir / "consumed", b"post-admission collection\n")
        stream.write(b"GEMINI-WIFI-NVRAM-CONSUME-v1\n")
        stream.flush()
        stream.close()
        consumed_marker = True

    raw, code, timed_out = run_bounded(
        ssh_command(repo_root, admission["boot_id"]), b"",
        on_admission=mark_consumed)
    if consumed_marker:
        _write_private(attempt_dir / "raw-stream.txt", raw)
    info: dict[str, Any] | None = None
    try:
        info = validate_process(raw, code, timed_out, admission["boot_id"])
    except CollectionError:
        raise
    _write_private(attempt_dir / "wifi.sha256", (info["wifi_digest"] or "").encode() + b"\n")
    _write_private(attempt_dir / "nvram_daemon.sha256", (info["daemon_digest"] or "").encode() + b"\n")
    _write_private(attempt_dir / "libnvram.sha256", (info["lib_digest"] or "").encode() + b"\n")
    if not consumed_marker:
        _write_private(attempt_dir / "consumed", b"post-admission collection\n")
    result = sanitized_record(info, admission, consumed=True)
    _write_private(attempt_dir / "result.json", (json.dumps(result, sort_keys=True) + "\n").encode())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="perform the one admitted SSH read")
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--attempt-dir", type=Path)
    args = parser.parse_args(argv)
    if not args.execute:
        print("DRY-RUN: no SSH, no device access, no private input read")
        return 0
    if args.admission is None or args.attempt_dir is None:
        print("REFUSED: execute requires an admission and a new attempt directory", file=sys.stderr)
        return 2
    try:
        result = collect(args.admission, args.attempt_dir, Path(__file__).resolve().parents[2])
    except (CollectionError, OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
