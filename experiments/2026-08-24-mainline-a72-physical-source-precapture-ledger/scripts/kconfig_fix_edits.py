#!/usr/bin/env python3
"""Remove the reciprocal negative dependency from the old ledger mode."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    root = parser.parse_args().source_root.resolve()
    path = root / "fs/pstore/Kconfig"
    text = path.read_text(encoding="utf-8")
    physical_start = text.index("config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER\n")
    precapture_start = text.index(
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER\n"
    )
    physical = text[physical_start:precapture_start]
    line = "\tdepends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER\n"
    if physical.count(line) != 1 or text.count(line) != 1:
        raise SystemExit("expected one reciprocal pre-capture dependency")
    path.write_text(text[:physical_start] + physical.replace(line, "", 1)
                    + text[precapture_start:], encoding="utf-8")


if __name__ == "__main__":
    main()
