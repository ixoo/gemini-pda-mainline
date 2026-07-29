#!/usr/bin/env python3
"""Validate Photon's fixed receive-sentinel helper source and AArch64 ELF."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import stat
import struct
import sys

sys.dont_write_bytecode = True
import candidate_photon as cp


REQUIRED_SOURCE_TOKENS = (
    '#define PHOTON_I2C_OF_SUFFIX "/i2c@1100e000"',
    "#define PHOTON_I2C_ADDR 0x69U",
    "#define PHOTON_I2C_RDWR 0x0707UL",
    "#define PHOTON_I2C_M_RD 0x0001U",
    "#define PHOTON_PASSES 2U",
    "#define PHOTON_REGISTER_COUNT 3U",
    "0x05U, 0x06U, 0x47U",
    "0xd9U, 0xd0U, 0xc0U, 0xd9U, 0xd0U, 0xc0U",
    "0xa1U, 0xb2U, 0xc3U, 0xd4U, 0xe5U, 0xf6U",
    ".addr = PHOTON_I2C_ADDR",
    ".flags = 0U",
    ".flags = PHOTON_I2C_M_RD",
    ".nmsgs = PHOTON_MESSAGE_COUNT",
    "ioctl(descriptor, PHOTON_I2C_RDWR, &request)",
    "if (argc != 1)",
    "if (kmsg_fd < 0)",
    "values[transaction] = prefill;",
    "if (values[transaction] != prefill)",
    "post_diff_mask |= 1U << transaction;",
    "if (post_diff_mask == 0U)",
    "for (transaction = 0U; transaction < PHOTON_TRANSACTION_COUNT;",
    "errno = 0;\n\t\tentry = readdir(directory);",
    "result = errno == 0 && matches == 1U ? 0 : -1;",
)

REQUIRED_BINARY_MARKERS = (
    b"/sys/class/i2c-dev\0",
    b"/i2c@1100e000\0",
    b"/dev/%s\0",
    (
        b"GEMINI_PHOTON_BEGIN adapter=%s of=/i2c@1100e000 address=0x69 "
        b"transactions=6 registers=05,06,47,05,06,47 "
        b"prefills=a1,b2,c3,d4,e5,f6\0"
    ),
    (
        b"GEMINI_PHOTON_PRE transaction=%u pass=%u register=0x%02x "
        b"prefill=0x%02x address=0x69 messages=2\0"
    ),
    (
        b"GEMINI_PHOTON_READ transaction=%u pass=%u register=0x%02x "
        b"pre=0x%02x post=0x%02x post_differs_pre=%s\0"
    ),
    (
        b"GEMINI_PHOTON_RESULT class=%s completed=%u ioctl_result=%d "
        b"errno=%d pre=a1,b2,c3,d4,e5,f6 post=%s post_diff_mask=0x%02x "
        b"page_con_access=none\0"
    ),
    b"post-reference-tuple\0",
    b"post-all-zero\0",
    b"post-pass-tuples-equal-other\0",
    b"post-none-equal-pre-pass-tuples-differ\0",
    b"post-all-equal-pre\0",
    b"post-mixed-equal-pre\0",
    b"ioctl-result-not-two\0",
)

FORBIDDEN_BINARY_MARKERS = (
    b"overwritten=",
    b"overwrite_mask=",
    b"page_con=untouched",
    b"expected-signature\0",
    b"all-overwritten-zero\0",
    b"stable-different\0",
    b"all-sentinels-preserved\0",
    b"partial-sentinel-match-unstable\0",
    b"unstable-different\0",
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
    "while ((entry = readdir(directory)) != NULL)",
    'status = "sentinel-survived"',
    "overwritten=",
    "overwrite_mask",
    "page_con=untouched",
    "expected-signature",
    "all-overwritten-zero",
    "stable-different",
    "all-sentinels-preserved",
    "partial-sentinel-match-unstable",
    "unstable-different",
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

    require_once(text, "#define PHOTON_I2C_ADDR 0x69U", "I2C address")
    require_once(text, "#define PHOTON_PASSES 2U", "pass count")
    require_once(text, "0x05U, 0x06U, 0x47U", "register sequence")
    require_once(
        text,
        "0xa1U, 0xb2U, 0xc3U, 0xd4U, 0xe5U, 0xf6U",
        "sentinel sequence",
    )
    require_once(
        text,
        "ioctl(descriptor, PHOTON_I2C_RDWR, &request)",
        "I2C_RDWR call site",
    )
    require_once(text, "static int read_one_register(", "transaction helper")
    if re.search(
        r"uint8_t\s+values\s*\[[^\]]+\]\s*=", text
    ) is not None:
        raise ValueError("receive array must not have a zero/default initializer")
    if text.count(".addr = PHOTON_I2C_ADDR") != 2:
        raise ValueError("both and only both I2C messages must use address 0x69")
    if text.count(".len = 1U") != 2:
        raise ValueError("both I2C messages must be exactly one byte")
    if text.count("GEMINI_PHOTON_PRE transaction=") != 1:
        raise ValueError("persistent PRE marker call site changed")
    if text.count("GEMINI_PHOTON_RESULT class=%s") != 1:
        raise ValueError("aggregate RESULT marker call site changed")

    prefill_assignment = text.index("values[transaction] = prefill;")
    pre_marker = text.index('"GEMINI_PHOTON_PRE transaction=')
    transfer = text.index("ioctl_result = read_one_register(")
    post_compare = text.index("if (values[transaction] != prefill)")
    stdout_post_compare = text.index(
        '"GEMINI_PHOTON_READ transaction=%u pass=%u register=0x%02x '
        'pre=0x%02x post=0x%02x post_differs_pre=%s"'
    )
    if not (
        prefill_assignment
        < pre_marker
        < transfer
        < post_compare
        < stdout_post_compare
    ):
        raise ValueError(
            "required sentinel-assignment/PRE/ioctl/post-read ordering changed"
        )
    pre_guard = text.rfind("if (!emit_marker(", 0, pre_marker)
    if pre_guard < 0 or pre_marker - pre_guard > 64:
        raise ValueError("PRE marker is not fail-closed before the transfer")
    if "emit_stdout(" not in text:
        raise ValueError("stdout-only per-read evidence is absent")
    if text.count('dprintf(kmsg_fd, "<6>%s\\n", line)') != 1:
        raise ValueError("persistent marker write primitive changed")
    if text.count("read_one_register(") != 2:
        raise ValueError("probe must have one transaction helper and one call site")
    success_start = text.index("\t\tcompleted++;", transfer)
    success_end = text.index(
        "\n\t}\n\n\tif (completed == PHOTON_TRANSACTION_COUNT)",
        success_start,
    )
    if "break;" in text[success_start:success_end]:
        raise ValueError("successful transfer path must complete both passes")


def validate_source(path: pathlib.Path) -> bytes:
    data = regular(path, "Photon probe source")
    if digest(data) != cp.PROBE_SOURCE_SHA256:
        raise ValueError("source-pinned Photon probe changed")
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
    data = regular(path, "Photon probe binary")
    if cp.HEX256.fullmatch(cp.PROBE_BINARY_SHA256) is not None:
        if digest(data) != cp.PROBE_BINARY_SHA256:
            raise ValueError("calibrated Photon probe binary changed")
    program_offset, program_size, program_count = elf_header(data)
    for index in range(program_count):
        offset = program_offset + index * program_size
        program_type = struct.unpack_from("<I", data, offset)[0]
        if program_type == 3:
            raise ValueError("probe binary contains a dynamic interpreter")
    for marker in REQUIRED_BINARY_MARKERS:
        if marker not in data:
            raise ValueError(f"probe binary lacks marker: {marker!r}")
    for marker in FORBIDDEN_BINARY_MARKERS:
        if marker in data:
            raise ValueError(f"probe binary retains superseded marker: {marker!r}")
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

    print("validation=photon-fixed-rx-sentinel-probe")
    print(f"source_sha256={digest(source)}")
    print(f"binary_sha256={digest(binary)}")
    print("architecture=linux-aarch64-static")
    print("arguments=none")
    print("adapter_of_path=/i2c@1100e000")
    print("address=0x69")
    print("registers=0x05,0x06,0x47-twice")
    print("prefills=a1,b2,c3,d4,e5,f6")
    print("transactions=6-combined-I2C_RDWR-pointer-read")
    print("persistent_success_lines=8")
    print("per_read_post_evidence=stdout-only")
    print("complete_success_path_transfer_count=6")
    print("post_equal_pre_does_not_stop=yes")
    print("post_comparison=post-differs-pre,post-diff-mask")
    print("paired_prefills=05:a1/d4,06:b2/e5,47:c3/f6")
    print("page_register_access=none")
    print("automatic_invocation=none")
    print("storage_watchdog_reboot_cpu_control=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
