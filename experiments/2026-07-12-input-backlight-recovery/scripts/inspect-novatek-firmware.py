#!/usr/bin/env python3
"""Inspect non-sensitive metadata in the private vendor NVT firmware image."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED_SIZE = 118_784
VERSION_OFFSET = 0x1A000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    args = parser.parse_args()

    data = args.image.read_bytes()
    if len(data) <= VERSION_OFFSET + 1:
        raise SystemExit("firmware image is too short for vendor metadata")

    version = data[VERSION_OFFSET]
    version_bar = data[VERSION_OFFSET + 1]
    print(f"path={args.image}")
    print(f"size={len(data)}")
    print(f"expected_size={EXPECTED_SIZE}")
    print(f"size_match={len(data) == EXPECTED_SIZE}")
    print(f"sha256={hashlib.sha256(data).hexdigest()}")
    print(f"version_offset=0x{VERSION_OFFSET:x}")
    print(f"version=0x{version:02x}")
    print(f"version_bar=0x{version_bar:02x}")
    print(f"version_sum=0x{(version + version_bar):02x}")
    print(f"version_pair_valid={(version + version_bar) == 0xff}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
