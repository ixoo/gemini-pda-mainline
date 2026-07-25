#!/usr/bin/env python3
"""Strictly decode Candidate AP's private USB live-FDT transfer."""

from __future__ import annotations

import argparse
import base64
import binascii
import dataclasses
import hashlib
import os
import pathlib
import re
import stat
import struct
import sys
import uuid


sys.dont_write_bytecode = True

PRIVATE_RELATIVE_ROOT = pathlib.Path("artifacts/runtime-captures")
TRANSCRIPT_NAME = "live-fdt-transfer.txt"
FDT_NAME = "live-fdt.dtb"
USB_BANNER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
HOST_MAC = "42:00:15:19:82:00"
HOST_ADDRESS = "10.15.19.1"
DEVICE_ADDRESS = "10.15.19.82"
HOST_BEGIN = "__AP_LIVE_FDT_HOST_BEGIN__"
HOST_END = "__AP_LIVE_FDT_HOST_END__"
CAPTURE_BEGIN = "__AP_LIVE_FDT_CAPTURE_BEGIN__"
CAPTURE_END = "__AP_LIVE_FDT_CAPTURE_END__"
PAYLOAD_BEGIN = "__AP_LIVE_FDT_BASE64_BEGIN__"
PAYLOAD_END = "__AP_LIVE_FDT_BASE64_END__"
MARKERS = (
    HOST_BEGIN,
    HOST_END,
    CAPTURE_BEGIN,
    PAYLOAD_BEGIN,
    PAYLOAD_END,
    CAPTURE_END,
)
HEX256 = re.compile(r"[0-9a-f]{64}")
INTERFACE = re.compile(r"[A-Za-z0-9]+")
OUTPUT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
BASE64_LINE = re.compile(r"[A-Za-z0-9+/]+={0,2}")
UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
MAX_TRANSCRIPT_SIZE = 2 * 1024 * 1024
MAX_FDT_SIZE = 1024 * 1024
FDT_MAGIC = 0xD00DFEED


@dataclasses.dataclass(frozen=True)
class CaptureResult:
    boot_id: str
    live_fdt_sha256: str
    live_fdt_size: int


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_canonical_absolute(path: pathlib.Path, label: str) -> None:
    if not path.is_absolute():
        raise ValueError(f"{label} must be absolute")
    normalized = pathlib.Path(os.path.normpath(os.fspath(path)))
    if normalized != path:
        raise ValueError(f"{label} must be lexically canonical")


def require_owned_mode(
    path: pathlib.Path,
    label: str,
    wanted_mode: int,
    *,
    directory: bool,
    nonempty: bool = False,
) -> os.stat_result:
    info = path.lstat()
    wanted_type = stat.S_ISDIR if directory else stat.S_ISREG
    if path.is_symlink() or not wanted_type(info.st_mode):
        raise ValueError(f"{label} is missing, unsafe, or has the wrong type")
    if stat.S_IMODE(info.st_mode) != wanted_mode:
        raise ValueError(f"{label} mode must be {wanted_mode:04o}")
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise ValueError(f"{label} is not owned by the current user")
    if nonempty and not info.st_size:
        raise ValueError(f"{label} is empty")
    return info


def private_root(repository: pathlib.Path) -> pathlib.Path:
    require_canonical_absolute(repository, "repository")
    require_owned_mode(repository, "repository", stat.S_IMODE(repository.lstat().st_mode), directory=True)
    if repository.resolve(strict=True) != repository:
        raise ValueError("repository path traverses a symlink")

    ignore = repository / ".gitignore"
    info = ignore.lstat()
    if ignore.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError("repository .gitignore is missing or unsafe")
    ignored = {
        line.strip()
        for line in ignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if "/artifacts/" not in ignored:
        raise ValueError("repository does not ignore /artifacts/")

    root = repository / PRIVATE_RELATIVE_ROOT
    require_owned_mode(root, "private runtime-capture root", 0o700, directory=True)
    if root.resolve(strict=True) != root:
        raise ValueError("private runtime-capture root traverses a symlink")
    return root


def require_direct_child(
    repository: pathlib.Path,
    output_dir: pathlib.Path,
    *,
    must_exist: bool,
) -> pathlib.Path:
    require_canonical_absolute(output_dir, "output directory")
    root = private_root(repository)
    if output_dir.parent != root or OUTPUT_NAME.fullmatch(output_dir.name) is None:
        raise ValueError(
            "output directory must be one safe direct child of "
            "artifacts/runtime-captures"
        )
    if must_exist:
        require_owned_mode(output_dir, "private output directory", 0o700, directory=True)
        if output_dir.resolve(strict=True) != output_dir:
            raise ValueError("private output directory traverses a symlink")
    elif output_dir.exists() or output_dir.is_symlink():
        raise ValueError("refusing to reuse an existing output directory")
    return output_dir


def prepare_output_dir(
    repository: pathlib.Path,
    output_dir: pathlib.Path,
) -> None:
    output_dir = require_direct_child(
        repository,
        output_dir,
        must_exist=False,
    )
    os.mkdir(output_dir, 0o700)
    os.chmod(output_dir, 0o700)
    require_direct_child(repository, output_dir, must_exist=True)


def parse_key_values(lines: list[str], label: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        if line.count("=") != 1:
            raise ValueError(f"{label} contains a malformed field")
        name, value = line.split("=", 1)
        if not name or name in values:
            raise ValueError(f"{label} contains a duplicate or empty field")
        values[name] = value
    return values


def require_host_block(lines: list[str], begin: int, end: int) -> None:
    values = parse_key_values(lines[begin + 1 : end], "host block")
    expected_static = {
        "mac": HOST_MAC,
        "host_address": HOST_ADDRESS,
        "device_address": DEVICE_ADDRESS,
        "capture_transport": "direct-usb-tcp-2323",
        "authentication": "none",
        "encryption": "none",
        "fdt_source": "/sys/firmware/fdt",
        "device_partition_read": "no",
        "hardware_write": "no",
        "i2c_transaction_or_controller_control": "none",
        "regulator_control": "none",
        "cpu_hotplug_control": "none",
        "watchdog_control": "none",
        "reboot_executed": "no",
        "power_state_transition_requested": "no",
    }
    if set(values) != set(expected_static) | {"interface", "route_interface"}:
        raise ValueError("host block inventory changed")
    for name, wanted in expected_static.items():
        if values[name] != wanted:
            raise ValueError(f"host block differs: {name}")
    interface = values["interface"]
    if (
        INTERFACE.fullmatch(interface) is None
        or values["route_interface"] != interface
    ):
        raise ValueError("host block does not bind the route to one safe interface")


def canonical_uuid(value: str) -> str:
    if UUID.fullmatch(value) is None:
        raise ValueError("boot ID is not one lowercase RFC4122 UUID")
    parsed = uuid.UUID(value)
    if str(parsed) != value:
        raise ValueError("boot ID is not canonical")
    return value


def decimal_size(value: str, label: str) -> int:
    if not value.isdecimal() or (len(value) > 1 and value.startswith("0")):
        raise ValueError(f"{label} is not one canonical decimal size")
    size = int(value)
    if not 40 <= size <= MAX_FDT_SIZE:
        raise ValueError(f"{label} is outside the bounded FDT range")
    return size


def decode_base64(lines: list[str]) -> bytes:
    if not lines:
        raise ValueError("base64 payload is empty")
    for index, line in enumerate(lines):
        if (
            BASE64_LINE.fullmatch(line) is None
            or len(line) % 4
            or not 4 <= len(line) <= 76
            or (index < len(lines) - 1 and len(line) != 76)
            or (index < len(lines) - 1 and "=" in line)
        ):
            raise ValueError("base64 payload has invalid wrapping, alphabet, or padding")
    encoded = "".join(lines)
    if "=" in encoded[:-2] or len(encoded) % 4:
        raise ValueError("base64 payload padding is not canonical")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("base64 payload is invalid") from exc
    if base64.b64encode(decoded).decode("ascii") != encoded:
        raise ValueError("base64 payload is not the canonical encoding")
    return decoded


def require_fdt_header(data: bytes) -> None:
    if len(data) < 40:
        raise ValueError("decoded FDT is shorter than its header")
    (
        magic,
        total_size,
        off_struct,
        off_strings,
        off_mem_rsvmap,
        version,
        last_compatible_version,
        _boot_cpuid_phys,
        size_strings,
        size_struct,
    ) = struct.unpack(">10I", data[:40])
    if magic != FDT_MAGIC:
        raise ValueError("decoded FDT magic is not d00dfeed")
    if total_size != len(data):
        raise ValueError("decoded FDT header totalsize differs from file size")
    if version < 16 or last_compatible_version > version:
        raise ValueError("decoded FDT version contract is malformed")
    if off_mem_rsvmap % 8 or off_struct % 4:
        raise ValueError("decoded FDT block alignment is malformed")
    if (
        not 40 <= off_mem_rsvmap <= total_size
        or not 40 <= off_struct <= total_size
        or not 40 <= off_strings <= total_size
        or off_struct + size_struct > total_size
        or off_strings + size_strings > total_size
    ):
        raise ValueError("decoded FDT block bounds are malformed")


def read_transcript(path: pathlib.Path) -> tuple[str, list[str]]:
    info = require_owned_mode(
        path,
        "private live-FDT transcript",
        0o600,
        directory=False,
        nonempty=True,
    )
    if info.st_size > MAX_TRANSCRIPT_SIZE:
        raise ValueError("private live-FDT transcript exceeds its bound")
    raw = path.read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeError as exc:
        raise ValueError("private live-FDT transcript is not ASCII") from exc
    if "\r" in text or "\0" in text or any(
        ord(character) < 0x20 and character not in "\n\t" for character in text
    ):
        raise ValueError("private live-FDT transcript contains control framing")
    return text, text.splitlines()


def parse_transcript(
    transcript: pathlib.Path,
    expected_config_sha256: str,
) -> tuple[CaptureResult, bytes]:
    if HEX256.fullmatch(expected_config_sha256) is None:
        raise ValueError("expected AP configuration is not one lowercase SHA-256")
    text, lines = read_transcript(transcript)
    if not text.startswith(HOST_BEGIN + "\n"):
        raise ValueError("host block is not the first transcript record")
    for marker in MARKERS:
        if text.count(marker) != 1 or lines.count(marker) != 1:
            raise ValueError(f"transcript marker is absent, duplicated, or contaminated: {marker}")
    positions = [lines.index(marker) for marker in MARKERS]
    if positions != sorted(positions):
        raise ValueError("transcript markers are out of order")
    (
        host_begin,
        host_end,
        capture_begin,
        payload_begin,
        payload_end,
        capture_end,
    ) = positions
    if host_begin != 0:
        raise ValueError("host block position differs")
    require_host_block(lines, host_begin, host_end)
    prelude = lines[host_end + 1 : capture_begin]
    if prelude.count(USB_BANNER) != 1:
        raise ValueError("exact inherited USB shell banner is absent or duplicated")

    before_payload = lines[capture_begin + 1 : payload_begin]
    after_payload = lines[payload_end + 1 : capture_end]
    if len(before_payload) != 4 or len(after_payload) != 3:
        raise ValueError("capture metadata grammar changed")
    before = parse_key_values(before_payload, "pre-transfer metadata")
    after = parse_key_values(after_payload, "post-transfer metadata")
    if list(before) != [
        "boot_id_pre",
        "config_sha256",
        "fdt_sha256_pre",
        "fdt_size_pre",
    ]:
        raise ValueError("pre-transfer metadata order or inventory changed")
    if list(after) != [
        "boot_id_post",
        "fdt_sha256_post",
        "fdt_size_post",
    ]:
        raise ValueError("post-transfer metadata order or inventory changed")

    boot_id = canonical_uuid(before["boot_id_pre"])
    if canonical_uuid(after["boot_id_post"]) != boot_id:
        raise ValueError("boot ID changed across the live-FDT transfer")
    if before["config_sha256"] != expected_config_sha256:
        raise ValueError("live kernel configuration is not exact Candidate AP")
    for name in ("fdt_sha256_pre", "fdt_sha256_post"):
        if HEX256.fullmatch(
            before[name] if name in before else after[name]
        ) is None:
            raise ValueError("remote live-FDT SHA-256 is malformed")
    if before["fdt_sha256_pre"] != after["fdt_sha256_post"]:
        raise ValueError("remote live-FDT hash changed across the transfer")
    pre_size = decimal_size(before["fdt_size_pre"], "pre-transfer FDT size")
    post_size = decimal_size(after["fdt_size_post"], "post-transfer FDT size")
    if pre_size != post_size:
        raise ValueError("remote live-FDT size changed across the transfer")

    data = decode_base64(lines[payload_begin + 1 : payload_end])
    if len(data) != pre_size:
        raise ValueError("decoded live-FDT size differs from both remote samples")
    live_hash = digest(data)
    if live_hash != before["fdt_sha256_pre"]:
        raise ValueError("decoded live-FDT hash differs from both remote samples")
    require_fdt_header(data)
    return CaptureResult(boot_id, live_hash, len(data)), data


def write_private_fdt(path: pathlib.Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to overwrite a private live-FDT file")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while preserving private live FDT")
            view = view[written:]
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise
    else:
        os.close(descriptor)
    try:
        info = require_owned_mode(
            path,
            "private decoded live FDT",
            0o600,
            directory=False,
            nonempty=True,
        )
        if info.st_size != len(data) or digest(path.read_bytes()) != digest(data):
            raise ValueError("private decoded live FDT failed local readback")
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def decode_capture(
    repository: pathlib.Path,
    output_dir: pathlib.Path,
    expected_config_sha256: str,
) -> CaptureResult:
    output_dir = require_direct_child(repository, output_dir, must_exist=True)
    transcript = output_dir / TRANSCRIPT_NAME
    fdt = output_dir / FDT_NAME
    result, data = parse_transcript(transcript, expected_config_sha256)
    write_private_fdt(fdt, data)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--repository", required=True, type=pathlib.Path)
    prepare.add_argument("--output-dir", required=True, type=pathlib.Path)

    decode = subparsers.add_parser("decode")
    decode.add_argument("--repository", required=True, type=pathlib.Path)
    decode.add_argument("--output-dir", required=True, type=pathlib.Path)
    decode.add_argument("--expected-config-sha256", required=True)

    args = parser.parse_args()
    try:
        if args.operation == "prepare":
            prepare_output_dir(args.repository, args.output_dir)
            return 0
        result = decode_capture(
            args.repository,
            args.output_dir,
            args.expected_config_sha256,
        )
    except (OSError, UnicodeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"boot_id={result.boot_id}")
    print(f"live_fdt_sha256={result.live_fdt_sha256}")
    print(f"live_fdt_size={result.live_fdt_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
