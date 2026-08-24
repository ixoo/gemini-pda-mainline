#!/usr/bin/env python3
"""Apply the deterministic A72 physical-source pre-capture ledger."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


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
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER\n"
        "\tbool \"Gemini A72 physical-source retained ledger\"\n"
        "\tdepends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y\n"
        "\tdepends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y\n",
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER\n"
        "\tbool \"Gemini A72 physical-source retained ledger\"\n"
        "\tdepends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y\n"
        "\tdepends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y\n"
        "\tdepends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER\n",
    )
    mode = dedent(r'''
config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER
	bool "Gemini A72 physical-source pre-capture ledger"
	depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y
	depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y
	depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER
	depends on !PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION
	depends on !PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION
	depends on !PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION
	default n
	help
	  Give the physical-source observer one retained record at probe entry and
	  one after all three bound source devices are held. Release the references
	  and return success after the second record without running the capture.

	  Reuse the qualified first-dmesg writer with at most two short writes and
	  no overwrite, clear, retry, physical snapshot, provider transaction,
	  owner mutation, CPU request, reset, reboot, or power action.
	  If unsure, say N.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n",
        mode + "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n",
    )

    ledger = root / "fs/pstore/gemini_protected_readback_ledger.c"
    replace_once(
        ledger,
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER)\n"
        "#define GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE\n",
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER)\n"
        "#define GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE\n",
    )
    records = dedent(r'''
#ifdef CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A "
	"checkpoint=probe-enter slot=1 crc32=b8f6c566\n",
	"====0.000000-D\n"
	"GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A "
	"checkpoint=sources-held slot=2 crc32=9e7fd3e6\n",
};
#elif defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER)
''').lstrip("\n")
    replace_once(
        ledger,
        "#ifdef CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER\n",
        records,
    )
    raw_anchor = (
        "#if defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER) || \\\n"
    )
    raw_replacement = (
        "#if defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER) || \\\n"
    )
    text = ledger.read_text(encoding="utf-8")
    if text.count(raw_anchor) != 2:
        raise SystemExit("ledger: expected two physical raw-mode conditionals")
    ledger.write_text(text.replace(raw_anchor, raw_replacement), encoding="utf-8")

    observer = root / (
        "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    )
    replace_once(
        observer,
        "\tstruct device *dev = &pdev->dev;\n\tint ret;\n\n"
        "\tsnapshot = kvzalloc_obj(*snapshot);\n",
        "\tstruct device *dev = &pdev->dev;\n\tint ret;\n\n"
        f"#ifdef {MODE}\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(0))\n"
        "\t\treturn dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t     \"probe-enter ledger checkpoint failed\\n\");\n"
        "#endif\n\n"
        "\tsnapshot = kvzalloc_obj(*snapshot);\n",
    )
    replace_once(
        observer,
        "\tret = mt6797_a72_physical_source_run(&context, &mt6797_physical_runtime,\n"
        "\t\t\t\t\t     snapshot);\n",
        f"#ifdef {MODE}\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(1)) {\n"
        "\t\tret = dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t    \"sources-held ledger checkpoint failed\\n\");\n"
        "\t\tgoto put_bigidvfs;\n"
        "\t}\n"
        "\tdev_info(dev, \"pre-capture ledger complete; capture disabled\\n\");\n"
        "\tret = 0;\n"
        "\tgoto put_bigidvfs;\n"
        "#endif\n\n"
        "\tret = mt6797_a72_physical_source_run(&context, &mt6797_physical_runtime,\n"
        "\t\t\t\t\t     snapshot);\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root.resolve())


if __name__ == "__main__":
    main()
