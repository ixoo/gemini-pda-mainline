#!/usr/bin/env python3
"""Apply the deterministic first-dmesg protected-clock call-ledger edit."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


MODE = "CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply(root: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    mode_config = dedent(r'''
config PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION
	bool "Gemini protected-clock first-dmesg call qualification"
	depends on PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER=y
	depends on !PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION
	default n
	help
	  Move the existing clock-only observer's before-call and after-return
	  records from sparse dmesg zones 173 and 174 to consecutive records 1
	  and 2. Retain the qualified all-ones entry-header gate, signature-last
	  commit, full local readback, two-write ceiling, and no-clear/no-retry
	  policy.

	  The observer still makes exactly one protected clock read and zero
	  BigiDVFS reads. This mode adds no caller, transport operation, secure
	  call, owner registration, CPU request, storage, reset, or power action.
	  If unsure, say N.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n",
        mode_config + "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n",
    )

    ledger = root / "fs/pstore/gemini_protected_readback_ledger.c"
    old_layout = dedent(r'''
#if defined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION) || \
	defined(CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION)
#define GEMINI_PRB_LEDGER_BASE		GEMINI_PRB_RESERVE_BASE
#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION
#define GEMINI_PRB_SLOT_COUNT		1
#else
#define GEMINI_PRB_SLOT_COUNT		2
#endif
#define GEMINI_PRB_FIRST_OWNED_SLOT	0
''').lstrip("\n")
    new_layout = dedent(r'''
#if defined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION) || \
	defined(CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION) || \
	defined(CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION)
#define GEMINI_PRB_LEDGER_BASE		GEMINI_PRB_RESERVE_BASE
#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION
#define GEMINI_PRB_SLOT_COUNT		1
#else
#define GEMINI_PRB_SLOT_COUNT		2
#endif
#define GEMINI_PRB_FIRST_OWNED_SLOT	0
''').lstrip("\n")
    replace_once(ledger, old_layout, new_layout)

    records_anchor = (
        "#ifdef CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION\n"
    )
    records = dedent(r'''
#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 token=GPCF-20260823-A "
	"checkpoint=before-clock slot=1 crc32=183854b2\n",
	"====0.000000-D\n"
	"GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 token=GPCF-20260823-A "
	"checkpoint=after-clock slot=2 crc32=d14b85aa\n",
};
#elif defined(CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION)
''').lstrip("\n")
    replace_once(ledger, records_anchor, records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root.resolve())


if __name__ == "__main__":
    main()
