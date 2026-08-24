#!/usr/bin/env python3
"""Apply the deterministic A72 global initcall ledger successor."""

from __future__ import annotations

import argparse
from pathlib import Path


NEW_MODE = "CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER"
OLD_MODE = "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER"


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
    base_anchor = "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n"
    block = (
        "config PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER\n"
        "\tbool \"Gemini A72 global initcall retained ledger\"\n"
        "\tdepends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y\n"
        "\tdepends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y\n"
        "\tdepends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER\n"
        "\tdepends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER\n"
        "\tdepends on !PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL\n"
        "\tdepends on !PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER\n"
        "\tdepends on !PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER\n"
        "\tdepends on !PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER\n"
        "\tdepends on !PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION\n"
        "\tdepends on !PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION\n"
        "\tdepends on !PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION\n"
        "\tdefault n\n"
        "\thelp\n"
        "\t  Commit retained record 1 from a global subsys initcall and record 2\n"
        "\t  from a later fs initcall. Do not register the physical-source observer.\n"
        "\t  This localizes progress before its rejected device initcall boundary.\n\n"
        "\t  Reuse the qualified first-dmesg writer with at most two short writes,\n"
        "\t  no overwrite, clear, or retry, and no observer registration, allocation,\n"
        "\t  source lookup, snapshot, provider transaction, clock or BigiDVFS call,\n"
        "\t  publication, owner mutation, CPU request, reset, reboot, or power action.\n"
        "\t  If unsure, say N.\n\n"
    )
    replace_once(kconfig, base_anchor, block + base_anchor)

    ledger = root / "fs/pstore/gemini_protected_readback_ledger.c"
    replace_once(
        ledger,
        "#include <linux/init.h>\n",
        "#include <linux/errno.h>\n#include <linux/init.h>\n",
    )
    for anchor in (
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER)\n",
        "#if defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER) || \\\n",
    ):
        text = ledger.read_text(encoding="utf-8")
        expected = 1 if anchor.startswith("\tdefined") else 2
        if text.count(anchor) != expected:
            raise SystemExit(f"{ledger}: expected {expected} conditional anchors")
        replacement = (
            anchor.rstrip("\n") + " || \\\n"
            "\tdefined(CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER)\n"
            if anchor.startswith("\tdefined")
            else "#if defined(CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER) || \\\n"
                 "\tdefined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER) || \\\n"
        )
        ledger.write_text(text.replace(anchor, replacement), encoding="utf-8")

    records_anchor = f"#ifdef {OLD_MODE}\n"
    records = (
        f"#ifdef {NEW_MODE}\n"
        "static const char * const gemini_prb_records[] = {\n"
        "\t\"====0.000000-D\\n\"\n"
        "\t\"GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A \"\n"
        "\t\"checkpoint=subsys-init slot=1 crc32=cf2a6946\\n\",\n"
        "\t\"====0.000000-D\\n\"\n"
        "\t\"GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A \"\n"
        "\t\"checkpoint=fs-init slot=2 crc32=91ac2a49\\n\",\n"
        "};\n"
        f"#elif defined({OLD_MODE})\n"
    )
    replace_once(ledger, records_anchor, records)

    init_anchor = "\n#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL\n"
    initcalls = (
        f"\n#ifdef {NEW_MODE}\n"
        "static int __init gemini_a72_subsys_initcall_checkpoint(void)\n"
        "{\n"
        "\treturn gemini_protected_readback_ledger_checkpoint(0) ? 0 : -EIO;\n"
        "}\n"
        "subsys_initcall(gemini_a72_subsys_initcall_checkpoint);\n\n"
        "static int __init gemini_a72_fs_initcall_checkpoint(void)\n"
        "{\n"
        "\treturn gemini_protected_readback_ledger_checkpoint(1) ? 0 : -EIO;\n"
        "}\n"
        "fs_initcall(gemini_a72_fs_initcall_checkpoint);\n"
        "#endif\n"
    )
    replace_once(ledger, init_anchor, initcalls + init_anchor)

    observer = root / (
        "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    )
    init = (
        "static int __init mt6797_a72_physical_source_init(void)\n"
        "{\n"
    )
    replacement = (
        init + f"#ifdef {NEW_MODE}\n"
        "\treturn 0;\n"
        "#endif\n\n"
    )
    replace_once(observer, init, replacement)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root.resolve())


if __name__ == "__main__":
    main()
