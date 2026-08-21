#!/usr/bin/env python3
"""Validate the generated retained ram-console copy-owner source tree."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    reader = (root / "drivers/soc/mediatek/mtk-ram-console-reader.c").read_text()
    header = (root / "include/linux/soc/mediatek/mtk-ram-console.h").read_text()
    binding = (root / "Documentation/devicetree/bindings/soc/mediatek/"
               "mediatek,mt6797-ram-console.yaml").read_text()
    dts = (root / "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts").read_text()
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text()
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text()

    require(reader.count("memremap(") == 1, "one physical map call")
    require(reader.count("memunmap(") == 1, "one physical unmap call")
    require("MEMREMAP_WB" in reader, "ordinary-memory mapping")
    require("of_reserved_mem_region_count" in reader, "one-region check")
    require("of_reserved_mem_region_to_resource" in reader,
            "reserved-memory resource lookup")
    require('of_property_read_bool(memory, "no-map")' in reader,
            "no-map check")
    require("resource_size(&resource) != MTK_RAM_CONSOLE_READER_SIZE" in reader,
            "exact resource-size check")
    require(reader.count("KUNIT_CASE(mtk_ram_console_reader_") == 7,
            "seven focused KUnit cases")
    require("state->attempted = true;" in reader, "attempt latch")
    require("return -EALREADY;" in reader, "second-capture refusal")
    require("mtk_ram_console_parse(buffer, size, &snapshot)" in reader,
            "parser invocation on copied buffer")
    require("mtk_ram_console_snapshot_get" in reader + header,
            "typed snapshot getter")

    for token in (
        "ioremap(", "devm_memremap(", "readl(", "writel(", "debugfs",
        "proc_create", "nvmem", "0x44400000", "cpu_up", "cpu_boot",
        "psci_ops", "reset_provenance", "safe_reset",
    ):
        require(token not in reader + header,
                f"forbidden reader/header token: {token}")

    require("const: mediatek,mt6797-ram-console" in binding,
            "binding compatible")
    require("memory-region:" in binding and "maxItems: 1" in binding,
            "binding one-region contract")
    require("additionalProperties: false" in binding,
            "closed binding")
    require(dts.count("ram_console_reserved: memory@44400000") == 1,
            "exact labeled Gemini reservation")
    require(dts.count('compatible = "mediatek,mt6797-ram-console";') == 1,
            "one Gemini consumer")
    require("memory-region = <&ram_console_reserved>;" in dts,
            "Gemini memory-region linkage")
    consumer = dts.split("\tram-console {", 1)[1].split("\t};", 1)[0]
    require('status = "disabled";' in consumer, "default-off Gemini consumer")

    require(kconfig.count("config MTK_RAM_CONSOLE_READER\n") == 1,
            "reader Kconfig")
    require(kconfig.count("config MTK_RAM_CONSOLE_READER_KUNIT_TEST\n") == 1,
            "reader KUnit Kconfig")
    require(makefile.count("CONFIG_MTK_RAM_CONSOLE_READER") == 1,
            "reader Makefile entry")

    print("source_validation=pass")
    print("generated_patch_count=3")
    print("kunit_case_count=7")
    print("physical_map_call_count=1")
    print("physical_unmap_call_count=1")
    print("copy_attempt_limit=1")
    print("dt_default=disabled")
    print("reset_classifier=none")
    print("a34_caller=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
