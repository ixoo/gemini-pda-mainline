#!/usr/bin/env python3
"""Apply the independent CPU9 pre-ledger progress source edit."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
from textwrap import dedent


HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
PARENT_HASHES = {
    "fs/pstore/Kconfig":
        "6d9125da9098a67afd38e7466f3ae04c3fad30b7bbb37ac214704ad0c1795d1d",
    "fs/pstore/Makefile":
        "0d68246afa1608dadd09358206026035dde118ba659e11df5b6b92c9d108b371",
}
NEW_PATHS = {
    "fs/pstore/gemini_cpu9_progress_ledger.c":
        "gemini_cpu9_progress_ledger.c",
    "fs/pstore/gemini_cpu9_progress_ledger_internal.h":
        "gemini_cpu9_progress_ledger_internal.h",
    "fs/pstore/gemini_cpu9_progress_ledger_test.c":
        "gemini_cpu9_progress_ledger_test.c",
    "include/linux/gemini_cpu9_progress_ledger.h":
        "gemini_cpu9_progress_ledger.h",
}

KCONFIG = dedent("""\
    config PSTORE_GEMINI_CPU9_PROGRESS_LEDGER
    \tbool "Gemini CPU9 pre-ledger progress ledger"
    \tdepends on PSTORE_GEMINI_CPU9_TRANSITION_LEDGER=y
    \tdefault n
    \thelp
    \t  Add one bounded mutable progress lane in the third exact Gemini
    \t  ramoops dmesg record. It first requires the exact CRC-valid CPU8
    \t  online terminal in record 0 and an exact logical-empty progress lane.

    \t  Ten ordered boundaries use the existing alternating two-copy CRC
    \t  wire. At most 20 record commits and 202 32-bit writes occur in the
    \t  one owned record. The owner never clears, repairs, retries, or accepts
    \t  a nonempty predecessor. This option adds no production caller, CPU
    \t  request, watchdog, SMC, cluster effect, reset, storage, or boot policy.

    config PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST
    \tbool "KUnit tests for the Gemini CPU9 progress ledger"
    \tdepends on KUNIT=y
    \tdepends on PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y
    \tdefault n
    \thelp
    \t  Test exact CPU8 proof, logical-empty ownership, all ten ordered
    \t  boundaries, attempt binding, write bound, and refusal of replay,
    \t  malformed, raw, or committed progress lanes in injected word arrays.

    \t  No retained RAM, MMIO, CPU request, watchdog, SMC, regulator, clock,
    \t  storage, reset, reboot, or device action is performed.

    """)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"{label} anchor changed: {text.count(old)}")
    return text.replace(old, new)


def apply(root: Path) -> None:
    root = root.resolve()
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise ValueError(f"progress parent changed: {relative}")
    for relative in NEW_PATHS:
        if (root / relative).exists():
            raise ValueError(f"progress path already exists: {relative}")

    kconfig = root / "fs/pstore/Kconfig"
    text = kconfig.read_text(encoding="utf-8")
    anchor = "config PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST\n"
    text = replace_once(text, anchor, KCONFIG + anchor, "pstore Kconfig")
    kconfig.write_text(text, encoding="utf-8")

    makefile = root / "fs/pstore/Makefile"
    text = makefile.read_text(encoding="utf-8")
    anchor = (
        "obj-$(CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER) += "
        "gemini_cpu9_transition_ledger.o\n"
    )
    addition = (
        anchor
        + "obj-$(CONFIG_PSTORE_GEMINI_CPU9_PROGRESS_LEDGER) += "
        "gemini_cpu9_progress_ledger.o\n"
        + "obj-$(CONFIG_PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST) += "
        "gemini_cpu9_progress_ledger_test.o\n"
    )
    text = replace_once(text, anchor, addition, "pstore Makefile")
    makefile.write_text(text, encoding="utf-8")

    for relative, template in NEW_PATHS.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEMPLATES / template, target)
