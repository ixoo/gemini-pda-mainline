#!/usr/bin/env python3
"""Semantically validate the deterministic Gemini BusyBox console map."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import stat
import struct
import sys
import unicodedata


SOURCE_SHA256 = "318f48316e6bed5ada064879535ec2bca470dc1a8b8c9abd1d92da81bb2c6c7c"
MAGIC = b"bkeymap"
MAX_NR_KEYMAPS = 256
NR_KEYS = 128
HEADER_SIZE = len(MAGIC) + MAX_NR_KEYMAPS
INTERNAL_XOR = 0xF000
SOURCE_TABLES = {
    0: "plain_map",
    1: "shift_map",
    2: "altgr_map",
    4: "ctrl_map",
    5: "shift_ctrl_map",
    8: "alt_map",
    12: "ctrl_alt_map",
}
EXPECTED_TABLES = tuple(sorted((*SOURCE_TABLES, 3)))
EXPECTED_SIZE = HEADER_SIZE + len(EXPECTED_TABLES) * NR_KEYS * 2
K_HOLE_UAPI = 0x0200

ARRAY_RE = re.compile(
    r"^(?:static\s+)?unsigned short\s+"
    r"(?P<name>[a-z][a-z0-9_]*)\[NR_KEYS\]\s*=\s*\{"
    r"(?P<body>.*?)^\};$",
    re.MULTILINE | re.DOTALL,
)
VALUE_RE = re.compile(r"0x([0-9a-fA-F]{4})")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    return path.read_bytes()


def parse_baseline(source: bytes) -> dict[int, list[int]]:
    if digest(source) != SOURCE_SHA256:
        raise ValueError("source is not exact Linux v7.1 defkeymap.c_shipped")
    try:
        text = source.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("pinned keymap source is not ASCII") from exc
    arrays: dict[str, list[int]] = {}
    for match in ARRAY_RE.finditer(text):
        values = [int(value, 16) for value in VALUE_RE.findall(match.group("body"))]
        if len(values) == 256:
            arrays[match.group("name")] = values
    if set(SOURCE_TABLES.values()) - set(arrays):
        raise ValueError("one or more default keymap arrays are absent")
    for table, name in SOURCE_TABLES.items():
        if arrays[name][NR_KEYS:] != [0xF200] * NR_KEYS:
            raise ValueError(
                f"default table {table} high half is not entirely K_HOLE"
            )
    baseline = {
        table: [value ^ INTERNAL_XOR for value in arrays[name][:NR_KEYS]]
        for table, name in SOURCE_TABLES.items()
    }
    baseline[3] = [K_HOLE_UAPI] * NR_KEYS
    return baseline


def decode_bkeymap(data: bytes) -> dict[int, list[int]]:
    if len(data) != EXPECTED_SIZE:
        raise ValueError(f"binary size is {len(data)}, expected {EXPECTED_SIZE}")
    if data[: len(MAGIC)] != MAGIC:
        raise ValueError("BusyBox bkeymap magic is invalid")
    flags = data[len(MAGIC) : HEADER_SIZE]
    if any(flag not in (0, 1) for flag in flags):
        raise ValueError("bkeymap flags contain a value other than zero or one")
    present = {table for table, flag in enumerate(flags) if flag}
    if present != set(EXPECTED_TABLES):
        raise ValueError(f"binary table set differs from Linux defaults: {sorted(present)}")

    offset = HEADER_SIZE
    tables: dict[int, list[int]] = {}
    for table, flag in enumerate(flags):
        if not flag:
            continue
        end = offset + NR_KEYS * 2
        tables[table] = list(struct.unpack(f"<{NR_KEYS}H", data[offset:end]))
        offset = end
    if offset != len(data):
        raise ValueError("binary has trailing or truncated table bytes")
    return tables


def expected_values() -> dict[tuple[int, int], int]:
    values: dict[tuple[int, int], int] = {
        (0, 40): ord("\\"),
        (1, 40): ord("|"),
        (1, 51): ord("/"),
        (1, 52): ord("?"),
        (2, 2): ord("~"),
        (2, 3): ord("`"),
        # Direct Unicode UAPI values are codepoint ^ 0xf000.
        (2, 4): 0x00A3 ^ INTERNAL_XOR,
        (2, 5): 0x20AC ^ INTERNAL_XOR,
        (2, 6): ord("<"),
        (2, 7): ord(">"),
        (2, 8): ord("["),
        (2, 9): ord("]"),
        (2, 10): ord("{"),
        (2, 11): ord("}"),
        (2, 15): 0x0207,  # K_CAPS
        (2, 23): ord("+"),
        (2, 24): ord("-"),
        (2, 25): ord("="),
        (2, 36): ord("_"),
        (2, 37): ord(";"),
        (2, 38): ord('"'),
        (2, 40): ord(":"),
        (2, 50): ord("'"),
        (2, 52): 0x263A ^ INTERNAL_XOR,
        (3, 0): K_HOLE_UAPI,
        (3, 29): 0x0702,  # K_CTRL, modifier-state preservation
        (3, 40): K_HOLE_UAPI,
        (3, 42): 0x0700,  # K_SHIFT
        (3, 54): 0x0700,  # K_SHIFT
        (3, 56): 0x0703,  # K_ALT
        (3, 97): 0x0702,  # K_CTRL
        (3, 100): 0x0701,  # K_ALTGR
        (4, 40): 0x001C,  # Control_backslash
        (5, 40): K_HOLE_UAPI,
        (8, 40): 0x085C,  # Meta_backslash
        (12, 40): K_HOLE_UAPI,
        (2, 103): 0x0118,  # K_PGUP
        (2, 105): 0x0114,  # K_FIND, default Home sequence
        (2, 106): 0x0117,  # K_SELECT, default End sequence
        (2, 108): 0x0119,  # K_PGDN
    }
    for offset, keycode in enumerate(range(2, 12)):
        values[(3, keycode)] = 0x0100 + offset  # K_F1 through K_F10
    for table in EXPECTED_TABLES:
        values[(table, 125)] = 0x0701  # K_ALTGR
    return values


def semantic(value: int) -> str:
    internal = value ^ INTERNAL_XOR
    if internal < 0xF000:
        try:
            name = unicodedata.name(chr(internal))
        except (ValueError, TypeError):
            name = "UNNAMED"
        return f"U+{internal:04X} {name}"
    key_type = (internal >> 8) - 0xF0
    key_value = internal & 0xFF
    names = {
        (0, 0x1C): "Control_backslash",
        (1, 0x00): "K_F1",
        (1, 0x09): "K_F10",
        (1, 0x14): "K_FIND/Home",
        (1, 0x17): "K_SELECT/End",
        (1, 0x18): "K_PGUP",
        (1, 0x19): "K_PGDN",
        (2, 0x00): "K_HOLE",
        (2, 0x07): "K_CAPS",
        (2, 0x7E): "K_ALLOCATED",
        (7, 0x00): "K_SHIFT",
        (7, 0x01): "K_ALTGR",
        (7, 0x02): "K_CTRL",
        (7, 0x03): "K_ALT",
        (8, 0x5C): "Meta_backslash",
    }
    if (key_type, key_value) in names:
        return names[(key_type, key_value)]
    if key_type == 0:
        return f"KT_LATIN U+{key_value:04X}"
    return f"KT_{key_type} value=0x{key_value:02x}"


def validate(
    source: bytes, binary: bytes
) -> tuple[dict[int, list[int]], dict[tuple[int, int], int]]:
    baseline = parse_baseline(source)
    candidate = decode_bkeymap(binary)
    expected = expected_values()
    changes = {
        location: value
        for location, value in expected.items()
        if baseline[location[0]][location[1]] != value
    }

    actual_changes = {
        (table, keycode): value
        for table, values in candidate.items()
        for keycode, value in enumerate(values)
        if value != baseline[table][keycode]
    }
    if set(actual_changes) != set(changes):
        missing = sorted(set(changes) - set(actual_changes))
        extra = sorted(set(actual_changes) - set(changes))
        raise ValueError(f"changed-entry set differs: missing={missing} extra={extra}")
    wrong = {
        location: (candidate[location[0]][location[1]], value)
        for location, value in expected.items()
        if candidate[location[0]][location[1]] != value
    }
    if wrong:
        raise ValueError(f"one or more semantic values are wrong: {wrong}")

    # Check both sides of U(x) explicitly.  Loading 0x20ac for Euro would be
    # wrong: KDSKBENT would XOR it to internal 0xd0ac and emit U+D0AC.
    for keycode, codepoint in ((4, 0x00A3), (5, 0x20AC), (52, 0x263A)):
        value = candidate[2][keycode]
        if value != codepoint ^ INTERNAL_XOR or value ^ INTERNAL_XOR != codepoint:
            raise ValueError(f"Fn Unicode encoding is wrong at keycode {keycode}")
    return candidate, changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--keymap", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        source = read_regular(args.source, "defkeymap source")
        binary = read_regular(args.keymap, "bkeymap")
        candidate, changes = validate(source, binary)
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"source_sha256={digest(source)}")
    print(f"keymap_sha256={digest(binary)}")
    print(f"keymap_size={len(binary)}")
    print("tables=0,1,2,3,4,5,8,12")
    print("source_high_halves=128-255:all-K_HOLE")
    print("table=9 status=absent semantic=Shift+Alt-unallocated")
    print(f"changes={len(changes)}")
    for table, keycode in (
        (2, 4),
        (2, 5),
        (2, 52),
        (3, 0),
        (3, 2),
        (3, 11),
        (3, 29),
        (3, 42),
        (3, 54),
        (3, 56),
        (3, 97),
        (3, 100),
        (3, 125),
        (4, 40),
        (5, 40),
        (8, 40),
        (12, 40),
        (2, 15),
        (2, 103),
        (2, 105),
        (2, 108),
        (2, 125),
    ):
        value = candidate[table][keycode]
        print(
            f"table={table} keycode={keycode} uapi=0x{value:04x} "
            f"internal=0x{value ^ INTERNAL_XOR:04x} semantic={semantic(value)}"
        )
    print("validation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
