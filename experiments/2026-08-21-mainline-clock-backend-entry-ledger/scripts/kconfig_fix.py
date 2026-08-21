#!/usr/bin/env python3
"""Apply the isolated clock-entry ledger Kconfig dependency correction."""

from __future__ import annotations

import argparse
from pathlib import Path


OLD = "\tdepends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\n"
NEW = (
    "\tdepends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y || "
    "MTK_MT6797_DVFSP_CLOCK_BACKEND=y\n"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = args.source_root.resolve() / "fs/pstore/Kconfig"
    text = path.read_text(encoding="utf-8")
    if text.count(OLD) != 1 or NEW in text:
        raise SystemExit("unexpected protected-readback base dependency")
    path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")


if __name__ == "__main__":
    main()
