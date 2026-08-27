#!/usr/bin/env python3
"""Validate the CPU8 PSCI/generic-hotplug lifecycle bridge source."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def bounded(source: str, start: str, end: str, label: str) -> str:
    first = source.find(start)
    require(first >= 0, f"{label}: start")
    last = source.find(end, first)
    require(last >= 0, f"{label}: end")
    return source[first:last + len(end)]


def braced(source: str, start: str, label: str) -> str:
    first = source.find(start)
    require(first >= 0, f"{label}: start")
    opening = source.find("{", first)
    require(opening >= 0, f"{label}: opening brace")
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[first:index + 1]
    raise SystemExit(f"validation failed: {label}: closing brace")


def ordered(source: str, tokens: tuple[str, ...], label: str) -> None:
    cursor = 0
    for token in tokens:
        position = source.find(token, cursor)
        require(position >= 0, f"{label}: missing token: {token}")
        cursor = position + len(token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    cpu_h = (root / "include/linux/cpu.h").read_text(encoding="utf-8")
    cpu_c = (root / "kernel/cpu.c").read_text(encoding="utf-8")
    cpu_ops = (root / "arch/arm64/include/asm/cpu_ops.h").read_text(
        encoding="utf-8")
    smp = (root / "arch/arm64/kernel/smp.c").read_text(encoding="utf-8")
    mt_psci = (root / "arch/arm64/kernel/mt6797_psci.c").read_text(
        encoding="utf-8")
    header = (root / "drivers/soc/mediatek/mt6797-a72-transition-internal.h"
              ).read_text(encoding="utf-8")
    source = (root / "drivers/soc/mediatek/mt6797-a72-transition.c").read_text(
        encoding="utf-8")
    normalized_cpu = collapse_whitespace(cpu_c)
    normalized_source = collapse_whitespace(source)

    for name in ("arch_cpu_up_secondary_complete", "arch_cpu_up_complete"):
        require(cpu_h.count(f"int {name}(") == 1,
                f"one generic declaration for {name}")
        require(cpu_ops.count(f"(*{name.removeprefix('arch_')})(") == 1,
                f"one cpu_operations field for {name}")
        require(smp.count(f"int {name}(") == 1,
                f"one arm64 dispatcher for {name}")
        require(cpu_c.count(f"int __weak {name}(") == 1,
                f"one no-op weak default for {name}")

    secondary_path = bounded(
        normalized_cpu,
        "ret = __cpu_up(cpu, idle);",
        "ret = cpuhp_bp_sync_alive(cpu);",
        "secondary completion hook placement",
    )
    ordered(
        secondary_path,
        (
            "ret = __cpu_up(cpu, idle);",
            "if (ret) goto out_unlock;",
            "ret = arch_cpu_up_secondary_complete(cpu);",
            "if (ret) goto out_unlock;",
            "ret = cpuhp_bp_sync_alive(cpu);",
        ),
        "secondary completion hook placement",
    )
    full_path = bounded(
        normalized_cpu,
        "ret = cpuhp_up_callbacks(cpu, st, target);",
        "cpus_write_unlock();",
        "full CPUHP completion hook placement",
    )
    ordered(
        full_path,
        (
            "ret = cpuhp_up_callbacks(cpu, st, target);",
            "if (!ret) ret = arch_cpu_up_complete(cpu, st->target);",
            "cpus_write_unlock();",
        ),
        "full CPUHP completion hook placement",
    )
    require("CONFIG_HOTPLUG_SPLIT_STARTUP" in cpu_c,
            "split-startup boundary remains explicit")

    require(mt_psci.count(".cpu_up_secondary_complete") == 0,
            "MT6797 secondary callback remains unset")
    require(mt_psci.count(".cpu_up_complete") == 0,
            "MT6797 full callback remains unset")
    veto = bounded(
        collapse_whitespace(mt_psci),
        "static int mt6797_psci_cpu_boot(unsigned int cpu)",
        "return -EAGAIN;",
        "MT6797 CPU boot veto",
    )
    require("A72 power sequence inactive" in veto,
            "MT6797 CPU boot veto remains active")
    require("cpu_psci_ops.cpu_boot" not in veto,
            "no production PSCI delegation")

    for token in (
        "enum mt6797_a72_transition_lifecycle",
        "MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED",
        "MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE",
        "atomic_t lifecycle;",
        "bool cpu_on_accepted;",
        "int (*secondary_complete)(void *context, unsigned int cpu);",
        "mt6797_a72_transition_begin(",
        "mt6797_a72_transition_secondary_complete(",
        "mt6797_a72_transition_complete(",
        "mt6797_a72_transition_fail(",
    ):
        require(token in header, f"internal lifecycle contract: {token}")
    require("MT6797_A72_TRANSITION_CPU_ON_WAIT_MS" not in header,
            "private ten-second wait removed")
    require("online_wait" not in header, "online-wait callback removed")

    for name in (
        "mt6797_a72_transition_begin",
        "mt6797_a72_transition_secondary_complete",
        "mt6797_a72_transition_complete",
        "mt6797_a72_transition_fail",
        "mt6797_a72_transition_run",
    ):
        require(source.count(f"int {name}(") == 1,
                f"one definition for {name}")
    begin = bounded(
        normalized_source,
        "int mt6797_a72_transition_begin(",
        "int mt6797_a72_transition_secondary_complete(",
        "split begin",
    )
    ordered(
        begin,
        (
            "MT6797_A72_TRANSITION_STAGE_WATCHDOG",
            "MT6797_A72_TRANSITION_STAGE_P27",
            "MT6797_A72_TRANSITION_STAGE_PROVIDER",
            "MT6797_A72_TRANSITION_STAGE_ISOLATION",
            "MT6797_A72_TRANSITION_STAGE_SRAM",
            "MT6797_A72_TRANSITION_STAGE_CPU_ON",
            "result->cpu_requests++;",
            "ret = ops->cpu_on(context, MT6797_A72_TRANSITION_CPU8);",
            "result->cpu_on_accepted = true;",
            "MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED",
        ),
        "begin order through CPU_ON acceptance",
    )
    for forbidden in ("ops->secondary_complete", "ops->ipi_proof",
                      "ops->dcm_update"):
        require(forbidden not in begin,
                f"begin pauses before later callback: {forbidden}")

    secondary = bounded(
        normalized_source,
        "int mt6797_a72_transition_secondary_complete(",
        "int mt6797_a72_transition_complete(",
        "secondary handoff",
    )
    ordered(
        secondary,
        (
            "MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED",
            "MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_INFLIGHT",
            "cpu != MT6797_A72_TRANSITION_CPU8",
            "MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT",
            "ret = ops->secondary_complete(context, cpu);",
            "MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE",
        ),
        "secondary handoff order",
    )
    complete = bounded(
        normalized_source,
        "int mt6797_a72_transition_complete(",
        "int mt6797_a72_transition_fail(",
        "full handoff",
    )
    ordered(
        complete,
        (
            "MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE",
            "MT6797_A72_TRANSITION_LIFECYCLE_FINAL_INFLIGHT",
            "MT6797_A72_TRANSITION_STAGE_IPI",
            "ret = ops->ipi_proof(context, cpu);",
            "MT6797_A72_TRANSITION_STAGE_DCM",
            "ret = ops->dcm_update(context);",
            "MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF",
        ),
        "full handoff order",
    )
    run = braced(
        normalized_source,
        "int mt6797_a72_transition_run(",
        "injected composition",
    )
    ordered(
        run,
        (
            "mt6797_a72_transition_begin(",
            "mt6797_a72_transition_secondary_complete(",
            "mt6797_a72_transition_complete(",
        ),
        "injected composition order",
    )
    require(source.count("ops->cpu_on(") == 1,
            "one CPU_ON callback site")
    require("cpu_off(" not in source.lower(), "no CPU_OFF callback")
    require("retry" not in source.lower(), "no retry implementation")
    for forbidden in (
        "wait_for_completion", "cpu_online(", "cpu_running", "psci_ops",
        "smp_call_function", "readl(", "writel(", "regmap_",
        "reset_control_", "arm_smccc", "gemini_transition_ledger",
        "mtk_wdt", "regulator_",
    ):
        require(forbidden not in source,
                f"executor has no physical/private owner: {forbidden}")

    test_path = root / "drivers/soc/mediatek/mt6797-a72-transition-test.c"
    if args.phase == "tests":
        test_source = test_path.read_text(encoding="utf-8")
        require(test_source.count("KUNIT_CASE(mt6797_transition_") == 10,
                "ten focused lifecycle cases")
        for token in (
            '"mt6797-a72-transition-executor"',
            "mt6797_transition_split_success_test",
            "mt6797_transition_composed_run_test",
            "mt6797_transition_entry_rejections_test",
            "mt6797_transition_missing_op_test",
            "mt6797_transition_one_shot_test",
            "mt6797_transition_stage_failures_test",
            "mt6797_transition_lifecycle_failure_test",
            "mt6797_transition_handoff_guards_test",
            "mt6797_transition_malformed_ownership_test",
            "mt6797_transition_rollback_faults_test",
            "MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED",
            "MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE",
        ):
            require(token in test_source, f"focused test token: {token}")
        for forbidden in (
            "wait_for_completion", "cpu_online(", "psci_", "arm_smccc",
            "smp_call_function", "readl(", "writel(", "regmap_",
            "reset_control_", "gemini_transition_ledger", "mtk_wdt",
            "regulator_", "cpu_up(", "cpu_down(",
        ):
            require(forbidden not in test_source,
                    f"hardware-free tests: {forbidden}")
    else:
        require(test_path.is_file(), "existing predecessor test retained")
        predecessor = test_path.read_text(encoding="utf-8")
        require("mt6797_transition_split_success_test" not in predecessor,
                "new tests absent from production phase")
        require(".secondary_complete = mt6797_test_secondary_complete" in
                predecessor, "predecessor tests follow the split API")
        require("online_timeout_ms" not in predecessor,
                "predecessor tests no longer assert a private timeout")

    print(f"source_phase={args.phase}")
    print("secondary_hook=after-successful-__cpu_up")
    print("full_hook=after-successful-cpuhp-up-callbacks")
    print("generic_secondary_timeout_ms=5000")
    print("focused_kunit_cases=10")
    print("cpu_on_maximum=1")
    print("cpu_off_maximum=0")
    print("retry_maximum=0")
    print("mt6797_production_lifecycle_callbacks=0")
    print("production_callers=0")
    print("physical_effect_calls=0")
    print("device_action=none")
    print("source_validation=pass")


if __name__ == "__main__":
    main()
