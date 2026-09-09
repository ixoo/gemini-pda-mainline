#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline identity/metadata check; run against private retained files in the RE VM."""

import argparse
import hashlib
import json
import os
import stat


# Ordered by the observed header sequence, not lexical filename order.
PATCHES = (
    ("ROMv3_patch_1_1_hdr.bin", 46472,
     "5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e",
     1, "00000af0"),
    ("ROMv3_patch_1_0_hdr.bin", 210904,
     "450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630",
     2, "00000900"),
)


def verify(data, expected):
    name, size, digest, sequence, address = expected
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"{name}: retained identity mismatch")
    metadata = {
        "name": name, "bytes": size, "sha256": digest,
        "header_version_be": f"0x{int.from_bytes(data[22:24], 'big'):04x}",
        "count": data[24] >> 4, "sequence": data[24] & 15,
        "address_bytes_hex": (b"\0" + data[25:28]).hex(),
    }
    if (metadata["header_version_be"] != "0x8a00"
            or metadata["count"] != 2 or metadata["sequence"] != sequence
            or metadata["address_bytes_hex"] != address):
        raise ValueError(f"{name}: metadata mismatch")
    return metadata


def check_directory(directory):
    rows = []
    for expected in PATCHES:
        name, size, *_ = expected
        fd = os.open(os.path.join(directory, name),
                     os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size != size:
                raise ValueError(f"{name}: expected regular file and retained size")
            rows.append(verify(source.read(size + 1), expected))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="private retained firmware directory")
    args = parser.parse_args()
    rows = check_directory(args.directory)
    print(json.dumps({"scope": "offline retained identity; not runtime admission",
                      "patches": rows}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f"refused: {error}") from error
