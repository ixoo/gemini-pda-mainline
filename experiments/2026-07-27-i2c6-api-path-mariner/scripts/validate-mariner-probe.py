#!/usr/bin/env python3
"""Validate Mariner's fixed write/read helper source and AArch64 ELF."""

from __future__ import annotations

import argparse
import pathlib
import stat
import struct
import sys

sys.dont_write_bytecode = True
import candidate_mariner as ck


REQUIRED_SOURCE_TOKENS = (
    '#define MARINER_I2C_OF_SUFFIX "/i2c@1100e000"',
    "#define MARINER_I2C_ADDR 0x69U",
    "#define MARINER_I2C_SLAVE 0x0703UL",
    "#define MARINER_PAIR_COUNT 2U",
    "0x3cU, 0xa6U",
    "0x06U, 0x47U",
    "(unsigned long)MARINER_I2C_ADDR",
    "write(descriptor, &pointer, 1U)",
    "read(descriptor, &value, 1U)",
    'return "raw-expected-live";',
    'return "raw-pointer-echo";',
    'return "raw-lag";',
    'return "raw-zero";',
    'return "raw-other";',
    'observation->result_class = "raw-error";',
    "if (argc != 1)",
)

REQUIRED_BINARY_MARKERS = (
    b"/sys/class/i2c-dev\0",
    b"/i2c@1100e000\0",
    b"/dev/%s\0",
    (
        b"GEMINI_MARINER_BEGIN adapter=%s of=/i2c@1100e000 "
        b"address=0x69 registers=06,47 selection_ioctls=1 "
        b"bus_syscalls=4 api=write-read\n\0"
    ),
    (
        b"GEMINI_MARINER_SELECT call=1 request=I2C_SLAVE "
        b"address=0x69 result=%d errno=%d\n\0"
    ),
    (
        b"GEMINI_MARINER_WRITE pair=%u bus_call=%u address=0x69 "
        b"len=1 pointer=0x%02x result=%zd errno=%d\n\0"
    ),
    (
        b"GEMINI_MARINER_READ pair=%u bus_call=%u address=0x69 len=1 "
        b"user_pre=0x%02x post=0x%02x result=%zd errno=%d "
        b"post_differs_user_pre=%s\n\0"
    ),
    b"raw-expected-live\0",
    b"raw-pointer-echo\0",
    b"raw-lag\0",
    b"raw-zero\0",
    b"raw-other\0",
    b"raw-error\0",
)

FORBIDDEN_SOURCE_TOKENS = (
    "I2C_RDWR",
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
    "PAGE_CON",
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
            raise ValueError("source-pinned Mariner probe changed")
    for token in REQUIRED_SOURCE_TOKENS:
        if token not in text:
            raise ValueError(f"probe source lost required token: {token}")
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in text:
            raise ValueError(f"probe source contains forbidden token: {token}")
    if text.count(
        "ioctl(descriptor, MARINER_I2C_SLAVE,\n"
        "\t\t      (unsigned long)MARINER_I2C_ADDR)"
    ) != 1:
        raise ValueError("single I2C_SLAVE selection call site changed")
    if text.count("write(descriptor, &pointer, 1U)") != 1:
        raise ValueError("single looped pointer-write call site changed")
    if text.count("read(descriptor, &value, 1U)") != 1:
        raise ValueError("single looped one-byte read call site changed")
    exact_lag_predicate = (
        "if (observation->post[0] == 0x47U &&\n"
        "\t    observation->post[1] == 0x06U)\n"
        '\t\treturn "raw-lag";'
    )
    if text.count(exact_lag_predicate) != 1 or "0x05U" in text:
        raise ValueError("exact previous-write lag predicate changed")
    select = text.index(
        "ioctl(descriptor, MARINER_I2C_SLAVE,\n"
        "\t\t      (unsigned long)MARINER_I2C_ADDR)"
    )
    write = text.index("write(descriptor, &pointer, 1U)")
    read = text.index("read(descriptor, &value, 1U)")
    if not select < write < read:
        raise ValueError("selection/write/read ordering changed")


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
            raise ValueError("calibrated Mariner probe size changed")
        if ck.digest(data) != ck.PROBE_BINARY_SHA256:
            raise ValueError("calibrated Mariner probe binary changed")
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
        source = read_regular(args.source, "Mariner probe source")
        binary = read_regular(args.binary, "Mariner probe binary")
        audit_source(source, args.allow_unresolved_binary)
        audit_binary(binary, args.allow_unresolved_binary)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=mariner-static-aarch64-write-read-helper")
    print(f"source_sha256={ck.digest(source)}")
    print(f"binary_sha256={ck.digest(binary)}")
    print(f"binary_size={len(binary)}")
    print("i2c_address=0x69")
    print("selection_ioctls=1")
    print("bus_syscalls=4")
    print("order=write06,read1,write47,read1")
    print("user_prefills=0x3c,0xa6")
    print("forbidden_scope=storage,watchdog,reboot,cpu,regulator,page-con")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
