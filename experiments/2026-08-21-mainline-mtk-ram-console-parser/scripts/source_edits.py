#!/usr/bin/env python3
"""Apply deterministic MediaTek retained ram-console parser changes."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_new(path: Path, source: Path) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def apply(root: Path, experiment: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    makefile = root / "drivers/soc/mediatek/Makefile"

    replace_once(
        kconfig,
        "config MTK_PMIC_WRAP\n",
        dedent("""\
        config MTK_RAM_CONSOLE_PARSER
        \tbool "MediaTek retained ram-console parser"
        \tdepends on ARM64 && ARCH_MEDIATEK
        \thelp
        \t  Parse a caller-owned copy of the audited MediaTek retained
        \t  ram-console prefix with strict bounds and overflow checks. The
        \t  parser returns only the complete raw preloader status word and
        \t  does not map memory or classify reset provenance.

        config MTK_RAM_CONSOLE_PARSER_KUNIT_TEST
        \tbool "KUnit tests for the MediaTek ram-console parser"
        \tdepends on KUNIT=y
        \tselect MTK_RAM_CONSOLE_PARSER
        \thelp
        \t  Test corrupt and exact retained-header inputs in ordinary memory.
        \t  The suite performs no mapping, MMIO, reset, firmware, or CPU
        \t  operation.

        \t  If unsure, say N.

        config MTK_PMIC_WRAP
        """),
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_PMIC_WRAP) += mtk-pmic-wrap.o\n",
        "obj-$(CONFIG_MTK_RAM_CONSOLE_PARSER) += mtk-ram-console.o\n"
        "obj-$(CONFIG_MTK_PMIC_WRAP) += mtk-pmic-wrap.o\n",
    )

    write_new(
        root / "drivers/soc/mediatek/mtk-ram-console.c",
        experiment / "source/mtk-ram-console.c",
    )
    write_new(
        root / "include/linux/soc/mediatek/mtk-ram-console.h",
        experiment / "source/mtk-ram-console.h",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not (root / "drivers/soc/mediatek/Kconfig").is_file():
        raise SystemExit("unexpected source root")
    apply(root, Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
