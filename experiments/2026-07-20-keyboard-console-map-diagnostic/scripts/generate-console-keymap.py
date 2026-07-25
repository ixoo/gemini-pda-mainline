#!/usr/bin/env python3
"""Generate the Gemini US console map from Linux's pinned default keymap."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import struct
import sys


SOURCE_SHA256 = "318f48316e6bed5ada064879535ec2bca470dc1a8b8c9abd1d92da81bb2c6c7c"
MAGIC = b"bkeymap"
MAX_NR_KEYMAPS = 256
BUSYBOX_NR_KEYS = 128
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
OUTPUT_TABLES = tuple(sorted((*SOURCE_TABLES, 3)))
K_HOLE = 0xF200

ARRAY_RE = re.compile(
    r"^(?:static\s+)?unsigned short\s+"
    r"(?P<name>[a-z][a-z0-9_]*)\[NR_KEYS\]\s*=\s*\{"
    r"(?P<body>.*?)^\};$",
    re.MULTILINE | re.DOTALL,
)
VALUE_RE = re.compile(r"0x([0-9a-fA-F]{4})")
POINTER_RE = re.compile(
    r"^unsigned short\s+\*key_maps\[MAX_NR_KEYMAPS\]\s*=\s*\{"
    r"(?P<body>.*?)^\};$",
    re.MULTILINE | re.DOTALL,
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    return path.read_bytes()


def parse_default_maps(source: bytes) -> dict[int, list[int]]:
    if digest(source) != SOURCE_SHA256:
        raise ValueError("source is not exact Linux v7.1 defkeymap.c_shipped")
    try:
        text = source.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("pinned keymap source is not ASCII") from exc

    arrays: dict[str, list[int]] = {}
    for match in ARRAY_RE.finditer(text):
        body = match.group("body")
        residue = VALUE_RE.sub("", body).replace(",", "")
        if residue.strip():
            raise ValueError(f"unparsed C tokens in {match.group('name')}")
        values = [int(value, 16) for value in VALUE_RE.findall(body)]
        if len(values) != 256:
            raise ValueError(
                f"{match.group('name')} has {len(values)} entries, expected 256"
            )
        arrays[match.group("name")] = values

    pointer_match = POINTER_RE.search(text)
    if not pointer_match:
        raise ValueError("key_maps pointer table is absent")
    pointers = [
        token.strip()
        for token in pointer_match.group("body").split(",")
        if token.strip()
    ]
    discovered = {
        index: name for index, name in enumerate(pointers) if name != "NULL"
    }
    if discovered != SOURCE_TABLES:
        raise ValueError(f"unexpected default key_maps layout: {discovered}")
    count_match = re.search(r"^unsigned int keymap_count\s*=\s*(\d+);$", text, re.MULTILINE)
    if not count_match or int(count_match.group(1)) != len(SOURCE_TABLES):
        raise ValueError("keymap_count does not match the default pointer table")

    try:
        for table, name in SOURCE_TABLES.items():
            high_half = arrays[name][BUSYBOX_NR_KEYS:]
            if high_half != [K_HOLE] * BUSYBOX_NR_KEYS:
                raise ValueError(
                    f"default table {table} high half is not entirely K_HOLE"
                )
        return {
            table: arrays[name][:BUSYBOX_NR_KEYS]
            for table, name in SOURCE_TABLES.items()
        }
    except KeyError as exc:
        raise ValueError(f"referenced keymap array is absent: {exc.args[0]}") from exc


def latin(character: str) -> int:
    if len(character) != 1 or ord(character) > 0xFF:
        raise ValueError(f"not a single Latin-1 character: {character!r}")
    return 0xF000 | ord(character)


def require_anchor(
    maps: dict[int, list[int]], table: int, keycode: int, expected: int, label: str
) -> int:
    actual = maps[table][keycode]
    if actual != expected:
        raise ValueError(
            f"default {label} anchor changed: table={table} keycode={keycode} "
            f"got=0x{actual:04x} expected=0x{expected:04x}"
        )
    return actual


def apply_gemini_us_layer(default_maps: dict[int, list[int]]) -> dict[int, list[int]]:
    maps = {table: values.copy() for table, values in default_maps.items()}

    # These are internal defkeymap values, before the kernel's U(x) boundary.
    # Pin the K_* anchors instead of treating cursor/function sequences as text.
    k_caps = require_anchor(maps, 0, 58, 0xF207, "K_CAPS")
    k_find = require_anchor(maps, 0, 102, 0xF114, "K_FIND/Home")
    k_pgup = require_anchor(maps, 0, 104, 0xF118, "K_PGUP")
    k_select = require_anchor(maps, 0, 107, 0xF117, "K_SELECT/End")
    k_pgdn = require_anchor(maps, 0, 109, 0xF119, "K_PGDN")
    k_ctrl = require_anchor(maps, 0, 29, 0xF702, "left K_CTRL")
    require_anchor(maps, 0, 97, k_ctrl, "right K_CTRL")
    k_shift = require_anchor(maps, 0, 42, 0xF700, "K_SHIFT")
    require_anchor(maps, 0, 54, k_shift, "right K_SHIFT")
    k_alt = require_anchor(maps, 0, 56, 0xF703, "K_ALT")
    k_altgr = require_anchor(maps, 0, 100, 0xF701, "K_ALTGR")
    require_anchor(maps, 0, 0, K_HOLE, "K_HOLE")

    # The captured known-good XKB layout has a fourth level on the number row.
    # Allocate only that Shift+Fn table and fail closed everywhere else.  The
    # kernel does not write entry zero through KDSKBENT.  Keep a valid K_HOLE in
    # the payload at index zero; writing index one allocates the absent table,
    # at which point the kernel installs K_ALLOCATED at index zero.  The live
    # verifier accounts for that documented payload-to-kernel transition.
    shift_fn = [K_HOLE] * BUSYBOX_NR_KEYS
    shift_fn[29] = k_ctrl
    shift_fn[42] = k_shift
    shift_fn[54] = k_shift
    shift_fn[56] = k_alt
    shift_fn[97] = k_ctrl
    shift_fn[100] = k_altgr
    for offset, keycode in enumerate(range(2, 12)):
        shift_fn[keycode] = require_anchor(
            maps, 0, 59 + offset, 0xF100 + offset, f"K_F{offset + 1}"
        )
    maps[3] = shift_fn

    # The active DT intentionally retains KEY_APOSTROPHE at this physical
    # position to remain compatible with the proven 3.18/Gemian map.  Correct
    # its US silkscreen meaning in the VT map instead.  Copy the pinned Linux
    # KEY_BACKSLASH Ctrl/Shift+Ctrl/Alt/Ctrl+Alt semantics rather than retaining
    # KEY_APOSTROPHE's Ctrl-G and Meta-apostrophe behavior.  Shift+Alt table 9
    # remains deliberately absent, like the pinned Linux default.
    for table in (0, 1, 4, 5, 8, 12):
        maps[table][40] = maps[table][43]
    maps[1][51] = latin("/")
    maps[1][52] = latin("?")

    # Physical Fn emits KEY_LEFTMETA (keycode 125).  Making it K_ALTGR in every
    # loaded output table ensures both press and release remain modifier
    # events while another loaded modifier table is active.
    for values in maps.values():
        values[125] = k_altgr

    fn = maps[2]
    for keycode, character in {
        2: "~",
        3: "`",
        6: "<",
        7: ">",
        8: "[",
        9: "]",
        10: "{",
        11: "}",
        23: "+",
        24: "-",
        25: "=",
        36: "_",
        37: ";",
        38: '"',
        40: ":",
        50: "'",
    }.items():
        fn[keycode] = latin(character)

    # Direct Unicode code points are stored literally in the kernel's internal
    # map.  The bkeymap/KDSKBENT representation below must therefore contain
    # U+00A3^0xf000 (0xf0a3) and U+20AC^0xf000 (0xd0ac), not their code points.
    # Linux v7.1 VTs default to K_UNICODE; a caller must not load this map into
    # a console deliberately switched to a non-Unicode keyboard mode.
    fn[4] = 0x00A3
    fn[5] = 0x20AC
    fn[52] = 0x263A

    fn[15] = k_caps
    fn[103] = k_pgup
    fn[105] = k_find
    fn[106] = k_select
    fn[108] = k_pgdn
    return maps


def encode_bkeymap(maps: dict[int, list[int]]) -> bytes:
    if set(maps) != set(OUTPUT_TABLES):
        raise ValueError("output table set differs from the pinned Linux-plus-Shift-Fn policy")
    flags = bytearray(MAX_NR_KEYMAPS)
    for table in maps:
        flags[table] = 1

    output = bytearray(MAGIC)
    output.extend(flags)
    for table in range(MAX_NR_KEYMAPS):
        if not flags[table]:
            continue
        values = maps[table]
        if len(values) != BUSYBOX_NR_KEYS:
            raise ValueError(f"table {table} does not have 128 BusyBox entries")
        # BusyBox reads native uint16_t values.  The target is little-endian
        # arm64, so encode that target format explicitly and reproducibly.
        output.extend(
            struct.pack(
                f"<{BUSYBOX_NR_KEYS}H",
                *(value ^ INTERNAL_XOR for value in values),
            )
        )
    return bytes(output)


def write_new(path: pathlib.Path, data: bytes) -> None:
    if not path.parent.is_dir():
        raise ValueError("output parent directory does not exist")
    created = False
    try:
        with path.open("xb") as stream:
            created = True
            stream.write(data)
        os.chmod(path, 0o644)
    except Exception:
        if created:
            path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        required=True,
        help="exact Linux v7.1 drivers/tty/vt/defkeymap.c_shipped",
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    try:
        source = read_regular(args.source, "defkeymap source")
        maps = apply_gemini_us_layer(parse_default_maps(source))
        output = encode_bkeymap(maps)
        write_new(args.output, output)
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"source_sha256={digest(source)}")
    print(f"output_sha256={digest(output)}")
    print(f"output_size={len(output)}")
    print("tables=0,1,2,3,4,5,8,12")
    print("source_high_halves=128-255:all-K_HOLE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
