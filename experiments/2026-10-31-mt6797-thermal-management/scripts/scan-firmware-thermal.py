#!/usr/bin/env python3
"""Summarize thermal-relevant content of retained Gemini firmware images.

Read-only. Never copies firmware bytes into Git: the emitted table contains
file names, sizes, digests, entropy summaries and matched ASCII strings only.

Usage:
    ./scan-firmware-thermal.py FIRMWARE_ROOT > results/firmware-thermal-scan.tsv

FIRMWARE_ROOT is a private directory containing the retained partition images
and vendor firmware tree. The expected layout is the one described in
docs/hardware/firmware.md plus the private partition capture.
"""

from __future__ import annotations

import collections
import hashlib
import math
import re
import struct
import sys
from pathlib import Path

TERMS = re.compile(
    r"thermal|temperature|tmsensor|tscpu|dvfs|ppm|ptp|eem|throttl|"
    r"calib|efuse|vts|verdict",
    re.IGNORECASE,
)

# Addresses whose presence in a blob is meaningful for the thermal chain.
ADDRESSES = {
    0x1100B000: "therm_ctrl",
    0x11001000: "auxadc",
    0x10206180: "ts_efuse0",
    0x10206184: "ts_efuse1",
    0x10206188: "ts_efuse2",
    0x11015000: "cspm",
    0x0012A000: "csram",
}

STRINGS = re.compile(rb"[\x20-\x7e]{6,}")


def entropy_prefix(data: bytes, block: int = 256 * 1024) -> str:
    values = []
    for start in range(0, min(len(data), block * 4), block):
        chunk = data[start:start + block]
        counts = collections.Counter(chunk)
        total = len(chunk)
        values.append(
            round(-sum(n / total * math.log2(n / total) for n in counts.values()), 1)
        )
    return ",".join(str(v) for v in values)


def aligned_hits(data: bytes, address: int) -> list[int]:
    """Offsets of 4-byte-aligned little-endian occurrences of an address."""
    blob = struct.pack("<I", address)
    found = []
    start = data.find(blob)
    while start != -1:
        if start % 4 == 0:
            found.append(start)
        start = data.find(blob, start + 1)
    return found


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-4].strip(), file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    files = sorted(p for p in root.rglob("*") if p.is_file())
    if not files:
        print("no files below %s" % root, file=sys.stderr)
        return 2

    print("\t".join([
        "file", "bytes", "sha256", "entropy_256k", "thermal_strings",
        "matched_terms", "address_constants",
    ]))
    for path in files:
        data = path.read_bytes()
        text = b"\n".join(STRINGS.findall(data))
        strings = {s.decode("ascii", "replace") for s in text.split(b"\n")}
        matched = sorted({s for s in strings if TERMS.search(s)})
        terms = sorted({m.lower() for s in matched for m in TERMS.findall(s)})
        addrs = [
            "%s@0x%x" % (name, addr)
            for addr, name in sorted(ADDRESSES.items())
            if aligned_hits(data, addr)
        ]
        print("\t".join([
            path.relative_to(root).as_posix(),
            str(len(data)),
            hashlib.sha256(data).hexdigest(),
            entropy_prefix(data),
            str(len(matched)),
            ",".join(terms),
            ",".join(addrs),
        ]).rstrip("\t"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
