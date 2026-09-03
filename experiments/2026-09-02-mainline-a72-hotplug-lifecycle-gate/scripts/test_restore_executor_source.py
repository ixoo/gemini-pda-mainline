#!/usr/bin/env python3
"""Require unsafe CPU9 restore-executor mutations to fail closed."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


FILES = {
    "header": "drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h",
    "source": "drivers/soc/mediatek/mt6797-a72-restore-executor.c",
    "test": "drivers/soc/mediatek/mt6797-a72-restore-executor-test.c",
    "kconfig": "drivers/soc/mediatek/Kconfig",
    "makefile": "drivers/soc/mediatek/Makefile",
}

MUTATIONS = (
    ("header", "RESTORE_CPU9 9U", "RESTORE_CPU9 8U"),
    ("header", "OFFLINE_MEMBERS BIT(0)", "OFFLINE_MEMBERS 0"),
    ("header", "ONLINE_MEMBERS (BIT(0) | BIT(1))", "ONLINE_MEMBERS BIT(0)"),
    ("header", "OFFLINE_SYSTEM_MASK GENMASK_ULL(8, 0)",
     "OFFLINE_SYSTEM_MASK GENMASK_ULL(7, 0)"),
    ("header", "ONLINE_SYSTEM_MASK GENMASK_ULL(9, 0)",
     "ONLINE_SYSTEM_MASK GENMASK_ULL(8, 0)"),
    ("header", "STAGE_PREPARED = 14", "STAGE_PREPARED = 13"),
    ("header", "STAGE_CPU_ON_COMMITTED = 15", "STAGE_CPU_ON_COMMITTED = 14"),
    ("header", "STAGE_SECONDARY_COMPLETE = 16", "STAGE_SECONDARY_COMPLETE = 15"),
    ("header", "STAGE_FULL_COMPLETE = 17", "STAGE_FULL_COMPLETE = 16"),
    ("header", "u64 controller_identity;", "u64 ignored_controller_identity;"),
    ("header", "bool watchdog_owned;", "bool watchdog_seen;"),
    ("source", "down_parent->completed == 1", "down_parent->completed <= 1"),
    ("source", "proof->cpu8_responsive == 1", "proof->cpu8_responsive <= 1"),
    ("source", "proof->shared_state_unchanged == 1",
     "proof->shared_state_unchanged <= 1"),
    ("source", "restore->identity.parent_generation ==",
     "restore->identity.parent_generation !="),
    ("source", "restore->identity.generation != down_parent->identity.generation",
     "restore->identity.generation == down_parent->identity.generation"),
    ("source", "restore->budgets.cpu_on == cpu_on",
     "restore->budgets.cpu_on != cpu_on"),
    ("source", "request->controller_identity && request->watchdog_identity &&\n"
     "\t\trequest->watchdog_owned",
     "request->controller_identity && request->watchdog_identity ||\n"
     "\t\trequest->watchdog_owned"),
    ("source", "atomic_cmpxchg(&controller->consumed, 0, 1)",
     "atomic_read(&controller->consumed)"),
    ("source", "ret = ops->cpu_boot(context, cpu);",
     "ret = ops->cpu_boot(context, cpu);\n\tops->cpu_boot(context, cpu);"),
    ("source",
     "\t\tMT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED, true);",
     "\t\tMT6797_A72_RESTORE_STAGE_VALIDATED, true);"),
    ("source",
     "\t\tMT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE, true);",
     "\t\tMT6797_A72_RESTORE_STAGE_VALIDATED, true);"),
    ("source", "members != MT6797_A72_RESTORE_ONLINE_MEMBERS",
     "members == MT6797_A72_RESTORE_ONLINE_MEMBERS"),
    ("source",
     "ret = ops->verify_terminal(context, &result->request,\n"
     "\t\t\t\t   &result->restore, members, online_mask,\n"
     "\t\t\t\t   system_online_mask);",
     "ret = 0; /* terminal verification removed */"),
    ("source", "*suppress_initial_rollback = true;",
     "*suppress_initial_rollback = false;"),
    ("source", "#include <linux/string.h>",
     "#include <linux/string.h>\n/* cpu_psci_ops.cpu_boot */"),
    ("test", "KUNIT_CASE(restore_executor_rollback_test),", ""),
    ("test", "KUNIT_CASE(restore_executor_secondary_order_test),", ""),
    ("test", "KUNIT_CASE(restore_executor_checkpoint_failure_test),", ""),
    ("kconfig", "\tdepends on ARM64_MT6797_A72_CPU9_MEMBERSHIP\n", ""),
    ("kconfig",
     "config MTK_MT6797_A72_RESTORE_EXECUTOR\n"
     "\tbool \"MediaTek MT6797 disconnected CPU9 restore executor\"\n"
     "\tdepends on ARM64 && ARCH_MEDIATEK\n"
     "\tdepends on ARM64_MT6797_A72_CPU9_MEMBERSHIP\n"
     "\tdepends on MTK_MT6797_A72_HOTPLUG_EXECUTOR\n"
     "\tdefault n\n",
     "config MTK_MT6797_A72_RESTORE_EXECUTOR\n"
     "\tbool \"MediaTek MT6797 disconnected CPU9 restore executor\"\n"
     "\tdepends on ARM64 && ARCH_MEDIATEK\n"
     "\tdepends on ARM64_MT6797_A72_CPU9_MEMBERSHIP\n"
     "\tdepends on MTK_MT6797_A72_HOTPLUG_EXECUTOR\n"
     "\tdefault y\n"),
    ("makefile", "mt6797-a72-restore-executor-test.o",
     "mt6797-a72-restore-executor.o"),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validator = Path(__file__).resolve().parent / "validate_restore_executor_source.py"
    rejected = 0
    for index, (label, old, new) in enumerate(MUTATIONS, start=1):
        with tempfile.TemporaryDirectory(
            prefix=f"restore-executor-mutation-{index}-"
        ) as name:
            root = Path(name)
            for relative in FILES.values():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, target)
            path = root / FILES[label]
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                raise SystemExit(f"mutation anchor changed: {index}:{label}:{old}")
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            completed = subprocess.run(
                ["python3", str(validator), "--source-root", str(root),
                 "--require-tests"],
                check=False, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if completed.returncode == 0:
                raise SystemExit(f"unsafe mutation accepted: {index}:{label}")
            rejected += 1
    print("restore_executor_mutations=pass")
    print(f"unsafe_mutations_rejected={rejected}")


if __name__ == "__main__":
    main()
