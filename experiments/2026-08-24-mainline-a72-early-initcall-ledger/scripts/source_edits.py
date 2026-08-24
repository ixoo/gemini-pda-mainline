#!/usr/bin/env python3
"""Apply the deterministic A72 early-initcall ledger successor."""

from __future__ import annotations

import argparse
from pathlib import Path


NEW_MODE = "CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER"
PARENT_MODE = "CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}: expected one anchor beginning {old.splitlines()[0]!r}, "
            f"found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_count(path: Path, old: str, new: str, expected: int) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} conditional anchors, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def apply(root: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    base_anchor = "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n"
    block = (
        "config PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER\n"
        "\tbool \"Gemini A72 early initcall retained ledger\"\n"
        "\tdepends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y\n"
        "\tdepends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y\n"
        "\tdepends on !PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER\n"
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
        "\t  Commit record 1 from pure initcall and record 2 from core initcall.\n"
        "\t  If the pure checkpoint refuses, record one fixed refusal marker in\n"
        "\t  slot 2 only after repeating the exact DT, map, and raw-header gates.\n"
        "\t  Do not register the physical-source observer.\n\n"
        "\t  Make at most two short retained write attempts with no overwrite,\n"
        "\t  clear, or retry, and no observer registration, allocation, source\n"
        "\t  lookup, snapshot, provider transaction, clock or BigiDVFS call,\n"
        "\t  publication, owner mutation, CPU request, reset, reboot, or power\n"
        "\t  action. If unsure, say N.\n\n"
    )
    replace_once(kconfig, base_anchor, block + base_anchor)

    ledger = root / "fs/pstore/gemini_protected_readback_ledger.c"
    replace_once(
        ledger,
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER)\n"
        "#define GEMINI_PRB_LEDGER_BASE",
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER)\n"
        "#define GEMINI_PRB_LEDGER_BASE",
    )
    replace_count(
        ledger,
        "#if defined(CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER) || \\\n",
        "#if defined(CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER) || \\\n",
        2,
    )

    records_anchor = (
        f"#ifdef {PARENT_MODE}\n"
        "static const char * const gemini_prb_records[] = {\n"
    )
    records = (
        f"#ifdef {NEW_MODE}\n"
        "static const char * const gemini_prb_records[] = {\n"
        "\t\"====0.000000-D\\n\"\n"
        "\t\"GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A \"\n"
        "\t\"checkpoint=pure-init outcome=commit slot=1 crc32=03d9627f\\n\",\n"
        "\t\"====0.000000-D\\n\"\n"
        "\t\"GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A \"\n"
        "\t\"checkpoint=core-init outcome=commit slot=2 crc32=57dd63b5\\n\",\n"
        "};\n\n"
        "static const char gemini_prb_refusal_record[] =\n"
        "\t\"====0.000000-D\\n\"\n"
        "\t\"GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A \"\n"
        "\t\"checkpoint=pure-init outcome=primary-refused slot=2 \"\n"
        "\t\"crc32=5767e326\\n\";\n"
        f"#elif defined({PARENT_MODE})\n"
        "static const char * const gemini_prb_records[] = {\n"
    )
    replace_once(ledger, records_anchor, records)

    init_anchor = (
        f"\n#ifdef {PARENT_MODE}\n"
        "static int __init gemini_a72_subsys_initcall_checkpoint(void)\n"
    )
    early = (
        f"\n#ifdef {NEW_MODE}\n"
        "static bool gemini_a72_pure_refusal_checkpoint(void)\n"
        "{\n"
        "\tvoid __iomem *ledger;\n"
        "\tvoid __iomem *slot;\n"
        "\tbool written = false;\n\n"
        "\tif (!gemini_prb_exact_dt())\n"
        "\t\treturn false;\n"
        "\tledger = ioremap_wc(GEMINI_PRB_LEDGER_BASE,\n"
        "\t\t\t    GEMINI_PRB_SLOT_COUNT * GEMINI_PRB_SLOT_SIZE);\n"
        "\tif (!ledger)\n"
        "\t\treturn false;\n"
        "\tslot = (u8 __iomem *)ledger + GEMINI_PRB_SLOT_SIZE;\n"
        "\tif (gemini_prb_slot_available(slot))\n"
        "\t\twritten = gemini_prb_write(slot, gemini_prb_refusal_record);\n"
        "\tiounmap(ledger);\n\n"
        "\treturn written;\n"
        "}\n\n"
        "static int __init gemini_a72_pure_initcall_checkpoint(void)\n"
        "{\n"
        "\tif (gemini_protected_readback_ledger_checkpoint(0))\n"
        "\t\treturn 0;\n"
        "\treturn gemini_a72_pure_refusal_checkpoint() ? -EAGAIN : -EIO;\n"
        "}\n"
        "pure_initcall(gemini_a72_pure_initcall_checkpoint);\n\n"
        "static int __init gemini_a72_core_initcall_checkpoint(void)\n"
        "{\n"
        "\treturn gemini_protected_readback_ledger_checkpoint(1) ? 0 : -EIO;\n"
        "}\n"
        "core_initcall(gemini_a72_core_initcall_checkpoint);\n"
        "#endif\n"
    )
    replace_once(ledger, init_anchor, early + init_anchor)

    observer = root / "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    old_guard = (
        "#ifdef CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER\n"
        "\treturn 0;\n"
        "#endif\n"
    )
    new_guard = (
        "#if defined(CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER)\n"
        "\treturn 0;\n"
        "#endif\n"
    )
    replace_once(observer, old_guard, new_guard)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root.resolve())


if __name__ == "__main__":
    main()
