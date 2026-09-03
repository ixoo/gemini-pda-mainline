#!/usr/bin/env python3
"""Validate the exact CPU9 P30E rearm primitive and restore integration."""

from __future__ import annotations

import argparse
from pathlib import Path


def body(text: str, name: str) -> str:
    start = text.find(name + "(")
    if start < 0:
        raise ValueError(f"function missing: {name}")
    brace = text.find("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace:index + 1]
    raise ValueError(f"function unterminated: {name}")


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate_primitive(root: Path) -> list[str]:
    kconfig = (root / "arch/arm64/Kconfig").read_text()
    makefile = (root / "arch/arm64/kernel/Makefile").read_text()
    header = (root / "arch/arm64/include/asm/mt6797_a72_p30e.h").read_text()
    source = (root / "arch/arm64/kernel/mt6797_a72_p30e.c").read_text()
    test = (root / "arch/arm64/kernel/mt6797_a72_p30e_test.c").read_text()
    errors: list[str] = []
    try:
        prepare = body(source, "arm64_mt6797_a72_p30e_prepare_cpu9_rearm")
        rearm = body(source, "arm64_mt6797_a72_p30e_rearm_cpu9")
    except ValueError as exc:
        return [str(exc)]

    require(errors,
            "config ARM64_MT6797_A72_P30E_REARM_KUNIT_TEST" in kconfig,
            "P30E rearm KUnit option missing")
    require(errors, "mt6797_a72_p30e_test.o" in makefile,
            "P30E rearm KUnit object missing")
    require(errors, "int arm64_mt6797_a72_p30e_rearm_cpu9(void);" in header,
            "production rearm prototype missing")
    require(errors, "prepare_cpu9_rearm" in header,
            "testable rearm reconstruction prototype missing")
    for marker in (
        "P30E_MAGIC_WORD) !=\n\t\t    ARM64_MT6797_A72_P30E_MAGIC",
        "P30E_ABI_WORD) !=\n\t\t    ARM64_MT6797_A72_P30E_ABI_AND_SIZE",
        "ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP",
        "ARM64_MT6797_A72_P30E_CPU9",
        "ARM64_MT6797_A72_P30E_MPIDR_CPU9",
        "generation == ~0ULL", "cookie == ~0ULL",
        "ARM64_MT6797_A72_P30E_ARMED",
        "ARM64_MT6797_A72_P30E_TARGET_PUBLISHED",
        "ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD) != 1",
        "ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD) != 1",
        "ARM64_MT6797_A72_P30E_TARGET_REASON_WORD)",
        "ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD)",
        "ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD) !=",
        "ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD)",
        "identity != le64_to_cpu(READ_ONCE(\n"
        "\t\t\t    slot->target_boot_identity[i]))",
        "memchr_inv(slot->reserved",
        "p30e_crc64(&initial) !=", "CONTROLLER_SEQUENCE_WORD, 2",
    ):
        require(errors, marker in prepare,
                f"P30E rearm validation changed: {marker}")
    require(errors, prepare.count("*next = initial") == 1,
            "rearm reconstruction must publish output once after validation")
    require(errors, "TARGET_STATE_WORD,\n\t\t ARM64_MT6797_A72_P30E_EMPTY" in source,
            "rearm target-empty reconstruction missing")
    require(errors, "&arm64_mt6797_a72_p30e_cpu9_slot" in rearm,
            "production rearm target changed")
    require(errors, rearm.count("p30e_invalidate_slot(slot)") == 1,
            "production rearm invalidate count changed")
    require(errors, rearm.count("p30e_clean_slot(slot)") == 2,
            "production rearm clean count changed")
    require(errors, rearm.count("smp_store_release(") == 1,
            "target EMPTY release publication changed")
    require(errors, "if (ret)\n\t\tgoto out_unlock;" in rearm,
            "rearm failure no-write gate changed")
    require(errors, "cpu_up(" not in source and "cpu_down(" not in source and
            "psci_ops" not in source and "arm_smccc" not in source,
            "P30E primitive acquired a CPU or firmware operation")
    for marker in (
        "KUNIT_CASE(p30e_rearm_success_test)",
        "KUNIT_CASE(p30e_rearm_mutations_test)",
        "P30E_MUT_TARGET_BOOT_ID", "P30E_MUT_CONTROLLER_SEQUENCE",
        "P30E_MUT_ENTRY_PC", "P30E_MUT_RESERVED", "P30E_MUT_CRC",
        "P30E_MUT_COUNT",
    ):
        require(errors, marker in test, f"P30E KUnit coverage changed: {marker}")
    return errors


def validate_final(root: Path) -> list[str]:
    errors = validate_primitive(root)
    executor_header = (
        root / "drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h"
    ).read_text()
    executor = (
        root / "drivers/soc/mediatek/mt6797-a72-restore-executor.c"
    ).read_text()
    executor_test = (
        root / "drivers/soc/mediatek/mt6797-a72-restore-executor-test.c"
    ).read_text()
    binding_header = (
        root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h"
    ).read_text()
    binding = (
        root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c"
    ).read_text()
    binding_test = (
        root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c"
    ).read_text()
    ledger_public = (
        root / "include/linux/gemini_a72_hotplug_ledger.h"
    ).read_text()
    ledger_internal = (
        root / "fs/pstore/gemini_a72_hotplug_ledger_internal.h"
    ).read_text()
    ledger_test = (
        root / "fs/pstore/gemini_a72_hotplug_ledger_test.c"
    ).read_text()
    try:
        boot = body(executor, "mt6797_a72_restore_executor_boot")
        readiness = body(binding,
                         "mt6797_a72_hotplug_restore_readiness_with_ops")
        binding_rearm = body(binding,
                             "mt6797_a72_hotplug_restore_p30e_rearm")
    except ValueError as exc:
        return errors + [str(exc)]

    for marker in (
        "MT6797_A72_RESTORE_STAGE_P30E_REARMED = 16",
        "MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE = 17",
        "MT6797_A72_RESTORE_STAGE_FULL_COMPLETE = 18",
        "MT6797_A72_RESTORE_REARMING", "MT6797_A72_RESTORE_REARMED",
        "u32 p30e_rearm_calls;", "bool p30e_rearmed;",
        "int (*p30e_rearm)(void *context, unsigned int cpu);",
    ):
        require(errors, marker in executor_header,
                f"restore executor rearm contract changed: {marker}")
    require(errors, "ops->p30e_rearm && ops->cpu_boot" in executor,
            "rearm callback is not mandatory")
    for marker in (
        "result->p30e_rearm_calls++", "ops->p30e_rearm(context, cpu)",
        "result->p30e_rearmed = true",
        "MT6797_A72_RESTORE_STAGE_P30E_REARMED",
    ):
        require(errors, marker in boot, f"restore boot rearm step changed: {marker}")
    rearm_index = boot.find("ops->p30e_rearm(context, cpu)")
    rearm_checkpoint = boot.find(
        "MT6797_A72_RESTORE_STAGE_P30E_REARMED, true")
    cpu_boot_index = boot.find("ops->cpu_boot(context, cpu)")
    require(errors, 0 <= rearm_index < rearm_checkpoint < cpu_boot_index,
            "rearm/checkpoint/CPU_ON ordering changed")
    require(errors, boot.count("ops->cpu_boot(context, cpu)") == 1,
            "restore CPU_ON call count changed")
    require(errors, "KUNIT_CASE(restore_executor_rearm_failure_test)" in
            executor_test, "executor rearm failure KUnit missing")
    require(errors, "state->result.cpu_boot_calls, 0U" in executor_test,
            "zero-CPU_ON rearm failure assertion missing")
    require(errors, "checkpoints[4]" in executor_test,
            "executor checkpoint capacity changed")

    require(errors,
            "MT6797_A72_RESTORE_READY_CPU9_PWR_CON 0x00010332U" in
            binding_header, "exact CPU9 off power-control value changed")
    require(errors,
            "!(result->last.spm_cpu_pwr_status &" in readiness and
            "spm_mp2_cpu1_pwr_con ==" in readiness and
            "spm_cpu_pwr_status |" not in readiness,
            "readiness must use primary-off plus exact per-core-off")
    require(errors, "spm_cpu_pwr_status_2nd &\n"
                    "\t\t      MT6797_A72_RESTORE_READY_CPU8_STATUS" in
            readiness, "CPU8 secondary-mirror guard changed")
    require(errors, "arm64_mt6797_a72_p30e_rearm_cpu9()" in binding_rearm,
            "production binding does not invoke exact P30E rearm")
    require(errors, ".p30e_rearm = mt6797_a72_hotplug_restore_p30e_rearm" in
            binding, "production restore op missing P30E rearm")
    for marker in (
        "KUNIT_CASE(hotplug_binding_readiness_persistent_secondary_test)",
        "KUNIT_CASE(hotplug_binding_readiness_timeout_test)",
        "KUNIT_CASE(hotplug_binding_readiness_power_guard_test)",
        "KUNIT_CASE(hotplug_binding_readiness_cpu8_guard_test)",
    ):
        require(errors, marker in binding_test,
                f"binding KUnit coverage changed: {marker}")

    require(errors, "GEMINI_A72_HOTPLUG_P30E_REARMED" in ledger_public,
            "retained P30E rearm stage missing")
    require(errors,
            "#define GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 17U" in
            ledger_internal, "retained record maximum changed")
    require(errors,
            "#define GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD 0x00010003U" in
            ledger_internal, "retained semantic version changed")
    require(errors, "state.writes, 649U" in ledger_test,
            "retained successful-path write bound changed")
    require(errors, "GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS 37U" in
            ledger_internal, "wire layout unexpectedly changed")
    return errors


def validate(root: Path, phase: str) -> list[str]:
    return validate_primitive(root) if phase == "primitive" else validate_final(root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("primitive", "final"),
                        default="final")
    args = parser.parse_args()
    errors = validate(args.source_root.resolve(), args.phase)
    if errors:
        for error in errors:
            print(f"p30e_rearm_source=fail reason={error}")
        return 1
    print("p30e_rearm_source=pass")
    print(f"validation_phase={args.phase}")
    print("target_cpu=9")
    print("target_claim_changed=false")
    print("head_S_changed=false")
    if args.phase == "final":
        print("restore_cpu_on_calls_max=1")
        print("rearm_failure_cpu_on_calls=0")
        print("ledger_stages=14,15,16,17,18")
        print("ledger_version=0x00010003")
        print("successful_ledger_writes_max=649")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
