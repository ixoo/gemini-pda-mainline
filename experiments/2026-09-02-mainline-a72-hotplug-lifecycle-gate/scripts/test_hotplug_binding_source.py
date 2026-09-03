#!/usr/bin/env python3
"""Require the CPU9 hotplug binding validator to reject unsafe mutations."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile

from validate_hotplug_binding_source import validate


SOURCE = "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c"
INTERNAL = "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h"
PUBLIC = "include/linux/soc/mediatek/mt6797-a72-hotplug-binding.h"
PSCI = "arch/arm64/kernel/mt6797_psci.c"
ADMISSION = "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
KCONFIG = "drivers/soc/mediatek/Kconfig"
MAKEFILE = "drivers/soc/mediatek/Makefile"
TEST = "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c"

MUTATIONS = (
    (INTERNAL, "MT6797_A72_HOTPLUG_BINDING_CPU9 9U",
     "MT6797_A72_HOTPLUG_BINDING_CPU9 8U"),
    (SOURCE, "cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 && route == expected",
     "route == expected"),
    (SOURCE, "ops->task_identity(context) != expected_task ||\n\t    ", ""),
    (SOURCE, "!ops->cpu_online(context, cpu) ||\n\t    ", ""),
    (SOURCE, "!dev->offline_disabled", "dev->offline_disabled"),
    (SOURCE, "dev->offline)", "!dev->offline)"),
    (SOURCE, "dev->offline_disabled = false;",
     "dev->offline_disabled = true;"),
    (SOURCE, "dev->offline_disabled = true;\nout_unlock:",
     "out_unlock:"),
    (SOURCE, "ops->lock(context);", ""),
    (SOURCE, "ops->unlock(context);", ""),
    (SOURCE, "ret = ops->offline(context, dev);",
     "ret = 0;"),
    (SOURCE, "ret = add_cpu(cpu);", "ret = 0;"),
    (SOURCE, "binding->next_stage = GEMINI_A72_HOTPLUG_AFFINITY_OFF;",
     "binding->next_stage++;"),
    (SOURCE, "GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED;",
     "GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED;"),
    (SOURCE, "mt6797_a72_binder_parent_proof(proof)", "0"),
    (SOURCE, "mt6797_a72_cpu8_observer_run(\n",
     "mt6797_a72_cpu8_observer_run_with_ops(\n"),
    (SOURCE, "mt6797_a72_hotplug_commit_off(cpu)", "0"),
    (SOURCE, "mt6797_a72_hotplug_complete_restore(restore, cpu8_online,",
     "0 && mt6797_a72_hotplug_complete_restore(restore, cpu8_online,"),
    (PSCI, "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
     "{\n\treturn false;\n}",
     "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
     "{\n\treturn cpu == 9;\n}"),
    (PSCI, "psci_ops.affinity_info(cpu_logical_map(cpu), level)",
     "cpu_psci_ops.cpu_kill(cpu)"),
    (PSCI, "if (mt6797_a72_hotplug_binding_down_commit(cpu))",
     "if (false)"),
    (PSCI, ".cpu_down_validate = mt6797_psci_cpu_down_validate,\n", ""),
    (PSCI, "mt6797_a72_hotplug_binding_restore_rollback(",
     "mt6797_a72_cpu9_binder_failure("),
    (ADMISSION,
     "if (ret || !IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING))",
     "if (!IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING))"),
    (ADMISSION, "controller->cpu9.cpu9_transaction.identity.generation",
     "1"),
    (KCONFIG, "\tdefault n\n\thelp\n\t  Bind the proven one-task CPU9",
     "\tdefault y\n\thelp\n\t  Bind the proven one-task CPU9"),
    (MAKEFILE,
     "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING) += "
     "mt6797-a72-hotplug-binding.o\n", ""),
    (TEST, "state->saw_private_gate = !dev->offline_disabled;",
     "state->saw_private_gate = true;"),
)

COPY_PATHS = tuple(sorted({item[0] for item in MUTATIONS} | {PUBLIC}))


def mutate(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise ValueError(
            f"mutation anchor count changed for {relative}: {old!r}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validate(source, True)

    rejected = 0
    for relative, old, new in MUTATIONS:
        with tempfile.TemporaryDirectory(
            prefix="mt6797-a72-hotplug-binding-mutation-"
        ) as name:
            root = Path(name)
            for copy_relative in COPY_PATHS:
                destination = root / copy_relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / copy_relative, destination)
            mutate(root, relative, old, new)
            try:
                validate(root, True)
            except ValueError:
                rejected += 1
            else:
                raise SystemExit(f"unsafe mutation accepted: {relative}: {old}")

    print("hotplug_binding_mutations=pass")
    print(f"unsafe_mutations_rejected={rejected}")


if __name__ == "__main__":
    main()
