#!/usr/bin/env python3
"""Validate Cassini's fixed six-transaction helper source and AArch64 ELF."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import stat
import struct
import sys

sys.dont_write_bytecode = True
import candidate_cassini as cc


REQUIRED_SOURCE_TOKENS = (
    '#define CASSINI_I2C_OF_SUFFIX "/i2c@1100e000"',
    "#define CASSINI_I2C_ADDR 0x69U",
    "#define CASSINI_I2C_RDWR 0x0707UL",
    "#define CASSINI_I2C_M_RD 0x0001U",
    "#define CASSINI_PASSES 2U",
    "#define CASSINI_REGISTER_COUNT 3U",
    "0x05U, 0x06U, 0x47U",
    "0xd9U, 0xd0U, 0xc0U",
    ".addr = CASSINI_I2C_ADDR",
    ".flags = 0U",
    ".flags = CASSINI_I2C_M_RD",
    ".nmsgs = CASSINI_MESSAGE_COUNT",
    "ioctl(descriptor, CASSINI_I2C_RDWR, &request)",
    "if (argc != 1)",
    "if (kmsg_fd < 0)",
    "GEMINI_CASSINI_PROBE_FAIL stage=kmsg-open transactions=0",
    "static bool emit_marker(int kmsg_fd, const char *format, ...)",
    'if (dprintf(kmsg_fd, "<6>%s\\n", line) != length + 4)',
    "return true;",
    "for (pass = 0U; pass < CASSINI_PASSES; pass++)",
    "for (index = 0U; index < CASSINI_REGISTER_COUNT; index++)",
    "errno = 0;\n\t\tentry = readdir(directory);",
    "result = errno == 0 && matches == 1U ? 0 : -1;",
    "memcmp(values[0], values[1], CASSINI_REGISTER_COUNT)",
    "memcmp(values[0], cassini_expected, CASSINI_REGISTER_COUNT)",
)

REQUIRED_BINARY_MARKERS = (
    b"/sys/class/i2c-dev\0",
    b"/i2c@1100e000\0",
    b"/dev/%s\0",
    (
        b"GEMINI_CASSINI_PROBE_BEGIN adapter=%s of=/i2c@1100e000 "
        b"address=0x69 passes=2 registers=0x05,0x06,0x47\0"
    ),
    (
        b"GEMINI_CASSINI_TRANSACTION_BEGIN pass=%u register=0x%02x "
        b"transaction=%u address=0x69 messages=2\0"
    ),
    (
        b"GEMINI_CASSINI_READ pass=%u register=0x%02x value=0x%02x "
        b"transaction=%u\0"
    ),
    (
        b"GEMINI_CASSINI_PROBE_PASS first=d9,d0,c0 second=d9,d0,c0 "
        b"transactions=6 page_con=untouched\0"
    ),
    b"GEMINI_CASSINI_PROBE_FAIL stage=arguments transactions=0\0",
    b"GEMINI_CASSINI_PROBE_FAIL stage=kmsg-open transactions=0\0",
    b"GEMINI_CASSINI_PROBE_FAIL stage=adapter transactions=0\0",
    b"GEMINI_CASSINI_PROBE_FAIL stage=transfer ",
    b"GEMINI_CASSINI_PROBE_FAIL stage=unstable ",
    b"GEMINI_CASSINI_PROBE_FAIL stage=signature ",
)

FORBIDDEN_SOURCE_TOKENS = (
    "PAGE_CON",
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
    "while ((entry = readdir(directory)) != NULL)",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def require_once(text: str, token: str, label: str) -> None:
    count = text.count(token)
    if count != 1:
        raise ValueError(f"{label} count changed: expected 1, found {count}")


def audit_source(data: bytes) -> None:
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("probe source is not UTF-8") from exc

    for token in REQUIRED_SOURCE_TOKENS:
        if token not in text:
            raise ValueError(f"probe source lost required token: {token}")
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in text:
            raise ValueError(f"probe source contains forbidden token: {token}")

    require_once(text, "#define CASSINI_I2C_ADDR 0x69U", "I2C address")
    require_once(text, "#define CASSINI_PASSES 2U", "pass count")
    require_once(text, "0x05U, 0x06U, 0x47U", "register sequence")
    require_once(text, "0xd9U, 0xd0U, 0xc0U", "expected signature")
    require_once(
        text,
        "ioctl(descriptor, CASSINI_I2C_RDWR, &request)",
        "I2C_RDWR call site",
    )
    require_once(
        text,
        '"GEMINI_CASSINI_TRANSACTION_BEGIN pass=%u register=0x%02x '
        'transaction=%u address=0x69 messages=2"',
        "durable pre-transaction marker",
    )
    require_once(
        text,
        '"GEMINI_CASSINI_READ pass=%u register=0x%02x value=0x%02x '
        'transaction=%u"',
        "post-read marker",
    )
    require_once(text, "static int read_one_register(", "transaction helper")
    require_once(
        text,
        "errno = 0;\n\t\tentry = readdir(directory);",
        "readdir-local errno reset",
    )
    require_once(
        text,
        "result = errno == 0 && matches == 1U ? 0 : -1;",
        "readdir result check",
    )
    if text.count("if (!emit_marker(") != 4:
        raise ValueError(
            "BEGIN, transaction-begin, post-read, and PASS markers "
            "must be fail-closed"
        )
    kmsg_write = text.index(
        'if (dprintf(kmsg_fd, "<6>%s\\n", line) != length + 4)'
    )
    stdout_write = text.index('if (printf("%s\\n", line) >= 0)')
    if kmsg_write >= stdout_write:
        raise ValueError("persistent kmsg marker must precede stdout mirroring")
    probe_begin = text.index('"GEMINI_CASSINI_PROBE_BEGIN ')
    transaction_begin = text.index('"GEMINI_CASSINI_TRANSACTION_BEGIN ')
    transfer = text.index("transfer_result = read_one_register(")
    post_read = text.index('"GEMINI_CASSINI_READ ')
    if not probe_begin < transaction_begin < transfer < post_read:
        raise ValueError("durable marker and I2C transfer ordering changed")
    for marker, label in (
        ('"GEMINI_CASSINI_PROBE_BEGIN ', "probe BEGIN"),
        ('"GEMINI_CASSINI_TRANSACTION_BEGIN ', "transaction BEGIN"),
        ('"GEMINI_CASSINI_READ ', "post-read"),
    ):
        marker_offset = text.index(marker)
        guard_offset = text.rfind("if (!emit_marker(", 0, marker_offset)
        if guard_offset < 0 or marker_offset - guard_offset > 64:
            raise ValueError(f"{label} marker is not guarded by kmsg success")
    if text.count(".addr = CASSINI_I2C_ADDR") != 2:
        raise ValueError("both and only both I2C messages must use address 0x69")
    if text.count(".len = 1U") != 2:
        raise ValueError("both I2C messages must be exactly one byte")
    if re.search(r"\bcassini_registers\s*\[[^\]]+\]\s*=", text) is None:
        raise ValueError("fixed register array is absent")
    if "cassini_registers[index]" not in text:
        raise ValueError("transaction pointer is not sourced from fixed registers")


def validate_source(path: pathlib.Path) -> bytes:
    data = regular(path, "Cassini probe source")
    if digest(data) != cc.PROBE_SOURCE_SHA256:
        raise ValueError("source-pinned Cassini probe changed")
    audit_source(data)
    return data


def elf_header(data: bytes) -> tuple[int, int, int]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ValueError("probe binary is not ELF")
    if data[4:6] != b"\x02\x01":
        raise ValueError("probe binary is not little-endian ELF64")
    elf_type, machine = struct.unpack_from("<HH", data, 16)
    program_offset = struct.unpack_from("<Q", data, 32)[0]
    program_size, program_count = struct.unpack_from("<HH", data, 54)
    if machine != 183:
        raise ValueError("probe binary is not AArch64")
    if elf_type != 2:
        raise ValueError("probe binary is not a fixed-address static executable")
    if program_size < 56 or program_count == 0:
        raise ValueError("probe binary has an invalid program-header table")
    if program_offset + program_size * program_count > len(data):
        raise ValueError("probe binary program headers are out of bounds")
    return program_offset, program_size, program_count


def validate_binary(path: pathlib.Path) -> bytes:
    data = regular(path, "Cassini probe binary")
    program_offset, program_size, program_count = elf_header(data)
    for index in range(program_count):
        offset = program_offset + index * program_size
        program_type = struct.unpack_from("<I", data, offset)[0]
        if program_type == 3:
            raise ValueError("probe binary contains a dynamic interpreter")
    for marker in REQUIRED_BINARY_MARKERS:
        if marker not in data:
            raise ValueError(f"probe binary lacks marker: {marker!r}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=pathlib.Path)
    parser.add_argument("--binary", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        source = validate_source(args.source)
        binary = validate_binary(args.binary)
    except (OSError, UnicodeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=cassini-fixed-direct-address-probe")
    print(f"source_sha256={digest(source)}")
    print(f"binary_sha256={digest(binary)}")
    print("architecture=linux-aarch64-static")
    print("arguments=none")
    print("adapter_of_path=/i2c@1100e000")
    print("address=0x69")
    print("registers=0x05,0x06,0x47")
    print("passes=2")
    print("transactions=6-combined-I2C_RDWR-pointer-read")
    print("expected_signature=d9,d0,c0-twice")
    print("page_con_0x00=unreachable")
    print("automatic_invocation=none")
    print("storage_watchdog_reboot_cpu_control=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
