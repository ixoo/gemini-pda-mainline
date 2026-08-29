#!/usr/bin/env python3
"""Apply the exact same-version Gemian pmsg witness child."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


PARENT_SHA256 = {
    "arch/arm64/kernel/psci.c":
        "144ef9dda2ecee098ac285a7f3189a84401eccf39bc8da67f15cfc98da1d1bcc",
    "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c":
        "403c0bd179204c669f8733b71779b7f95d271eb415c1b7b0212f598e9c91ff79",
    "fs/pstore/pmsg.c":
        "d068bcef6caea7674bde8a900f5c0a774f6c8a71ab981075d1a12d0b8d9dd7e0",
    "include/linux/pstore.h":
        "7c3aa62a100652d4abc5abb34573a805f00a2bfb1f88fd0bec60a6a25195dd28",
}

ENTRY_RECORD = (
    "gemini-a72-pmsg-v1 stage=entry parent=register-capsule\\n"
)
PRE_SCHEDULER_RECORD = (
    "gemini-a72-pmsg-v1 stage=pre-scheduler parent=pair-v6-pass\\n"
)
TERMINAL_PASS_RECORD = (
    "gemini-a72-pmsg-v1 stage=pre-capsule result=pass\\n"
)
TERMINAL_FAULT_RECORD = (
    "gemini-a72-pmsg-v1 stage=pre-capsule result=fault\\n"
)

PMSG_INCLUDES_PARENT = """#include <linux/uaccess.h>
#include <linux/vmalloc.h>
"""
PMSG_INCLUDES_CHILD = """#include <linux/module.h>
#include <linux/string.h>
#include <linux/uaccess.h>
#include <linux/vmalloc.h>
"""
PMSG_HELPER_ANCHOR = """static DEFINE_MUTEX(pmsg_lock);
#define PMSG_MAX_BOUNCE_BUFFER_SIZE (1*PAGE_SIZE)

"""
PMSG_HELPER_BLOCK = """static DEFINE_MUTEX(pmsg_lock);
#define PMSG_MAX_BOUNCE_BUFFER_SIZE (1*PAGE_SIZE)
#define PMSG_MAX_KERNEL_RECORD_SIZE 256

int pstore_write_pmsg_kernel(const char *buf, size_t count)
{
	u64 id = 0;
	int ret = -ENODEV;

	if (!buf || !count || count > PMSG_MAX_KERNEL_RECORD_SIZE)
		return -EINVAL;

	mutex_lock(&pmsg_lock);
	if (psinfo && psinfo->write_buf && psinfo->name &&
	    !strcmp(psinfo->name, "ramoops"))
		ret = psinfo->write_buf(PSTORE_TYPE_PMSG, 0, &id, 0, buf, 0,
					count, psinfo);
	mutex_unlock(&pmsg_lock);

	return ret;
}
EXPORT_SYMBOL_GPL(pstore_write_pmsg_kernel);

"""

PSTORE_DECL_ANCHOR = """#ifdef CONFIG_PSTORE
extern int pstore_register(struct pstore_info *);
"""
PSTORE_DECL_CHILD = """#ifdef CONFIG_PSTORE_PMSG
int pstore_write_pmsg_kernel(const char *buf, size_t count);
#else
static inline int pstore_write_pmsg_kernel(const char *buf, size_t count)
{
	return -ENODEV;
}
#endif

#ifdef CONFIG_PSTORE
extern int pstore_register(struct pstore_info *);
"""

OBSERVER_INCLUDE_PARENT = """#include <linux/proc_fs.h>
#include <linux/seq_file.h>
"""
OBSERVER_INCLUDE_CHILD = """#include <linux/proc_fs.h>
#include <linux/pstore.h>
#include <linux/seq_file.h>
"""
OBSERVER_DEFINE_PARENT = """#define MT6797_A72_OBS_PROC_NAME\t"mt6797_a72_transition"

"""
OBSERVER_DEFINE_CHILD = f"""#define MT6797_A72_OBS_PROC_NAME\t"mt6797_a72_transition"

static const char mt6797_a72_pmsg_entry[] =
\t"{ENTRY_RECORD}";

"""
OBSERVER_INIT_PARENT = """static int __init mt6797_a72_obs_init(void)
{
	if (!proc_create(MT6797_A72_OBS_PROC_NAME, 0400, NULL,
"""
OBSERVER_INIT_CHILD = """static int __init mt6797_a72_obs_init(void)
{
	(void)pstore_write_pmsg_kernel(mt6797_a72_pmsg_entry,
				       sizeof(mt6797_a72_pmsg_entry) - 1);
	if (!proc_create(MT6797_A72_OBS_PROC_NAME, 0400, NULL,
"""

PSCI_INCLUDE_PARENT = """#include <linux/spinlock.h>
#include <uapi/linux/psci.h>
"""
PSCI_INCLUDE_CHILD = """#include <linux/pstore.h>
#include <linux/spinlock.h>
#include <uapi/linux/psci.h>
"""
PSCI_DEFINE_PARENT = """#define MT6797_A72_SC_HASH8_EXPECTED 0xf678147669874ecdULL
#define MT6797_A72_SC_HASH9_EXPECTED 0xc2274327e9c8104cULL

"""
PSCI_DEFINE_CHILD = f"""#define MT6797_A72_SC_HASH8_EXPECTED 0xf678147669874ecdULL
#define MT6797_A72_SC_HASH9_EXPECTED 0xc2274327e9c8104cULL

static const char mt6797_a72_pmsg_pre_scheduler[] =
\t"{PRE_SCHEDULER_RECORD}";
static const char mt6797_a72_pmsg_terminal_pass[] =
\t"{TERMINAL_PASS_RECORD}";
static const char mt6797_a72_pmsg_terminal_fault[] =
\t"{TERMINAL_FAULT_RECORD}";

"""
PSCI_PRE_SCHEDULER_PARENT = "\t\tmt6797_a72_sc_run();\n"
PSCI_PRE_SCHEDULER_CHILD = """		(void)pstore_write_pmsg_kernel(mt6797_a72_pmsg_pre_scheduler,
			sizeof(mt6797_a72_pmsg_pre_scheduler) - 1);
		mt6797_a72_sc_run();
"""
PSCI_TERMINAL_PARENT = """	pr_emerg("gemini-a72-pair-v7 result=%s parent_pass=%d sc_reported=%d sc_iterations=262144 sc_rescheds=64 sc_expected8=%d sc_start8=%d sc_end8=%d sc_expected9=%d sc_start9=%d sc_end9=%d sc_task8=%d sc_task9=%d sc_create8=%d sc_create9=%d sc_unpark8=%d sc_unpark9=%d sc_readywait8=%d sc_readywait9=%d sc_startwait8=%d sc_startwait9=%d sc_wait8=%d sc_wait9=%d sc_error8=%d sc_error9=%d sc_stop8=%d sc_stop9=%d sc_done8=%d sc_done9=%d sc_ready=%d sc_finished=%d sc_hash8=%016llx sc_hash9=%016llx\\n",
"""
PSCI_TERMINAL_CHILD = """	(void)pstore_write_pmsg_kernel(passed ?
		mt6797_a72_pmsg_terminal_pass :
		mt6797_a72_pmsg_terminal_fault,
		passed ? sizeof(mt6797_a72_pmsg_terminal_pass) - 1 :
			 sizeof(mt6797_a72_pmsg_terminal_fault) - 1);
	pr_emerg("gemini-a72-pair-v7 result=%s parent_pass=%d sc_reported=%d sc_iterations=262144 sc_rescheds=64 sc_expected8=%d sc_start8=%d sc_end8=%d sc_expected9=%d sc_start9=%d sc_end9=%d sc_task8=%d sc_task9=%d sc_create8=%d sc_create9=%d sc_unpark8=%d sc_unpark9=%d sc_readywait8=%d sc_readywait9=%d sc_startwait8=%d sc_startwait9=%d sc_wait8=%d sc_wait9=%d sc_error8=%d sc_error9=%d sc_stop8=%d sc_stop9=%d sc_done8=%d sc_done9=%d sc_ready=%d sc_finished=%d sc_hash8=%016llx sc_hash9=%016llx\\n",
"""


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {text.count(old)}")
    return text.replace(old, new, 1)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def transform_mapping(
    parents: dict[str, str], *, verify_hashes: bool = True
) -> dict[str, str]:
    if set(parents) != set(PARENT_SHA256):
        raise RuntimeError("parent path inventory changed")
    if verify_hashes:
        for path, expected in PARENT_SHA256.items():
            actual = sha256_text(parents[path])
            if actual != expected:
                raise RuntimeError(f"parent hash changed: {path}: {actual}")

    children = dict(parents)
    path = "fs/pstore/pmsg.c"
    text = replace_once(children[path], PMSG_INCLUDES_PARENT,
                        PMSG_INCLUDES_CHILD, "pmsg includes")
    children[path] = replace_once(text, PMSG_HELPER_ANCHOR,
                                  PMSG_HELPER_BLOCK, "pmsg helper")

    path = "include/linux/pstore.h"
    children[path] = replace_once(children[path], PSTORE_DECL_ANCHOR,
                                  PSTORE_DECL_CHILD, "pstore declaration")

    path = "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c"
    text = replace_once(children[path], OBSERVER_INCLUDE_PARENT,
                        OBSERVER_INCLUDE_CHILD, "observer include")
    text = replace_once(text, OBSERVER_DEFINE_PARENT,
                        OBSERVER_DEFINE_CHILD, "observer record")
    children[path] = replace_once(text, OBSERVER_INIT_PARENT,
                                  OBSERVER_INIT_CHILD, "observer call")

    path = "arch/arm64/kernel/psci.c"
    text = replace_once(children[path], PSCI_INCLUDE_PARENT,
                        PSCI_INCLUDE_CHILD, "psci include")
    text = replace_once(text, PSCI_DEFINE_PARENT,
                        PSCI_DEFINE_CHILD, "psci records")
    text = replace_once(text, PSCI_PRE_SCHEDULER_PARENT,
                        PSCI_PRE_SCHEDULER_CHILD, "pre-scheduler call")
    children[path] = replace_once(text, PSCI_TERMINAL_PARENT,
                                  PSCI_TERMINAL_CHILD, "terminal call")
    return children


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    parents = {
        path: (args.source / path).read_text(encoding="utf-8")
        for path in PARENT_SHA256
    }
    children = transform_mapping(parents)
    for path, text in children.items():
        (args.source / path).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
