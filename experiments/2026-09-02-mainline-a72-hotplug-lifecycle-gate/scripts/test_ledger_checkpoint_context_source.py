#!/usr/bin/env python3
"""Reject context-unsafe mutations of the record-4 checkpoint path."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_ledger_checkpoint_context_source.py"
LEDGER = "fs/pstore/gemini_a72_hotplug_ledger.c"

MUTATIONS = (
    ("#include <linux/spinlock.h>\n", ""),
    ("DEFINE_RAW_SPINLOCK(gemini_a72_hotplug_ledger_checkpoint_lock)",
     "DEFINE_MUTEX(gemini_a72_hotplug_ledger_checkpoint_lock)"),
    ("raw_spin_lock_irqsave(&gemini_a72_hotplug_ledger_checkpoint_lock,",
     "mutex_lock(&gemini_a72_hotplug_ledger_checkpoint_lock); /*"),
    ("raw_spin_unlock_irqrestore(&gemini_a72_hotplug_ledger_checkpoint_lock,",
     "mutex_unlock(&gemini_a72_hotplug_ledger_checkpoint_lock); /*"),
    ("slot = READ_ONCE(hotplug_slot);", "slot = hotplug_slot;"),
    ("WRITE_ONCE(hotplug_slot, slot);", "hotplug_slot = slot;"),
    ("gemini_a72_hotplug_ledger_owner_checkpoint(\n\t\t&hotplug_owner,",
     "gemini_a72_hotplug_ledger_owner_checkpoint(\n\t\tNULL,"),
    ("/* The one-shot mapping remains pinned until the expected reset. */",
     "iounmap(slot);"),
    ("mutex_lock(&gemini_a72_hotplug_ledger_begin_lock);", ""),
    ("gemini_a72_hotplug_ledger_exact_dt()", "true"),
)


def load_validator():
    spec = importlib.util.spec_from_file_location("ledger_context", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("validator import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validator = load_validator()
    validator.validate(source)
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="ledger-context-mutations-") as name:
        base = Path(name) / "base"
        target = base / LEDGER
        target.parent.mkdir(parents=True)
        shutil.copyfile(source / LEDGER, target)
        for index, (old, new) in enumerate(MUTATIONS):
            candidate = Path(name) / f"mutation-{index}"
            shutil.copytree(base, candidate)
            path = candidate / LEDGER
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                raise AssertionError(f"mutation anchor changed: {index}")
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            try:
                validator.validate(candidate)
            except ValueError:
                rejected += 1
            else:
                raise AssertionError(f"unsafe mutation accepted: {index}")
    print("ledger_checkpoint_context_mutations=pass")
    print(f"unsafe_mutations_rejected={rejected}")


if __name__ == "__main__":
    main()
