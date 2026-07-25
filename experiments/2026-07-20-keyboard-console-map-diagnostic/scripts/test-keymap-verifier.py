#!/usr/bin/env python3
"""Exercise the static bkeymap parser without requiring a virtual terminal."""

from __future__ import annotations

import argparse
import os
import pathlib
import stat
import struct
import subprocess
import sys
import tempfile


MAGIC_SIZE = 7
FLAGS_SIZE = 256
HEADER_SIZE = MAGIC_SIZE + FLAGS_SIZE
TABLE_BYTES = 128 * 2


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    return path.read_bytes()


def run(verifier: pathlib.Path, path: pathlib.Path, expected_success: bool) -> bytes:
    result = subprocess.run(
        [os.fspath(verifier), "--check", os.fspath(path)],
        capture_output=True,
        check=False,
    )
    if (result.returncode == 0) != expected_success:
        raise RuntimeError(
            f"unexpected parser status {result.returncode} for {path.name}\n"
            f"stdout={result.stdout.decode(errors='replace')}\n"
            f"stderr={result.stderr.decode(errors='replace')}"
        )
    if not expected_success and b"console-keymap-verify:" not in result.stderr:
        raise RuntimeError(f"parser rejection lacked a diagnostic for {path.name}")
    return result.stdout


def table_offset(data: bytes, wanted: int) -> int:
    if data[MAGIC_SIZE + wanted] != 1:
        raise ValueError(f"table {wanted} is not declared")
    return HEADER_SIZE + sum(data[MAGIC_SIZE : MAGIC_SIZE + wanted]) * TABLE_BYTES


def remove_table(data: bytes, table: int) -> bytes:
    offset = table_offset(data, table)
    result = bytearray(data[:offset] + data[offset + TABLE_BYTES :])
    result[MAGIC_SIZE + table] = 0
    return bytes(result)


def add_hole_table(data: bytes, table: int) -> bytes:
    if data[MAGIC_SIZE + table] != 0:
        raise ValueError(f"table {table} is already declared")
    insertion = HEADER_SIZE + sum(data[MAGIC_SIZE : MAGIC_SIZE + table]) * TABLE_BYTES
    result = bytearray(data[:insertion])
    result.extend(struct.pack("<128H", *([0x0200] * 128)))
    result.extend(data[insertion:])
    result[MAGIC_SIZE + table] = 1
    return bytes(result)


def set_table_entry(data: bytes, table: int, index: int, value: int) -> bytes:
    result = bytearray(data)
    struct.pack_into("<H", result, table_offset(data, table) + index * 2, value)
    return bytes(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier", type=pathlib.Path, required=True)
    parser.add_argument("--keymap", type=pathlib.Path, required=True)
    args = parser.parse_args()

    try:
        verifier_info = args.verifier.lstat()
        if args.verifier.is_symlink() or not stat.S_ISREG(verifier_info.st_mode):
            raise ValueError("verifier is not a regular non-symlink file")
        original = read_regular(args.keymap, "keymap")
        expected = (
            b"keymap_parser=valid tables=8 entries=1024 "
            b"declared=0,1,2,3,4,5,8,12 table3_payload0=K_HOLE "
            b"undeclared=absent\n"
        )
        if run(args.verifier, args.keymap, True) != expected:
            raise RuntimeError("valid parser output changed")

        with tempfile.TemporaryDirectory(prefix="gemini-keymap-parser-") as temp_name:
            temp = pathlib.Path(temp_name)
            invalid_flag = bytearray(original)
            invalid_flag[MAGIC_SIZE + 6] = 2
            zero_tables = bytearray(original)
            zero_tables[MAGIC_SIZE:HEADER_SIZE] = bytes(FLAGS_SIZE)
            extra_flag = bytearray(original)
            extra_flag[MAGIC_SIZE + 6] = 1
            mutants = {
                "bad-magic": b"B" + original[1:],
                "short-header": original[: HEADER_SIZE - 1],
                "invalid-flag": bytes(invalid_flag),
                "zero-tables": bytes(zero_tables),
                "missing-payload-byte": original[:-1],
                "trailing-byte": original + b"\0",
                "extra-flag-without-payload": bytes(extra_flag),
                "shift-fn-table-absent": remove_table(original, 3),
                "shift-fn-invalid-allocated-input": set_table_entry(original, 3, 0, 0x027E),
                "shift-alt-table-present": add_hole_table(original, 9),
            }
            for name, data in mutants.items():
                path = temp / f"{name}.bkeymap"
                path.write_bytes(data)
                run(args.verifier, path, False)

            symlink = temp / "symlink.bkeymap"
            symlink.symlink_to(args.keymap.resolve())
            run(args.verifier, symlink, False)
    except (OSError, RuntimeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("valid_parser=PASS")
    print("parser_rejections=11/11")
    print("tty_access=not-required-for-check-mode")
    print("test=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
