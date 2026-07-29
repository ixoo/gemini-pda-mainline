#!/usr/bin/env python3
"""Validate Voyager's fixed split-read helper source and AArch64 ELF."""

from __future__ import annotations

import argparse
import pathlib
import stat
import struct
import sys

sys.dont_write_bytecode = True
import candidate_voyager as ck


REQUIRED_SOURCE_TOKENS = (
    '#define VOYAGER_I2C_OF_SUFFIX "/i2c@1100e000"',
    "#define VOYAGER_I2C_ADDR 0x69U",
    "#define VOYAGER_I2C_RDWR 0x0707UL",
    "#define VOYAGER_I2C_M_RD 0x0001U",
    "#define VOYAGER_PAIR_COUNT 2U",
    "0x3cU, 0xa6U",
    "0x06U, 0x47U",
    "0xd0U, 0xc0U",
    ".addr = VOYAGER_I2C_ADDR",
    ".nmsgs = 1U",
    "one_message_ioctl(descriptor, 0U, &pointer)",
    "one_message_ioctl(descriptor, VOYAGER_I2C_M_RD, &value)",
    'observation->result_class = "tx-result-not-one";',
    'observation->result_class = "rx-result-not-one";',
    "if (observation->post_diff_mask == 0U)",
    'return "split-expected-live";',
    'return "split-pointer-echo";',
    "if (argc != 1)",
)

REQUIRED_BINARY_MARKERS = (
    b"/sys/class/i2c-dev\0",
    b"/i2c@1100e000\0",
    b"/dev/%s\0",
    (
        b"GEMINI_VOYAGER_BEGIN adapter=%s of=/i2c@1100e000 "
        b"address=0x69 registers=06,47 pairs=2 calls=4 layout=split\n\0"
    ),
    (
        b"GEMINI_VOYAGER_TX pair=%u call=%u address=0x69 flags=0x0000 "
        b"len=1 pointer=0x%02x result=%d errno=%d\n\0"
    ),
    (
        b"GEMINI_VOYAGER_RX pair=%u call=%u address=0x69 flags=0x0001 "
        b"len=1 pre=0x%02x post=0x%02x result=%d errno=%d "
        b"post_differs_pre=%s\n\0"
    ),
    b"split-all-equal-pre\0",
    b"split-mixed-equal-pre\0",
    b"split-expected-live\0",
    b"split-pointer-echo\0",
    b"split-stable-other\0",
    b"split-unstable-other\0",
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
    "0x05U",
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
            raise ValueError("source-pinned Voyager probe changed")
    for token in REQUIRED_SOURCE_TOKENS:
        if token not in text:
            raise ValueError(f"probe source lost required token: {token}")
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in text:
            raise ValueError(f"probe source contains forbidden token: {token}")
    if text.count("return ioctl(descriptor, VOYAGER_I2C_RDWR, &request);") != 1:
        raise ValueError("I2C_RDWR syscall call site changed")
    if text.count(".addr = VOYAGER_I2C_ADDR") != 1:
        raise ValueError("message address contract changed")
    if text.count(".len = 1U") != 1 or text.count(".nmsgs = 1U") != 1:
        raise ValueError("single-message one-byte contract changed")
    tx = text.index("one_message_ioctl(descriptor, 0U, &pointer)")
    rx = text.index("one_message_ioctl(descriptor, VOYAGER_I2C_M_RD, &value)")
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
            raise ValueError("calibrated Voyager probe size changed")
        if ck.digest(data) != ck.PROBE_BINARY_SHA256:
            raise ValueError("calibrated Voyager probe binary changed")
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
        source = read_regular(args.source, "Voyager probe source")
        binary = read_regular(args.binary, "Voyager probe binary")
        audit_source(source, args.allow_unresolved_binary)
        audit_binary(binary, args.allow_unresolved_binary)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=voyager-static-aarch64-split-read-helper")
    print(f"source_sha256={ck.digest(source)}")
    print(f"binary_sha256={ck.digest(binary)}")
    print(f"binary_size={len(binary)}")
    print("i2c_address=0x69")
    print("pointers=0x06,0x47")
    print("receive_prefills=0x3c,0xa6")
    print("pairs=2")
    print("ioctl_calls=4")
    print("messages_per_ioctl=1")
    print("stop_between_pointer_and_read=yes")
    print("forbidden_scope=storage,watchdog,reboot,cpu,regulator,page-con")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
