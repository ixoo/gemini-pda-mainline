#!/usr/bin/env python3
"""Apply the deterministic Gemini protected-readback call-ledger change."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


LEDGER_SOURCE = dedent(r"""
// SPDX-License-Identifier: GPL-2.0-only
/* Experiment-only retained ledger around the first protected readback. */

#include <linux/io.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/pstore_ram.h>
#include <linux/string.h>

#define GEMINI_PRB_RESERVE_BASE		0x44410000ULL
#define GEMINI_PRB_RESERVE_SIZE		0x000e0000ULL
#define GEMINI_PRB_LEDGER_BASE		0x444bb000ULL
#define GEMINI_PRB_SLOT_SIZE		0x00001000UL
#define GEMINI_PRB_SLOT_COUNT		4
#define GEMINI_PRB_FIRST_OWNED_SLOT	2
#define GEMINI_PRB_HEADER_SIZE		12
#define GEMINI_PRB_SIGNATURE		0x43474244

static bool gemini_prb_armed;

static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A "
	"checkpoint=before-clock slot=173 crc32=08f2fe56\n",
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A "
	"checkpoint=after-clock slot=174 crc32=e477a18e\n",
};

static bool gemini_prb_slot_empty(void __iomem *slot)
{
	return readl(slot) == GEMINI_PRB_SIGNATURE &&
	       readl((u8 __iomem *)slot + 4) == 0 &&
	       readl((u8 __iomem *)slot + 8) == 0;
}

static bool gemini_prb_slot_exact(void __iomem *slot, const char *record)
{
	size_t len = strlen(record);
	size_t i;

	if (readl(slot) != GEMINI_PRB_SIGNATURE ||
	    readl((u8 __iomem *)slot + 4) != len ||
	    readl((u8 __iomem *)slot + 8) != len)
		return false;
	for (i = 0; i < len; i++)
		if (readb((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE + i) !=
		    record[i])
			return false;

	return true;
}

static bool gemini_prb_write(void __iomem *slot, const char *record)
{
	size_t len = strlen(record);
	size_t i;

	if (!gemini_prb_slot_empty(slot) ||
	    len > GEMINI_PRB_SLOT_SIZE - GEMINI_PRB_HEADER_SIZE)
		return false;

	memcpy_toio((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE, record, len);
	wmb(); /* Commit payload before producer metadata. */
	writel(len, (u8 __iomem *)slot + 4);
	wmb(); /* Commit start before the final size field. */
	writel(len, (u8 __iomem *)slot + 8);
	mb(); /* Order the complete local readback after the commit. */

	if (readl(slot) != GEMINI_PRB_SIGNATURE ||
	    readl((u8 __iomem *)slot + 4) != len ||
	    readl((u8 __iomem *)slot + 8) != len)
		return false;
	for (i = 0; i < len; i++)
		if (readb((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE + i) !=
		    record[i])
			return false;

	return true;
}

static bool gemini_prb_exact_dt(void)
{
	struct device_node *node;
	struct resource resource;
	const char *model;
	u32 value;
	bool exact = false;

	if (!of_machine_is_compatible("planet,gemini-pda") ||
	    of_property_read_string(of_root, "model", &model) ||
	    strcmp(model, "MT6797X"))
		return false;

	node = of_find_node_by_path("/reserved-memory/ramoops@44410000");
	if (!node)
		return false;
	if (!of_device_is_compatible(node, "ramoops") ||
	    of_address_to_resource(node, 0, &resource) ||
	    resource.start != GEMINI_PRB_RESERVE_BASE ||
	    resource_size(&resource) != GEMINI_PRB_RESERVE_SIZE ||
	    !of_property_read_bool(node, "no-map"))
		goto out;

	if (of_property_read_u32(node, "record-size", &value) ||
	    value != 0x1000)
		goto out;
	if (of_property_read_u32(node, "console-size", &value) ||
	    value != 0x10000)
		goto out;
	if (of_property_read_u32(node, "ftrace-size", &value) ||
	    value != 0x1000)
		goto out;
	if (of_property_read_u32(node, "pmsg-size", &value) ||
	    value != 0x20000)
		goto out;
	if (of_property_read_u32(node, "mem-type", &value) || value)
		goto out;
	exact = true;
out:
	of_node_put(node);
	return exact;
}

static bool gemini_prb_prefix_valid(void __iomem *ledger,
				    unsigned int checkpoint)
{
	unsigned int i;

	for (i = 0; i < GEMINI_PRB_SLOT_COUNT; i++) {
		void __iomem *slot = (u8 __iomem *)ledger +
				       i * GEMINI_PRB_SLOT_SIZE;

		if (checkpoint == 1 && i == GEMINI_PRB_FIRST_OWNED_SLOT) {
			if (!gemini_prb_slot_exact(slot, gemini_prb_records[0]))
				return false;
		} else if (!gemini_prb_slot_empty(slot)) {
			return false;
		}
	}

	return true;
}

bool gemini_protected_readback_ledger_checkpoint(unsigned int checkpoint)
{
	void __iomem *ledger;
	void __iomem *slot;
	bool written = false;

	if (checkpoint > 1 || (checkpoint == 0 && gemini_prb_armed) ||
	    (checkpoint == 1 && !gemini_prb_armed) || !gemini_prb_exact_dt())
		return false;

	ledger = ioremap_wc(GEMINI_PRB_LEDGER_BASE,
			    GEMINI_PRB_SLOT_COUNT * GEMINI_PRB_SLOT_SIZE);
	if (!ledger)
		return false;
	if (!gemini_prb_prefix_valid(ledger, checkpoint))
		goto out;

	slot = (u8 __iomem *)ledger +
	       (GEMINI_PRB_FIRST_OWNED_SLOT + checkpoint) *
	       GEMINI_PRB_SLOT_SIZE;
	written = gemini_prb_write(slot, gemini_prb_records[checkpoint]);
out:
	iounmap(ledger);
	if (checkpoint == 0 && written)
		gemini_prb_armed = true;
	else if (checkpoint == 1)
		gemini_prb_armed = false;

	return written;
}
""").lstrip("\n")


def apply(root: Path) -> None:
    source = root / "fs/pstore/gemini_protected_readback_ledger.c"
    if source.exists():
        raise SystemExit("protected-readback ledger source already exists")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(LEDGER_SOURCE, encoding="utf-8")

    kconfig = root / "fs/pstore/Kconfig"
    config = dedent(r"""
config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER
	bool "Gemini protected-readback retained call ledger"
	depends on PSTORE_RAM=y
	depends on ARM64 && ARCH_MEDIATEK && OF
	depends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y
	depends on !PSTORE_GEMINI_PRE_RAMOOPS_LEDGER
	depends on !PSTORE_GEMINI_ARM64_ENTRY_LEDGER
	default n
	help
	  Write at most two short records into exact otherwise-unused dmesg
	  zones in the existing Gemini ramoops reservation. The records bracket
	  the first protected-clock read in the one-shot readback observer.

	  The writer requires the exact candidate model, complete DT reservation
	  contract, and valid empty persistent-RAM headers before its first write.
	  It writes payload before metadata, fully reads back every record, never
	  retries or clears, and stops the observer before the next protected read
	  on any mismatch. Normal ramoops registration is skipped only for this
	  isolated option so known-good Gemian can recover the records.

	  This experiment-only option performs no storage, firmware, regulator,
	  clock, CPU, timer, watchdog, reset, or power operation. If unsure, say N.

""").lstrip("\n")
    anchor = "config PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT\n"
    replace_once(kconfig, anchor, config + anchor)

    makefile = root / "fs/pstore/Makefile"
    anchor = (
        "obj-$(CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER) += "
        "gemini_entry_ledger.o\n"
    )
    addition = (
        "obj-$(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER) += "
        "gemini_protected_readback_ledger.o\n"
    )
    replace_once(makefile, anchor, anchor + addition)

    ram = root / "fs/pstore/ram.c"
    anchor = dedent(r"""
#ifdef CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER
	if (of_machine_is_compatible("planet,gemini-pda"))
		return 0;
#endif
	ramoops_register_dummy();
""").lstrip("\n")
    replacement = dedent(r"""
#ifdef CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER
	if (of_machine_is_compatible("planet,gemini-pda"))
		return 0;
#endif
#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER
	if (of_machine_is_compatible("planet,gemini-pda"))
		return 0;
#endif
	ramoops_register_dummy();
""").lstrip("\n")
    replace_once(ram, anchor, replacement)

    header = root / "include/linux/pstore_ram.h"
    anchor = dedent(r"""
#ifdef CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER
void gemini_arm64_entry_ledger_post_mmu_checkpoint(void);
void gemini_arm64_entry_ledger_post_reserved_checkpoint(void);
#else
static inline void gemini_arm64_entry_ledger_post_mmu_checkpoint(void) { }
static inline void gemini_arm64_entry_ledger_post_reserved_checkpoint(void)
{
}
#endif

#endif
""").lstrip("\n")
    addition = dedent(r"""
#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER
bool gemini_protected_readback_ledger_checkpoint(unsigned int checkpoint);
#else
static inline bool
gemini_protected_readback_ledger_checkpoint(unsigned int checkpoint)
{
	return true;
}
#endif
""").lstrip("\n")
    replace_once(
        header,
        anchor,
        anchor.removesuffix("\n#endif\n") + "\n" + addition + "\n#endif\n",
    )

    observer = root / (
        "drivers/soc/mediatek/mt6797-protected-readback-observer.c"
    )
    replace_once(
        observer,
        "#include <linux/err.h>\n",
        "#include <linux/err.h>\n#include <linux/errno.h>\n",
    )
    replace_once(
        observer,
        "#include <linux/platform_device.h>\n",
        "#include <linux/platform_device.h>\n#include <linux/pstore_ram.h>\n",
    )
    old = (
        "\tclock_ret = mt6797_dvfsp_clock_backend_read(&clock_backend->dev,\n"
        "\t\t\t\t\t\t    &clock);\n"
        "\tbigidvfs_ret = "
        "mt6797_bigidvfs_backend_read(&bigidvfs_backend->dev,\n"
        "\t\t\t\t\t\t    &bigidvfs);\n"
    )
    new = (
        "\tif (!gemini_protected_readback_ledger_checkpoint(0)) {\n"
        "\t\tret = dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t    \"before-clock ledger checkpoint failed\\n\");\n"
        "\t\tgoto put_bigidvfs;\n"
        "\t}\n"
        "\tclock_ret = mt6797_dvfsp_clock_backend_read(&clock_backend->dev,\n"
        "\t\t\t\t\t\t    &clock);\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(1)) {\n"
        "\t\tret = dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t    \"after-clock ledger checkpoint failed\\n\");\n"
        "\t\tgoto put_bigidvfs;\n"
        "\t}\n"
        "\tbigidvfs_ret = "
        "mt6797_bigidvfs_backend_read(&bigidvfs_backend->dev,\n"
        "\t\t\t\t\t\t    &bigidvfs);\n"
    )
    replace_once(observer, old, new)
    replace_once(
        observer,
        "\tput_device(&bigidvfs_backend->dev);\n\tret = 0;\n\nput_clock:\n",
        "\tret = 0;\n\nput_bigidvfs:\n"
        "\tput_device(&bigidvfs_backend->dev);\n"
        "put_clock:\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root.resolve())


if __name__ == "__main__":
    main()
