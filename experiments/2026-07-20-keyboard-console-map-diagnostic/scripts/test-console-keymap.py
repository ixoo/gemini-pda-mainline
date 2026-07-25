#!/usr/bin/env python3
"""Exercise deterministic generation and focused console-map rejections."""

from __future__ import annotations

import argparse
import pathlib
import struct
import subprocess
import sys
import tempfile


MAGIC_SIZE = 7
FLAGS_SIZE = 256
TABLE_BYTES = 128 * 2
TABLES = (0, 1, 2, 3, 4, 5, 8, 12)


def run(command: list[str], expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != expected:
        raise RuntimeError(
            f"unexpected status {result.returncode}, wanted {expected}: {command}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def entry_offset(table: int, keycode: int) -> int:
    if table not in TABLES or not 0 <= keycode < 128:
        raise ValueError("invalid test table/keycode")
    return MAGIC_SIZE + FLAGS_SIZE + TABLES.index(table) * TABLE_BYTES + keycode * 2


def set_entry(data: bytes, table: int, keycode: int, value: int) -> bytes:
    result = bytearray(data)
    struct.pack_into("<H", result, entry_offset(table, keycode), value)
    return bytes(result)


def get_entry(data: bytes, table: int, keycode: int) -> int:
    return struct.unpack_from("<H", data, entry_offset(table, keycode))[0]


def add_hole_table(data: bytes, table: int) -> bytes:
    flags_offset = MAGIC_SIZE
    if not 0 <= table < FLAGS_SIZE or data[flags_offset + table]:
        raise ValueError("invalid synthetic test table")
    insertion = MAGIC_SIZE + FLAGS_SIZE
    for existing in TABLES:
        if existing >= table:
            break
        insertion += TABLE_BYTES
    result = bytearray(data[:insertion])
    result.extend(struct.pack("<128H", *([0x0200] * 128)))
    result.extend(data[insertion:])
    result[flags_offset + table] = 1
    return bytes(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, required=True)
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    generator = script_dir / "generate-console-keymap.py"
    validator = script_dir / "validate-console-keymap.py"
    python = sys.executable

    try:
        with tempfile.TemporaryDirectory(prefix="gemini-console-map-") as temp_name:
            temp = pathlib.Path(temp_name)
            first = temp / "first.bkeymap"
            second = temp / "second.bkeymap"
            run([python, str(generator), "--source", str(args.source), "--output", str(first)])
            run([python, str(generator), "--source", str(args.source), "--output", str(second)])
            if first.read_bytes() != second.read_bytes():
                raise RuntimeError("two clean generations are not byte-identical")

            validation = run(
                [python, str(validator), "--source", str(args.source), "--keymap", str(first)]
            )
            for token in (
                "tables=0,1,2,3,4,5,8,12",
                "source_high_halves=128-255:all-K_HOLE",
                "table=9 status=absent semantic=Shift+Alt-unallocated",
                "changes=53",
                "keycode=4 uapi=0xf0a3 internal=0x00a3 semantic=U+00A3",
                "keycode=5 uapi=0xd0ac internal=0x20ac semantic=U+20AC",
                "keycode=52 uapi=0xd63a internal=0x263a semantic=U+263A",
                "table=3 keycode=0 uapi=0x0200 internal=0xf200 semantic=K_HOLE",
                "table=3 keycode=2 uapi=0x0100 internal=0xf100 semantic=K_F1",
                "table=3 keycode=11 uapi=0x0109 internal=0xf109 semantic=K_F10",
                "table=4 keycode=40 uapi=0x001c internal=0xf01c semantic=Control_backslash",
                "table=5 keycode=40 uapi=0x0200 internal=0xf200 semantic=K_HOLE",
                "table=8 keycode=40 uapi=0x085c internal=0xf85c semantic=Meta_backslash",
                "table=12 keycode=40 uapi=0x0200 internal=0xf200 semantic=K_HOLE",
                "keycode=125 uapi=0x0701 internal=0xf701 semantic=K_ALTGR",
                "validation=PASS",
            ):
                if token not in validation.stdout:
                    raise RuntimeError(f"validator omitted semantic token: {token}")

            # Existing outputs are never overwritten.
            run(
                [python, str(generator), "--source", str(args.source), "--output", str(first)],
                expected=2,
            )

            changed_source = temp / "changed-defkeymap.c_shipped"
            source_data = args.source.read_bytes()
            changed_source.write_bytes(source_data.replace(b"Do not edit", b"Do nOt edit", 1))
            run(
                [
                    python,
                    str(generator),
                    "--source",
                    str(changed_source),
                    "--output",
                    str(temp / "bad.bkeymap"),
                ],
                expected=2,
            )

            original = first.read_bytes()
            expected_entries = {
                (0, 40): 0x005C,
                (1, 40): 0x007C,
                (2, 40): 0x003A,
                (3, 0): 0x0200,
                (3, 29): 0x0702,
                (3, 42): 0x0700,
                (3, 54): 0x0700,
                (3, 56): 0x0703,
                (3, 97): 0x0702,
                (3, 100): 0x0701,
                (3, 125): 0x0701,
                (4, 40): 0x001C,
                (5, 40): 0x0200,
                (8, 40): 0x085C,
                (12, 40): 0x0200,
            }
            expected_entries.update(
                {(3, keycode): 0x0100 + offset for offset, keycode in enumerate(range(2, 12))}
            )
            for location, expected in expected_entries.items():
                actual = get_entry(original, *location)
                if actual != expected:
                    raise RuntimeError(
                        f"wrong generated entry {location}: 0x{actual:04x}, expected 0x{expected:04x}"
                    )
            allowed_shift_fn = {0, *range(2, 12), 29, 42, 54, 56, 97, 100, 125}
            for keycode in range(128):
                if keycode not in allowed_shift_fn and get_entry(original, 3, keycode) != 0x0200:
                    raise RuntimeError(f"Shift+Fn table does not fail closed at keycode {keycode}")
            if original[MAGIC_SIZE + 9] != 0:
                raise RuntimeError("Shift+Alt table 9 was unexpectedly allocated")

            mutants = {
                "bad-magic": b"B" + original[1:],
                "trailing-byte": original + b"\0",
                "fn-not-altgr": set_entry(original, 0, 125, 0x0200),
                # A literal 0x20ac is the subtle wrong UAPI encoding for Euro.
                "euro-not-u-xored": set_entry(original, 2, 5, 0x20AC),
                "smiley-not-u-xored": set_entry(original, 2, 52, 0x263A),
                "unexpected-plain-change": set_entry(original, 0, 30, ord("z")),
                "shift-fn-invalid-allocated-input": set_entry(original, 3, 0, 0x027E),
                "shift-fn-f1-hole": set_entry(original, 3, 2, 0x0200),
                "shift-fn-unpictured-colon": set_entry(original, 3, 40, ord(":")),
                "shift-fn-release-hole": set_entry(original, 3, 125, 0x0200),
                "shift-fn-shift-release-hole": set_entry(original, 3, 42, 0x0200),
                "ctrl-backslash-bell": set_entry(original, 4, 40, 0x0007),
                "shift-ctrl-backslash-nonhole": set_entry(original, 5, 40, 0x001C),
                "alt-backslash-apostrophe": set_entry(original, 8, 40, 0x0827),
                "ctrl-alt-backslash-nonhole": set_entry(original, 12, 40, 0x081C),
                "shift-alt-table-present": add_hole_table(original, 9),
            }

            for name, data in mutants.items():
                path = temp / f"{name}.bkeymap"
                path.write_bytes(data)
                run(
                    [python, str(validator), "--source", str(args.source), "--keymap", str(path)],
                    expected=2,
                )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("deterministic_generations=2")
    print("generator_rejections=2")
    print("validator_mutations=16/16")
    print("shift_fn_fail_closed=PASS")
    print("backslash_modifier_semantics=PASS")
    print("semantic_unicode_checks=PASS")
    print("test=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
