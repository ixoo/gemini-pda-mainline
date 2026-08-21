#!/usr/bin/env python3
"""Apply deterministic retained ram-console copy-owner source phases."""

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


def replace_exact(path: Path, source: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"expected existing path: {path}")
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def apply_binding(root: Path, experiment: Path) -> None:
    write_new(
        root / "Documentation/devicetree/bindings/soc/mediatek/"
        "mediatek,mt6797-ram-console.yaml",
        experiment / "source/mediatek,mt6797-ram-console.yaml",
    )


def apply_driver(root: Path, experiment: Path) -> None:
    replace_once(
        root / "drivers/soc/mediatek/Kconfig",
        "config MTK_PMIC_WRAP\n",
        dedent("""\
        config MTK_RAM_CONSOLE_READER
        \tbool "MediaTek retained ram-console immutable reader"
        \tdepends on ARM64 && ARCH_MEDIATEK && OF_RESERVED_MEM
        \tselect MTK_RAM_CONSOLE_PARSER
        \thelp
        \t  Bind one no-map reserved-memory phandle, take one complete
        \t  ordinary-memory copy, unmap it before parsing, and publish only
        \t  the typed immutable raw-status snapshot. The reader does not
        \t  classify reset provenance or write retained memory.

        config MTK_RAM_CONSOLE_READER_KUNIT_TEST
        \tbool "KUnit tests for the MediaTek ram-console reader"
        \tdepends on KUNIT=y
        \tselect MTK_RAM_CONSOLE_READER
        \thelp
        \t  Test one-copy publication, failure invalidation, immutability,
        \t  and every-bit preservation with injected ordinary memory. The
        \t  suite does not map physical memory or perform a hardware action.

        \t  If unsure, say N.

        config MTK_PMIC_WRAP
        """),
    )
    replace_once(
        root / "drivers/soc/mediatek/Makefile",
        "obj-$(CONFIG_MTK_RAM_CONSOLE_PARSER) += mtk-ram-console.o\n",
        "obj-$(CONFIG_MTK_RAM_CONSOLE_PARSER) += mtk-ram-console.o\n"
        "obj-$(CONFIG_MTK_RAM_CONSOLE_READER) += mtk-ram-console-reader.o\n",
    )
    write_new(
        root / "drivers/soc/mediatek/mtk-ram-console-reader.c",
        experiment / "source/mtk-ram-console-reader.c",
    )
    replace_exact(
        root / "include/linux/soc/mediatek/mtk-ram-console.h",
        experiment / "source/mtk-ram-console.h",
    )


def apply_dt(root: Path) -> None:
    dts = root / "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts"
    replace_once(
        dts,
        "\treserved-memory {\n",
        "\tram-console {\n"
        "\t\tcompatible = \"mediatek,mt6797-ram-console\";\n"
        "\t\tmemory-region = <&ram_console_reserved>;\n"
        "\t\tstatus = \"disabled\";\n"
        "\t};\n\n"
        "\treserved-memory {\n",
    )
    replace_once(
        dts,
        "\t\tmemory@44400000 {\n",
        "\t\tram_console_reserved: memory@44400000 {\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("binding", "driver", "dt"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not (root / "drivers/soc/mediatek/Kconfig").is_file():
        raise SystemExit("unexpected source root")
    experiment = Path(__file__).resolve().parents[1]
    if args.phase == "binding":
        apply_binding(root, experiment)
    elif args.phase == "driver":
        apply_driver(root, experiment)
    else:
        apply_dt(root)


if __name__ == "__main__":
    main()
