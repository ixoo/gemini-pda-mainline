#!/usr/bin/env python3
"""Make the record-4 checkpoint path safe in the CPU-die context."""

from __future__ import annotations

import argparse
from pathlib import Path


LEDGER = "fs/pstore/gemini_a72_hotplug_ledger.c"

OLD_INCLUDES = """#include <linux/of_address.h>
#include <linux/string.h>
"""

NEW_INCLUDES = """#include <linux/of_address.h>
#include <linux/spinlock.h>
#include <linux/string.h>
"""

OLD_PRODUCTION = """static DEFINE_MUTEX(gemini_a72_hotplug_ledger_lock);
static struct gemini_a72_hotplug_ledger_owner hotplug_owner;
static void __iomem *hotplug_slot;
static bool hotplug_attempted;

int gemini_a72_hotplug_ledger_begin(u64 session_id)
{
	int ret;

	mutex_lock(&gemini_a72_hotplug_ledger_lock);
	if (hotplug_attempted) {
		ret = -EALREADY;
		goto out_unlock;
	}
	hotplug_attempted = true;
	if (!gemini_a72_hotplug_ledger_exact_dt()) {
		ret = -ENODEV;
		goto out_unlock;
	}
	hotplug_slot = ioremap_wc(GEMINI_A72_HOTPLUG_LEDGER_BASE,
				  GEMINI_A72_HOTPLUG_LEDGER_SLOT_SIZE);
	if (!hotplug_slot) {
		ret = -ENOMEM;
		goto out_unlock;
	}
	ret = gemini_a72_hotplug_ledger_owner_begin(
		&hotplug_owner, &hotplug_mmio_ops, hotplug_slot, session_id);
	if (ret) {
		iounmap(hotplug_slot);
		hotplug_slot = NULL;
	}
out_unlock:
	mutex_unlock(&gemini_a72_hotplug_ledger_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_a72_hotplug_ledger_begin);

int gemini_a72_hotplug_ledger_checkpoint(
	u64 session_id,
	const struct gemini_a72_hotplug_ledger_record *record)
{
	int ret;

	mutex_lock(&gemini_a72_hotplug_ledger_lock);
	if (!hotplug_slot) {
		ret = -EPERM;
		goto out_unlock;
	}
	ret = gemini_a72_hotplug_ledger_owner_checkpoint(
		&hotplug_owner, &hotplug_mmio_ops, hotplug_slot,
		session_id, record);
	if (ret || (record && record->terminal)) {
		iounmap(hotplug_slot);
		hotplug_slot = NULL;
	}
out_unlock:
	mutex_unlock(&gemini_a72_hotplug_ledger_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_a72_hotplug_ledger_checkpoint);
"""

NEW_PRODUCTION = """static DEFINE_MUTEX(gemini_a72_hotplug_ledger_begin_lock);
static DEFINE_RAW_SPINLOCK(gemini_a72_hotplug_ledger_checkpoint_lock);
static struct gemini_a72_hotplug_ledger_owner hotplug_owner;
static void __iomem *hotplug_slot;
static bool hotplug_attempted;

int gemini_a72_hotplug_ledger_begin(u64 session_id)
{
	void __iomem *slot;
	int ret;

	mutex_lock(&gemini_a72_hotplug_ledger_begin_lock);
	if (hotplug_attempted) {
		ret = -EALREADY;
		goto out_unlock;
	}
	hotplug_attempted = true;
	if (!gemini_a72_hotplug_ledger_exact_dt()) {
		ret = -ENODEV;
		goto out_unlock;
	}
	slot = ioremap_wc(GEMINI_A72_HOTPLUG_LEDGER_BASE,
			 GEMINI_A72_HOTPLUG_LEDGER_SLOT_SIZE);
	if (!slot) {
		ret = -ENOMEM;
		goto out_unlock;
	}
	ret = gemini_a72_hotplug_ledger_owner_begin(
		&hotplug_owner, &hotplug_mmio_ops, slot, session_id);
	if (ret)
		iounmap(slot);
	else
		WRITE_ONCE(hotplug_slot, slot);
out_unlock:
	mutex_unlock(&gemini_a72_hotplug_ledger_begin_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_a72_hotplug_ledger_begin);

int gemini_a72_hotplug_ledger_checkpoint(
	u64 session_id,
	const struct gemini_a72_hotplug_ledger_record *record)
{
	unsigned long flags;
	void __iomem *slot;
	int ret;

	raw_spin_lock_irqsave(&gemini_a72_hotplug_ledger_checkpoint_lock,
			      flags);
	slot = READ_ONCE(hotplug_slot);
	if (!slot) {
		ret = -EPERM;
		goto out_unlock;
	}
	ret = gemini_a72_hotplug_ledger_owner_checkpoint(
		&hotplug_owner, &hotplug_mmio_ops, slot, session_id, record);
out_unlock:
	raw_spin_unlock_irqrestore(&gemini_a72_hotplug_ledger_checkpoint_lock,
				   flags);
	/* The one-shot mapping remains pinned until the expected reset. */
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_a72_hotplug_ledger_checkpoint);
"""


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"source anchor changed: {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    path = root / LEDGER
    replace_once(path, OLD_INCLUDES, NEW_INCLUDES)
    replace_once(path, OLD_PRODUCTION, NEW_PRODUCTION)


if __name__ == "__main__":
    main()
