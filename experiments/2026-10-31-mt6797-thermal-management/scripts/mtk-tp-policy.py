#!/usr/bin/env python3
"""Decoder for the Gemini stock Android thermal policy files (`.tp`).

The vendor files are not encrypted.  The loader library applies a reversible
per-line rotation over the 91 printable ASCII characters and leaves line
breaks untouched:

    plain_index = (cipher_index - (column % 10)) mod 91      # column restarts at LF

This was recovered from the Thumb-2 leaf function in the vendor
`libmtcloader.so` that `readPolicy_formatV1` calls after reading each line.
Decoded files are a flat list of two-line records: a `/proc` path followed by
the value written verbatim to it, terminated by a literal `EOF` line.

Usage:
    ./mtk-tp-policy.py dec CIPHER_FILE > plain.txt
    ./mtk-tp-policy.py enc PLAIN_FILE  > cipher.txt

Only operate on files you are entitled to read.  The decoded policy is vendor
material; keep it out of the public repository.
"""

from __future__ import annotations

import sys

BASE = 0x20
ALPHABET = 91  # 0x20..0x7a inclusive


def transform(data: bytes, sign: int) -> bytes:
    out = bytearray()
    column = 0
    for byte in data:
        if byte == 0x0A:
            out.append(byte)
            column = 0
            continue
        if BASE <= byte <= BASE + ALPHABET - 1:
            index = (byte - BASE + sign * (column % 10)) % ALPHABET
            out.append(index + BASE)
        else:
            out.append(byte)
        column += 1
    return bytes(out)


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"dec", "enc"}:
        print(__doc__.strip().splitlines()[-4].strip(), file=sys.stderr)
        return 2
    with open(sys.argv[2], "rb") as handle:
        data = handle.read()
    sys.stdout.buffer.write(transform(data, +1 if sys.argv[1] == "enc" else -1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
