#!/usr/bin/env python3
"""Apply the deterministic pre-init recovery companion to the exact parent."""

from __future__ import annotations

import argparse
from pathlib import Path


class EditError(RuntimeError):
    pass


KCONFIG_PARENT = '''config GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER
	bool "Gemini MT6797 read-only DVFSP provenance observer"
	depends on ARCH_MT6797 && DEBUG_FS
	default n
	help
	  Publish a bounded read-only debugfs record for the vendor EEM
	  calibration lifecycle and PPM table commit epoch.  This diagnostic
	  does not register a regulator provider, replace a setter, write
	  hardware, or admit CPUs.  Its zero owner and transition handles make
	  the missing coherent transition owner explicit.
'''

KCONFIG_CHILD = KCONFIG_PARENT + '''
config GEMINI_MT6797_DVFSP_PROVENANCE_PREINIT_RECOVERY
	bool "Gemini MT6797 provenance pre-init recovery companion"
	depends on GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER && PSTORE_CONSOLE
	default n
	help
	  Emit an attributable late-init checkpoint after the pstore console
	  is registered, then request one emergency restart after 120 seconds.
	  This experiment-only diagnostic does not access storage, change a
	  DVFSP or regulator state, alter CPU admission, or take watchdog
	  ownership away from the vendor kernel kicker.
'''

MAKEFILE_PARENT = (
    "obj-$(CONFIG_GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER) += "
    "mt6797-dvfsp-provenance-observer.o\n"
    "obj-y += mt_cpufreq_hybrid.o\n"
)

MAKEFILE_CHILD = (
    "obj-$(CONFIG_GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER) += "
    "mt6797-dvfsp-provenance-observer.o\n"
    "obj-$(CONFIG_GEMINI_MT6797_DVFSP_PROVENANCE_PREINIT_RECOVERY) += "
    "mt6797-dvfsp-provenance-preinit-recovery.o\n"
    "obj-y += mt_cpufreq_hybrid.o\n"
)

RECOVERY_SOURCE = r'''/*
 * SPDX-License-Identifier: GPL-2.0
 *
 * Pre-init retained checkpoint and bounded recovery for the Gemini
 * MT6797 provenance experiment.
 */
#include <linux/errno.h>
#include <linux/init.h>
#include <linux/jiffies.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/reboot.h>
#include <linux/workqueue.h>

#define GEMINI_MT6797_PREINIT_RECOVERY_MARKER \
	"GEMINI_DVFSP_PROVENANCE_PREINIT_RECOVERY_20260815"
#define GEMINI_MT6797_PREINIT_RECOVERY_SECONDS	120

static void gemini_mt6797_preinit_recovery_workfn(struct work_struct *work)
{
	(void)work;
	pr_emerg("%s recovery=executing reset=emergency-restart "
		  "storage_access=none dvfsp_hardware_write=none "
		  "cpu8_cpu9_admission=closed\n",
		 GEMINI_MT6797_PREINIT_RECOVERY_MARKER);
	emergency_restart();
}

static DECLARE_DELAYED_WORK(gemini_mt6797_preinit_recovery_work,
	gemini_mt6797_preinit_recovery_workfn);

static int __init gemini_mt6797_preinit_recovery_init(void)
{
	bool scheduled;

	scheduled = schedule_delayed_work(
		&gemini_mt6797_preinit_recovery_work,
		GEMINI_MT6797_PREINIT_RECOVERY_SECONDS * HZ);
	pr_emerg("%s checkpoint=pre-init recovery=%s deadline_seconds=%u "
		  "pstore_console=required storage_access=none "
		  "dvfsp_hardware_write=none cpu8_cpu9_admission=closed\n",
		 GEMINI_MT6797_PREINIT_RECOVERY_MARKER,
		 scheduled ? "armed" : "schedule-failed",
		 GEMINI_MT6797_PREINIT_RECOVERY_SECONDS);
	return scheduled ? 0 : -EBUSY;
}
late_initcall_sync(gemini_mt6797_preinit_recovery_init);

MODULE_DESCRIPTION("Gemini MT6797 provenance pre-init recovery companion");
MODULE_LICENSE("GPL");
'''


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise EditError(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def apply(source: Path) -> None:
    kconfig = source / "drivers/misc/mediatek/base/power/Kconfig"
    makefile = source / "drivers/misc/mediatek/base/power/mt6797/Makefile"
    recovery = (
        source
        / "drivers/misc/mediatek/base/power/mt6797/"
        "mt6797-dvfsp-provenance-preinit-recovery.c"
    )
    if not source.is_dir() or not kconfig.is_file() or not makefile.is_file():
        raise EditError("source is not the exact prepared vendor tree")
    if recovery.exists() or recovery.is_symlink():
        raise EditError("recovery companion path already exists")
    replace_once(kconfig, KCONFIG_PARENT, KCONFIG_CHILD)
    replace_once(makefile, MAKEFILE_PARENT, MAKEFILE_CHILD)
    recovery.write_text(RECOVERY_SOURCE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    apply(args.source.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EditError as exc:
        raise SystemExit(f"error: {exc}")
