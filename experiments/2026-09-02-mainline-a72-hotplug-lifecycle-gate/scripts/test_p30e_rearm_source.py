#!/usr/bin/env python3
"""Mutation tripwires for the CPU9 P30E rearm implementation."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile

from validate_p30e_rearm_source import validate


P30E = "arch/arm64/kernel/mt6797_a72_p30e.c"
P30E_HEADER = "arch/arm64/include/asm/mt6797_a72_p30e.h"
EXECUTOR = "drivers/soc/mediatek/mt6797-a72-restore-executor.c"
EXECUTOR_HEADER = "drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h"
BINDING = "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c"
BINDING_HEADER = "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h"
LEDGER_HEADER = "include/linux/gemini_a72_hotplug_ledger.h"
LEDGER_INTERNAL = "fs/pstore/gemini_a72_hotplug_ledger_internal.h"

PRIMITIVE_MUTATIONS = (
    (P30E, "P30E_MAGIC_WORD) !=\n\t\t    ARM64_MT6797_A72_P30E_MAGIC ||",
     "P30E_MAGIC_WORD) ==\n\t\t    ARM64_MT6797_A72_P30E_MAGIC ||"),
    (P30E, "ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP ||",
     "ARM64_MT6797_A72_P30E_OPERATION_CPU8_UP ||"),
    (P30E, "generation == ~0ULL", "generation == 0ULL"),
    (P30E, "cookie == ~0ULL", "cookie == 0ULL"),
    (P30E, "P30E_TARGET_STATE_WORD) !=\n"
     "\t\t    ARM64_MT6797_A72_P30E_TARGET_PUBLISHED ||",
     "P30E_TARGET_STATE_WORD) !=\n"
     "\t\t    ARM64_MT6797_A72_P30E_TARGET_CLAIMED ||"),
    (P30E, "CONTROLLER_SEQUENCE_WORD) != 1",
     "CONTROLLER_SEQUENCE_WORD) != 2"),
    (P30E, "TARGET_SEQUENCE_WORD) != 1", "TARGET_SEQUENCE_WORD) != 2"),
    (P30E, "identity != le64_to_cpu(READ_ONCE(\n"
     "\t\t\t    slot->target_boot_identity[i]))",
     "identity == le64_to_cpu(READ_ONCE(\n"
     "\t\t\t    slot->target_boot_identity[i]))"),
    (P30E, "memchr_inv(slot->reserved", "memchr_inv(NULL"),
    (P30E, "p30e_crc64(&initial) !=", "p30e_crc64(&initial) =="),
    (P30E, "CONTROLLER_SEQUENCE_WORD, 2",
     "CONTROLLER_SEQUENCE_WORD, 1"),
    (P30E, "struct arm64_mt6797_a72_p30e_slot *slot =\n"
     "\t\t&arm64_mt6797_a72_p30e_cpu9_slot;",
     "struct arm64_mt6797_a72_p30e_slot *slot =\n"
     "\t\t&arm64_mt6797_a72_p30e_cpu8_slot;"),
    (P30E, "smp_store_release((u64 *)&slot->wire.word[\n"
     "\t\tARM64_MT6797_A72_P30E_TARGET_STATE_WORD]",
     "WRITE_ONCE(*(u64 *)&slot->wire.word[\n"
     "\t\tARM64_MT6797_A72_P30E_TARGET_STATE_WORD]"),
    (P30E_HEADER, "int arm64_mt6797_a72_p30e_rearm_cpu9(void);\n", ""),
)

FINAL_MUTATIONS = PRIMITIVE_MUTATIONS + (
    (EXECUTOR, "ops->p30e_rearm && ops->cpu_boot",
     "ops->cpu_boot"),
    (EXECUTOR, "result->p30e_rearm_calls++;", ""),
    (EXECUTOR, "result->p30e_rearmed = true;", ""),
    (EXECUTOR, "ret = ops->p30e_rearm(context, cpu);",
     "ret = ops->cpu_boot(context, cpu);"),
    (EXECUTOR_HEADER, "MT6797_A72_RESTORE_STAGE_P30E_REARMED = 16",
     "MT6797_A72_RESTORE_STAGE_P30E_REARMED = 15"),
    (BINDING_HEADER, "MT6797_A72_RESTORE_READY_CPU9_PWR_CON 0x00010332U",
     "MT6797_A72_RESTORE_READY_CPU9_PWR_CON 0x0001033fU"),
    (BINDING, "if (!(result->last.spm_cpu_pwr_status &\n"
     "\t\t      MT6797_A72_RESTORE_READY_CPU9_STATUS) &&",
     "if (!((result->last.spm_cpu_pwr_status |\n"
     "\t\t       result->last.spm_cpu_pwr_status_2nd) &\n"
     "\t\t      MT6797_A72_RESTORE_READY_CPU9_STATUS) &&"),
    (BINDING, "arm64_mt6797_a72_p30e_rearm_cpu9()", "0"),
    (LEDGER_HEADER, "\tGEMINI_A72_HOTPLUG_P30E_REARMED,\n", ""),
    (LEDGER_INTERNAL, "GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 17U",
     "GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 16U"),
)


def run_mutations(root: Path, phase: str) -> list[str]:
    failures: list[str] = []
    mutations = PRIMITIVE_MUTATIONS if phase == "primitive" else FINAL_MUTATIONS
    for index, (relative, old, new) in enumerate(mutations):
        with tempfile.TemporaryDirectory(prefix="p30e-rearm-mutation-") as name:
            target_root = Path(name) / "source"
            shutil.copytree(root, target_root)
            path = target_root / relative
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                failures.append(f"mutation-{index}-anchor:{relative}")
                continue
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            if not validate(target_root, phase):
                failures.append(f"mutation-{index}-accepted:{relative}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("primitive", "final"),
                        default="final")
    args = parser.parse_args()
    failures = run_mutations(args.source_root.resolve(), args.phase)
    if failures:
        for failure in failures:
            print(f"p30e_rearm_mutation=fail reason={failure}")
        return 1
    count = len(PRIMITIVE_MUTATIONS if args.phase == "primitive" else
                FINAL_MUTATIONS)
    print("p30e_rearm_mutations=pass")
    print(f"validation_phase={args.phase}")
    print(f"mutations_rejected={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
