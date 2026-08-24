#!/usr/bin/env python3
"""Apply the deterministic A72 observer init/probe ledger successor."""

from __future__ import annotations

import argparse
from pathlib import Path


MODE = "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}: expected one anchor beginning {old.splitlines()[0]!r}, "
            f"found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply(root: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    replace_once(
        kconfig,
        "\t  Give the physical-source observer one retained record at probe entry and\n"
        "\t  one after all three bound source devices are held. Release the references\n"
        "\t  and return success after the second record without running the capture.\n\n"
        "\t  Reuse the qualified first-dmesg writer with at most two short writes and\n"
        "\t  no overwrite, clear, retry, physical snapshot, provider transaction,\n"
        "\t  owner mutation, CPU request, reset, reboot, or power action.\n",
        "\t  Give the physical-source observer one retained record in its built-in\n"
        "\t  init before driver registration and one as the first probe operation.\n"
        "\t  Return before allocation or source lookup after the second record.\n\n"
        "\t  Reuse the qualified first-dmesg writer with at most two short writes and\n"
        "\t  no overwrite, clear, retry, allocation, physical snapshot, provider\n"
        "\t  transaction, owner mutation, CPU request, reset, reboot, or power action.\n",
    )

    ledger = root / "fs/pstore/gemini_protected_readback_ledger.c"
    replace_once(
        ledger,
        "\t\"GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A \"\n"
        "\t\"checkpoint=probe-enter slot=1 crc32=b8f6c566\\n\",\n"
        "\t\"====0.000000-D\\n\"\n"
        "\t\"GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A \"\n"
        "\t\"checkpoint=sources-held slot=2 crc32=9e7fd3e6\\n\",\n",
        "\t\"GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A \"\n"
        "\t\"checkpoint=driver-init slot=1 crc32=85e5f336\\n\",\n"
        "\t\"====0.000000-D\\n\"\n"
        "\t\"GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A \"\n"
        "\t\"checkpoint=probe-enter slot=2 crc32=85116721\\n\",\n",
    )

    observer = root / (
        "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    )
    replace_once(
        observer,
        "#include <linux/errno.h>\n#include <linux/module.h>\n",
        "#include <linux/errno.h>\n#include <linux/init.h>\n#include <linux/module.h>\n",
    )
    replace_once(
        observer,
        f"#ifdef {MODE}\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(0))\n"
        "\t\treturn dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t     \"probe-enter ledger checkpoint failed\\n\");\n"
        "#endif\n\n"
        "\tsnapshot = kvzalloc_obj(*snapshot);\n",
        f"#ifdef {MODE}\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(1))\n"
        "\t\treturn dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t     \"probe-enter ledger checkpoint failed\\n\");\n"
        "\tdev_info(dev, \"init/probe ledger complete; source lookup disabled\\n\");\n"
        "\treturn 0;\n"
        "#endif\n\n"
        "\tsnapshot = kvzalloc_obj(*snapshot);\n",
    )
    replace_once(
        observer,
        f"#ifdef {MODE}\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(1)) {\n"
        "\t\tret = dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t    \"sources-held ledger checkpoint failed\\n\");\n"
        "\t\tgoto put_bigidvfs;\n"
        "\t}\n"
        "\tdev_info(dev, \"pre-capture ledger complete; capture disabled\\n\");\n"
        "\tret = 0;\n"
        "\tgoto put_bigidvfs;\n"
        "#endif\n\n",
        "",
    )
    replace_once(
        observer,
        f"#ifdef {MODE}\n"
        "put_bigidvfs:\n"
        "#endif\n",
        "",
    )
    replace_once(
        observer,
        "builtin_platform_driver(mt6797_a72_physical_source_driver);\n",
        "\nstatic int __init mt6797_a72_physical_source_init(void)\n"
        "{\n"
        f"#ifdef {MODE}\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(0))\n"
        "\t\treturn -EIO;\n"
        "#endif\n\n"
        "\treturn platform_driver_register(&mt6797_a72_physical_source_driver);\n"
        "}\n"
        "device_initcall(mt6797_a72_physical_source_init);\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root.resolve())


if __name__ == "__main__":
    main()
