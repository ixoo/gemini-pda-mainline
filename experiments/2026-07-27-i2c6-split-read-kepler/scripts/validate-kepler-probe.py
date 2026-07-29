#!/usr/bin/env python3
"""Validate Kepler's fixed split-read helper source and AArch64 ELF."""

from __future__ import annotations

import argparse
import pathlib
import stat
import struct
import sys

sys.dont_write_bytecode = True
import candidate_kepler as ck


REQUIRED_SOURCE_TOKENS = (
    '#define KEPLER_I2C_OF_SUFFIX "/i2c@1100e000"',
    "#define KEPLER_I2C_ADDR 0x69U",
    "#define KEPLER_I2C_RDWR 0x0707UL",
    "#define KEPLER_I2C_M_RD 0x0001U",
    "#define KEPLER_REGISTER 0x05U",
    "#define KEPLER_PAIR_COUNT 2U",
    "0xa5U, 0x5aU",
    ".addr = KEPLER_I2C_ADDR",
    ".nmsgs = 1U",
    "one_message_ioctl(descriptor, 0U, &pointer)",
    "one_message_ioctl(descriptor, KEPLER_I2C_M_RD, &value)",
    'observation->result_class = "tx-result-not-one";',
    'observation->result_class = "rx-result-not-one";',
    "if (observation->post_diff_mask == 0U)",
    'return "split-stable-d9";',
    "if (argc != 1)",
)

REQUIRED_BINARY_MARKERS = (
    b"/sys/class/i2c-dev\0",
    b"/i2c@1100e000\0",
    b"/dev/%s\0",
    (
        b"GEMINI_KEPLER_BEGIN adapter=%s of=/i2c@1100e000 "
        b"address=0x69 register=0x05 pairs=2 calls=4 layout=split\n\0"
    ),
    (
        b"GEMINI_KEPLER_TX pair=%u call=%u address=0x69 flags=0x0000 "
        b"len=1 pointer=0x05 result=%d errno=%d\n\0"
    ),
    (
        b"GEMINI_KEPLER_RX pair=%u call=%u address=0x69 flags=0x0001 "
        b"len=1 pre=0x%02x post=0x%02x result=%d errno=%d "
        b"post_differs_pre=%s\n\0"
    ),
    b"split-all-equal-pre\0",
    b"split-mixed-equal-pre\0",
    b"split-stable-d9\0",
    b"split-stable-other\0",
    b"split-unstable\0",
    b"tx-result-not-one\0",
    b"rx-result-not-one\0",
)

FORBIDDEN_SOURCE_TOKENS = (
    "I2C_SLAVE",
    "I2C_SMBUS",
    "i2cset",
    "i2cget",
    "i2cdump",
    "/dev/mmc",
    "/dev/watchdog",
    "/dev/mem",
    "/sys/devices/system/cpu",
    "reboot(",
    "system(",
    "exec",
    "fork(",
    "usleep(",
    "sleep(",
    "nanosleep(",
    "0x00U",
    "0x06U",
    "0x47U",
)


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def audit_source(data: bytes, allow_unresolved: bool) -> None:
    text = data.decode("utf-8")
    if not allow_unresolved:
        ck.require_pins(binary=False)
        if ck.digest(data) != ck.PROBE_SOURCE_SHA256:
            raise ValueError("source-pinned Kepler probe changed")
    for token in REQUIRED_SOURCE_TOKENS:
        if token not in text:
            raise ValueError(f"probe source lost required token: {token}")
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in text:
            raise ValueError(f"probe source contains forbidden token: {token}")
    if text.count("return ioctl(descriptor, KEPLER_I2C_RDWR, &request);") != 1:
        raise ValueError("I2C_RDWR syscall call site changed")
    if text.count(".addr = KEPLER_I2C_ADDR") != 1:
        raise ValueError("message address contract changed")
    if text.count(".len = 1U") != 1 or text.count(".nmsgs = 1U") != 1:
        raise ValueError("single-message one-byte contract changed")
    tx = text.index("one_message_ioctl(descriptor, 0U, &pointer)")
    rx = text.index("one_message_ioctl(descriptor, KEPLER_I2C_M_RD, &value)")
    if tx >= rx:
        raise ValueError("pointer-write/read ordering changed")
    between = text[tx:rx]
    if 'observation->result_class = "tx-result-not-one";' not in between:
        raise ValueError("TX non-one fail-closed boundary changed")


def elf_header(data: bytes) -> tuple[int, int, int]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ValueError("probe binary is not ELF")
    if data[4:6] != b"\x02\x01":
        raise ValueError("probe binary is not little-endian ELF64")
    elf_type, machine = struct.unpack_from("<HH", data, 16)
    program_offset = struct.unpack_from("<Q", data, 32)[0]
    program_size, program_count = struct.unpack_from("<HH", data, 54)
    if machine != 183 or elf_type != 2:
        raise ValueError("probe binary is not static fixed-address AArch64")
    if program_size < 56 or program_count == 0:
        raise ValueError("probe binary program-header table is invalid")
    if program_offset + program_size * program_count > len(data):
        raise ValueError("probe binary program headers are out of bounds")
    return program_offset, program_size, program_count


def audit_binary(data: bytes, allow_unresolved: bool) -> None:
    if not allow_unresolved:
        ck.require_pins()
        if len(data) != ck.PROBE_BINARY_SIZE:
            raise ValueError("calibrated Kepler probe size changed")
        if ck.digest(data) != ck.PROBE_BINARY_SHA256:
            raise ValueError("calibrated Kepler probe binary changed")
    offset, size, count = elf_header(data)
    for index in range(count):
        program_type = struct.unpack_from("<I", data, offset + index * size)[0]
        if program_type == 3:
            raise ValueError("probe binary contains a dynamic interpreter")
    for marker in REQUIRED_BINARY_MARKERS:
        if marker not in data:
            raise ValueError(f"probe binary lacks marker: {marker!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=pathlib.Path)
    parser.add_argument("--binary", required=True, type=pathlib.Path)
    parser.add_argument("--allow-unresolved-binary", action="store_true")
    args = parser.parse_args()
    try:
        source = read_regular(args.source, "Kepler probe source")
        binary = read_regular(args.binary, "Kepler probe binary")
        audit_source(source, args.allow_unresolved_binary)
        audit_binary(binary, args.allow_unresolved_binary)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=kepler-static-aarch64-split-read-helper")
    print(f"source_sha256={ck.digest(source)}")
    print(f"binary_sha256={ck.digest(binary)}")
    print(f"binary_size={len(binary)}")
    print("i2c_address=0x69")
    print("pointer=0x05")
    print("pairs=2")
    print("ioctl_calls=4")
    print("messages_per_ioctl=1")
    print("stop_between_pointer_and_read=yes")
    print("forbidden_scope=storage,watchdog,reboot,cpu,regulator,page-con")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
