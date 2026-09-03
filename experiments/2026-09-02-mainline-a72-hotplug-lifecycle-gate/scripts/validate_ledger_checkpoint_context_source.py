#!/usr/bin/env python3
"""Validate the non-sleeping record-4 checkpoint production path."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


LEDGER = "fs/pstore/gemini_a72_hotplug_ledger.c"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def function(text: str, name: str) -> str:
    match = re.search(
        rf"^int {re.escape(name)}\([^\n]*\n(?:.*\n)*?^\}}\n",
        text,
        re.MULTILINE,
    )
    require(match is not None, f"missing function: {name}")
    return match.group(0)


def validate(root: Path) -> None:
    path = root / LEDGER
    require(path.is_file() and not path.is_symlink(), "ledger source missing")
    text = path.read_text(encoding="utf-8")
    begin = function(text, "gemini_a72_hotplug_ledger_begin")
    checkpoint = function(text, "gemini_a72_hotplug_ledger_checkpoint")

    for token in (
        "#include <linux/mutex.h>",
        "#include <linux/spinlock.h>",
        "DEFINE_MUTEX(gemini_a72_hotplug_ledger_begin_lock)",
        "DEFINE_RAW_SPINLOCK(gemini_a72_hotplug_ledger_checkpoint_lock)",
    ):
        require(token in text, f"locking contract missing: {token}")
    for token in (
        "mutex_lock(&gemini_a72_hotplug_ledger_begin_lock);",
        "gemini_a72_hotplug_ledger_exact_dt()",
        "ioremap_wc(GEMINI_A72_HOTPLUG_LEDGER_BASE,",
        "gemini_a72_hotplug_ledger_owner_begin(",
        "WRITE_ONCE(hotplug_slot, slot);",
        "iounmap(slot);",
    ):
        require(token in begin, f"begin contract missing: {token}")
    for token in (
        "raw_spin_lock_irqsave(&gemini_a72_hotplug_ledger_checkpoint_lock,",
        "slot = READ_ONCE(hotplug_slot);",
        "gemini_a72_hotplug_ledger_owner_checkpoint(\n"
        "\t\t&hotplug_owner, &hotplug_mmio_ops, slot, session_id, record);",
        "raw_spin_unlock_irqrestore(&gemini_a72_hotplug_ledger_checkpoint_lock,",
        "The one-shot mapping remains pinned until the expected reset.",
    ):
        require(token in checkpoint, f"checkpoint contract missing: {token}")
    for token in ("mutex_lock", "mutex_unlock", "iounmap", "ioremap"):
        require(token not in checkpoint,
                f"sleeping or mapping operation in checkpoint: {token}")
    require(checkpoint.count("gemini_a72_hotplug_ledger_owner_checkpoint(") == 1,
            "owner checkpoint call count changed")
    require(text.count("EXPORT_SYMBOL_GPL(gemini_a72_hotplug_ledger_checkpoint);") == 1,
            "checkpoint export changed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    validate(args.source_root.resolve())
    print("ledger_checkpoint_context=pass")
    print("checkpoint_lock=raw-spin-irqsave")
    print("checkpoint_sleeping_calls=0")
    print("terminal_iounmap_calls=0")
    print("mapping_lifetime=one-shot-until-reset")


if __name__ == "__main__":
    main()
