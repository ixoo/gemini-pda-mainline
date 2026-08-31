#!/usr/bin/env python3
"""Apply the independent Gemini CPU9 retained-ledger source edit."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
from textwrap import dedent


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES = SCRIPT_DIR.parent / "templates"
PARENT_HASHES = {
    "fs/pstore/Kconfig":
        "59086d37659fe94b18150336a3aab898f27ae075a8654361cb82ee3b217348b2",
    "fs/pstore/Makefile":
        "1facc86e96ccca27e47ab7116b554fa39c027f514631f13d15738366335e6576",
    "fs/pstore/gemini_transition_ledger.c":
        "83581a5a5a770f2d83fd1994cae2fcf41bbc4cd9f9dab87e691442ab6368d30b",
    "fs/pstore/gemini_transition_ledger_internal.h":
        "49a8969ab72fc5b8cc8e40700eab3741595596dd1a81b6e2438a289c42d1eae3",
    "include/linux/gemini_transition_ledger.h":
        "213d097627d3df1c5c3e7e6d3973e7b49dc7c7fc7f70bb86b2fab534fc833965",
}
NEW_PATHS = (
    "fs/pstore/gemini_cpu9_transition_ledger.c",
    "fs/pstore/gemini_cpu9_transition_ledger_internal.h",
    "fs/pstore/gemini_cpu9_transition_ledger_test.c",
    "include/linux/gemini_cpu9_transition_ledger.h",
)

KCONFIG = dedent("""\
    config PSTORE_GEMINI_CPU9_TRANSITION_LEDGER
    \tbool "Gemini independent CPU9 transition ledger"
    \tdepends on PSTORE_GEMINI_TRANSITION_LEDGER=y
    \tdefault n
    \thelp
    \t  Add a one-shot API for the second exact Gemini ramoops dmesg
    \t  record. The owner accepts an empty record only after record 0
    \t  contains the expected CRC-valid CPU8 online terminal from the
    \t  caller-supplied CPU8 attempt.

    \t  The lane reuses the proven two-copy wire format but has independent
    \t  physical ownership and sealing. It adds no caller, CPU request,
    \t  watchdog action, SMC, cluster-power action, or boot policy. If
    \t  unsure, say N.

    config PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST
    \tbool "KUnit tests for the Gemini CPU9 transition ledger"
    \tdepends on KUNIT=y
    \tdepends on PSTORE_GEMINI_CPU9_TRANSITION_LEDGER=y
    \tdefault n
    \thelp
    \t  Test the CPU8 terminal gate, exact attempt binding, empty-only CPU9
    \t  ownership, raw-header commit, five-stage sequence, and terminal
    \t  sealing in injected word arrays.

    \t  No retained RAM, MMIO, CPU request, watchdog, SMC, regulator, clock,
    \t  or cluster-power operation is used.

    """)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"parent source is absent or unsafe: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"parent source changed: {relative}: {actual}")
    for relative in NEW_PATHS:
        if (root / relative).exists():
            raise SystemExit(f"new CPU9 path already exists: {relative}")


def copy_new(root: Path, relative: str) -> None:
    source = TEMPLATES / Path(relative).name
    target = root / relative
    if not source.is_file() or source.is_symlink():
        raise SystemExit(f"template is absent or unsafe: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def apply(root: Path) -> None:
    root = root.resolve()
    validate_parent(root)
    replace_once(
        root / "fs/pstore/Kconfig",
        "config PSTORE_GEMINI_ADMISSION_TRACE\n",
        KCONFIG + "config PSTORE_GEMINI_ADMISSION_TRACE\n",
    )
    replace_once(
        root / "fs/pstore/Makefile",
        "obj-$(CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER) += "
        "gemini_transition_ledger.o\n",
        "obj-$(CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER) += "
        "gemini_transition_ledger.o\n"
        "obj-$(CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER) += "
        "gemini_cpu9_transition_ledger.o\n"
        "obj-$(CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST) += "
        "gemini_cpu9_transition_ledger_test.o\n",
    )
    for relative in NEW_PATHS:
        copy_new(root, relative)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root)
