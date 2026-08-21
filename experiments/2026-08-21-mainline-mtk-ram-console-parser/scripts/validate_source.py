#!/usr/bin/env python3
"""Validate generated MediaTek retained ram-console parser source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    source = (root / "drivers/soc/mediatek/mtk-ram-console.c").read_text()
    header = (
        root / "include/linux/soc/mediatek/mtk-ram-console.h"
    ).read_text()
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text()
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text()

    for token in (
        "config MTK_RAM_CONSOLE_PARSER",
        "depends on ARM64 && ARCH_MEDIATEK",
        "config MTK_RAM_CONSOLE_PARSER_KUNIT_TEST",
        "select MTK_RAM_CONSOLE_PARSER",
    ):
        require(token in kconfig, f"Kconfig token: {token}")
    require(
        "obj-$(CONFIG_MTK_RAM_CONSOLE_PARSER) += mtk-ram-console.o"
        in makefile,
        "Makefile object",
    )

    for token in (
        "MTK_RAM_CONSOLE_SIGNATURE\t0x43474244",
        "MTK_RAM_CONSOLE_HEADER_SIZE\t64",
        "MTK_RAM_CONSOLE_LK_SIZE\t\t64",
        "off_pl != MTK_RAM_CONSOLE_HEADER_SIZE",
        "sz_pl < sizeof(u32)",
        "check_add_overflow",
        "end != off_lpl",
        "end != off_lk",
        "end != off_llk",
        "end != off_linux",
        "off_console < off_linux",
        "snapshot->preloader_status = get_unaligned_le32(bytes + off_pl)",
        "EXPORT_SYMBOL_GPL(mtk_ram_console_parse)",
    ):
        require(token in source, f"strict parser token: {token}")
    require(source.count("get_unaligned_le32(bytes + off_pl)") == 1,
            "one status extraction")
    require(source.count("KUNIT_CASE(mtk_ram_console_") == 8,
            "eight focused KUnit cases")
    for case in (
        "invalid_arguments", "truncated", "signature", "buffer_size",
        "preloader_layout", "lk_layout", "exact", "every_bit",
    ):
        require(f"mtk_ram_console_{case}_test" in source,
                f"KUnit case: {case}")

    for token in (
        "struct mtk_ram_console_snapshot",
        "u32 preloader_status;",
        "bool valid;",
        "mtk_ram_console_parse",
        "return -EOPNOTSUPP;",
    ):
        require(token in header, f"public header token: {token}")

    forbidden = (
        "ioremap", "memremap", "of_reserved_mem", "readl(", "writel(",
        "ioread", "iowrite", "psci", "cpu_up", "cpu_down", "cpu_boot",
        "mt6797_a72_a34_evaluate", "reset_provenance", "safe_reset",
        "platform_reset", "external_reset", "device_node",
    )
    for token in forbidden:
        require(token not in source + header,
                f"forbidden mapping/classifier/effect token: {token}")

    print("source_validation=pass")
    print("wire_header_size=64")
    print("status_extractions=1")
    print("kunit_cases=8")
    print("physical_mapping=none")
    print("reset_classifier=none")
    print("a34_caller=none")
    print("hardware_action=none")


if __name__ == "__main__":
    main()
