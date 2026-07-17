#!/usr/bin/env python3
"""Generate or validate the deterministic Gemini simplefb test frame."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys


WIDTH = 1080
HEIGHT = 2160
STRIDE = 4352
BYTES_PER_PIXEL = 4
BAND_HEIGHT = 270
FRAME_BYTES = STRIDE * HEIGHT
WHITE = bytes((0xFF, 0xFF, 0xFF, 0xFF))
DARK_GRAY = bytes((0x20, 0x20, 0x20, 0xFF))


def expected_rows():
    pixels_per_stride = STRIDE // BYTES_PER_PIXEL
    for row_number in range(HEIGHT):
        pixel = WHITE if (row_number // BAND_HEIGHT) % 2 == 0 else DARK_GRAY
        yield pixel * pixels_per_stride


def expected_sha256() -> str:
    digest = hashlib.sha256()
    for row in expected_rows():
        digest.update(row)
    return digest.hexdigest()


def generate(path: pathlib.Path) -> None:
    if path.exists():
        raise ValueError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        for row in expected_rows():
            output.write(row)


def validate(path: pathlib.Path) -> None:
    if path.stat().st_size != FRAME_BYTES:
        raise ValueError(
            f"{path}: expected {FRAME_BYTES} bytes, got {path.stat().st_size}"
        )
    with path.open("rb") as source:
        for row_number, expected in enumerate(expected_rows()):
            actual = source.read(STRIDE)
            if actual != expected:
                raise ValueError(f"{path}: unexpected bytes in row {row_number}")
        if source.read(1):
            raise ValueError(f"{path}: trailing data")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=pathlib.Path)
    group.add_argument("--validate", type=pathlib.Path)
    args = parser.parse_args()
    try:
        if args.output is not None:
            generate(args.output)
            path = args.output
            result = "generated"
        else:
            validate(args.validate)
            path = args.validate
            result = "validated"
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"marker={result}")
    print(f"path={path}")
    print(f"width={WIDTH}")
    print(f"height={HEIGHT}")
    print(f"stride={STRIDE}")
    print(f"frame_bytes={FRAME_BYTES}")
    print("format=a8r8g8b8")
    print("pattern=8-horizontal-bands-opaque-white-dark-gray")
    print(f"sha256={expected_sha256()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
