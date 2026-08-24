#!/usr/bin/env python3
"""Add the guarded cleanup label required by the pre-capture path."""

from __future__ import annotations

import argparse
from pathlib import Path


MODE = "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER"
RELATIVE = Path(
    "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    root = parser.parse_args().source_root.resolve()
    path = root / RELATIVE
    text = path.read_text(encoding="utf-8")
    anchor = "\n\tput_device(context.bigidvfs);\nput_clock:\n"
    replacement = (
        f"\n#ifdef {MODE}\n"
        "put_bigidvfs:\n"
        "#endif\n"
        "\tput_device(context.bigidvfs);\n"
        "put_clock:\n"
    )
    if text.count(anchor) != 1:
        raise SystemExit("expected one unlabeled BigiDVFS cleanup edge")
    if "put_bigidvfs:" in text:
        raise SystemExit("BigiDVFS cleanup label already exists")
    path.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")


if __name__ == "__main__":
    main()
