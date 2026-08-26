#!/usr/bin/env python3
"""Apply deterministic Gemini transition-ledger source edits."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from textwrap import dedent


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES = SCRIPT_DIR.parent / "templates"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


PRODUCTION_KCONFIG = dedent("""\
    config PSTORE_GEMINI_TRANSITION_LEDGER
    \tbool "Gemini mutable retained transition ledger"
    \tdepends on PSTORE_RAM=y
    \tdepends on ARM64 && ARCH_MEDIATEK && OF
    \tdepends on !PSTORE_GEMINI_PRE_RAMOOPS_LEDGER
    \tdepends on !PSTORE_GEMINI_ARM64_ENTRY_LEDGER
    \tdepends on !PSTORE_GEMINI_PROTECTED_READBACK_LEDGER
    \tselect CRC32
    \tdefault n
    \thelp
    \t  Add a one-shot API that updates one compact retained CPU-transition
    \t  ledger in the first exact Gemini ramoops dmesg zone. Two alternating
    \t  copies preserve the last complete attempt, phase, stage, terminal,
    \t  generation, and CRC32 while the older copy is replaced.

    \t  The owner requires the exact Gemini model and reservation, accepts
    \t  only an empty, raw all-ones, or previously valid ledger header, and
    \t  seals on a write/readback fault or terminal record. Normal ramoops is
    \t  bypassed only on the Gemini while this isolated option is selected.

    \t  This option adds no caller, CPU request, watchdog action, SMC, device
    \t  trigger, or boot policy. If unsure, say N.

    """)

TEST_KCONFIG = dedent("""\
    config PSTORE_GEMINI_TRANSITION_LEDGER_KUNIT_TEST
    \tbool "KUnit tests for the Gemini transition ledger"
    \tdepends on KUNIT=y
    \tdepends on PSTORE_GEMINI_TRANSITION_LEDGER=y
    \tdefault n
    \thelp
    \t  Test all 18 ordered checkpoints plus terminal commit, raw-header
    \t  signature-last ordering, refusal cases, torn-write preservation,
    \t  corrupt-copy recovery, and one-shot sealing in an injected word array.

    \t  No retained RAM, MMIO, watchdog, SMC, or CPU operation is used.

    """)


def copy_new(root: Path, template: str, relative: str) -> None:
    target = root / relative
    if target.exists():
        raise SystemExit(f"new path already exists: {relative}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATES / template, target)


def apply_production(root: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    makefile = root / "fs/pstore/Makefile"
    ram = root / "fs/pstore/ram.c"

    replace_once(kconfig, "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n",
                 PRODUCTION_KCONFIG +
                 "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n")
    replace_once(
        makefile,
        "obj-$(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER) += "
        "gemini_protected_readback_ledger.o\n",
        "obj-$(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER) += "
        "gemini_protected_readback_ledger.o\n"
        "obj-$(CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER) += "
        "gemini_transition_ledger.o\n",
    )
    replace_once(
        ram,
        "#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n"
        "\tif (of_machine_is_compatible(\"planet,gemini-pda\"))\n"
        "\t\treturn 0;\n"
        "#endif\n",
        "#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n"
        "\tif (of_machine_is_compatible(\"planet,gemini-pda\"))\n"
        "\t\treturn 0;\n"
        "#endif\n"
        "#ifdef CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER\n"
        "\tif (of_machine_is_compatible(\"planet,gemini-pda\"))\n"
        "\t\treturn 0;\n"
        "#endif\n",
    )
    copy_new(root, "gemini_transition_ledger.c",
             "fs/pstore/gemini_transition_ledger.c")
    copy_new(root, "gemini_transition_ledger_internal.h",
             "fs/pstore/gemini_transition_ledger_internal.h")
    copy_new(root, "gemini_transition_ledger.h",
             "include/linux/gemini_transition_ledger.h")


def apply_tests(root: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    makefile = root / "fs/pstore/Makefile"

    replace_once(kconfig, "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n",
                 TEST_KCONFIG +
                 "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n")
    replace_once(
        makefile,
        "obj-$(CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER) += "
        "gemini_transition_ledger.o\n",
        "obj-$(CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER) += "
        "gemini_transition_ledger.o\n"
        "obj-$(CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER_KUNIT_TEST) += "
        "gemini_transition_ledger_test.o\n",
    )
    copy_new(root, "gemini_transition_ledger_test.c",
             "fs/pstore/gemini_transition_ledger_test.c")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "production":
        apply_production(root)
    else:
        apply_tests(root)


if __name__ == "__main__":
    main()
