#!/usr/bin/env python3
"""Validate the CPU8/CPU9 scheduler-context source contract."""

from __future__ import annotations

import argparse
from pathlib import Path


MASK = (1 << 64) - 1


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def scheduler_hash(cpu: int) -> int:
    value = 0xD6E8FEB86659FD93 ^ cpu
    hash_ = 1469598103934665603
    for iteration in range(262144):
        value ^= (cpu << 57) & MASK
        value ^= (iteration * 0x9E3779B97F4A7C15) & MASK
        value ^= (value << 13) & MASK
        value ^= value >> 7
        value ^= (value << 17) & MASK
        value &= MASK
        hash_ = ((hash_ ^ value) * 1099511628211) & MASK
    return hash_


def validate(psci: str, cpu: str, hps: str) -> None:
    require(psci.count("gemini-a72-pair-v7") == 2, "pair-v7 inventory changed")
    require(psci.count("gemini-a72-pair-v6") == 0, "obsolete pair-v6 remains")
    require(psci.count("gemini-a72-pair-v2") == 3, "pair-v2 inventory changed")
    for token in (
        "#define MT6797_A72_PL_ROUNDS 128",
        "#define MT6797_A72_PL_LINES 1024",
        "pl_result8.write_hash == pl_result9.read_hash",
        "pl_result9.write_hash == pl_result8.read_hash",
        "if (mt6797_a72_pl_passed())",
        "hps_reported == 1 && hps_cpu == 9 && hps_error == -EPERM",
    ):
        require(token in psci, f"pair-v6 parent contract missing: {token}")
    require(
        "if (cpu == 8 || cpu == 9)" in cpu and "return -EPERM;" in cpu,
        "public CPU8/9 veto changed",
    )
    for token in (
        "atomic_cmpxchg(&mt6797_a72_hps_down_reported,",
        "atomic_inc(&mt6797_a72_hps_down_count);",
        "hotplug_ret = cpu_down(cpu);",
    ):
        require(token in hps, f"inherited HPS contract missing: {token}")

    for token in (
        "#include <linux/completion.h>",
        "#include <linux/interrupt.h>",
        "#include <linux/kthread.h>",
        "#define MT6797_A72_SC_ITERATIONS 262144",
        "#define MT6797_A72_SC_RESCHED_INTERVAL 4096",
        "#define MT6797_A72_SC_RESCHEDS 64",
        "#define MT6797_A72_SC_SPIN_BUDGET (1U << 25)",
        "#define MT6797_A72_SC_TIMEOUT_MS 2000",
        "#define MT6797_A72_SC_HASH8_EXPECTED 0xf678147669874ecdULL",
        "#define MT6797_A72_SC_HASH9_EXPECTED 0xc2274327e9c8104cULL",
        "static u64 mt6797_a72_sc_step(u64 value, int cpu, unsigned int iteration)\n"
        "{\n"
        "\tvalue ^= (u64)cpu << 57;\n"
        "\tvalue ^= (u64)iteration * 0x9e3779b97f4a7c15ULL;\n"
        "\tvalue ^= value << 13;\n"
        "\tvalue ^= value >> 7;\n"
        "\tvalue ^= value << 17;\n"
        "\treturn value;\n"
        "}",
        "!!(current->flags & PF_KTHREAD) && !in_interrupt()",
        "cpu = get_cpu();\n\tput_cpu();",
        "atomic_inc(&mt6797_a72_sc_ready);",
        "while (atomic_read(&mt6797_a72_sc_ready) != 2)",
        "if (!budget--)",
        "iteration < MT6797_A72_SC_ITERATIONS",
        "(iteration + 1) % MT6797_A72_SC_RESCHED_INTERVAL",
        "cond_resched();",
        "atomic_inc(&mt6797_a72_sc_finished);",
        "complete(done);",
        "kthread_create_on_cpu(mt6797_a72_sc_thread,",
        "&mt6797_a72_sc_result8, 8,",
        "&mt6797_a72_sc_result9, 9,",
        '"gemini-a72-sc/%u"',
        "wake_up_process(mt6797_a72_sc_task8)",
        "wake_up_process(mt6797_a72_sc_task9)",
        "deadline = jiffies + msecs_to_jiffies(MT6797_A72_SC_TIMEOUT_MS);",
        "if (completion_done(done))",
        "if (time_after_eq(jiffies, deadline))",
        "wait_for_completion_timeout(done, remaining)",
        "mt6797_a72_sc_wait_until(&mt6797_a72_sc_done8, deadline)",
        "mt6797_a72_sc_wait_until(&mt6797_a72_sc_done9, deadline)",
        "kthread_stop(mt6797_a72_sc_task8)",
        "kthread_stop(mt6797_a72_sc_task9)",
        "kthread_stop(mt6797_a72_sc_task8);\n\t\tmt6797_a72_sc_task8 = NULL;",
        "kthread_stop(mt6797_a72_sc_task9);\n\t\tmt6797_a72_sc_task9 = NULL;",
        "mt6797_a72_sc_task8 = NULL;",
        "mt6797_a72_sc_task9 = NULL;",
        "sc_result8.hash == MT6797_A72_SC_HASH8_EXPECTED",
        "sc_result9.hash == MT6797_A72_SC_HASH9_EXPECTED",
        "sc_result8.stop_result == sc_result8.error",
        "sc_result9.stop_result == sc_result9.error",
        "sc_reported=%d sc_iterations=262144 sc_rescheds=64",
        "sc_wait8=%d sc_wait9=%d",
        "sc_hash8=%016llx sc_hash9=%016llx",
    ):
        require(token in psci, f"scheduler contract missing: {token}")

    scheduler = psci.split("#define MT6797_A72_SC_ITERATIONS", 1)[1].split(
        "static void mt6797_a72_coh_workfn", 1
    )[0]
    require(scheduler.count("kthread_create_on_cpu(") == 2, "create count changed")
    require(scheduler.count("wake_up_process(") == 2, "wake count changed")
    require(
        scheduler.count("wait_for_completion_timeout(") == 1,
        "bounded wait primitive count changed",
    )
    require(
        scheduler.count("mt6797_a72_sc_wait_until(") == 3,
        "shared-deadline wait call count changed",
    )
    require(scheduler.count("kthread_stop(") == 2, "stop count changed")
    require(scheduler.count("cond_resched();") == 1, "reschedule call count changed")
    require(scheduler.count("complete(done);") == 1, "completion publication changed")
    require(psci.count("sc_hash9=%016llx") == 2, "terminal inventory changed")
    require(psci.count("mt6797_a72_sc_task8 = NULL;") == 3, "CPU8 clear count changed")
    require(psci.count("mt6797_a72_sc_task9 = NULL;") == 3, "CPU9 clear count changed")

    require(scheduler_hash(8) == 0xF678147669874ECD, "CPU8 hash vector changed")
    require(scheduler_hash(9) == 0xC2274327E9C8104C, "CPU9 hash vector changed")
    require(scheduler_hash(8) != scheduler_hash(9), "CPU hashes alias")

    for forbidden in (
        "cpu_down(",
        "cpu_up(",
        "psci_ops",
        "regulator_",
        "mtk_wdt",
        "writel",
        "writew",
        "writeb",
        "set_cpus_allowed",
        "sched_setscheduler",
        "set_user_nice",
        "kthread_bind(",
        "schedule_timeout",
        "msleep",
        "ssleep",
        "kmalloc",
        "vmalloc",
    ):
        require(forbidden not in scheduler, f"scheduler path has forbidden action: {forbidden}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    psci = (args.source / "arch/arm64/kernel/psci.c").read_text()
    cpu = (args.source / "kernel/cpu.c").read_text()
    hps = (
        args.source
        / "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c"
    ).read_text()
    validate(psci, cpu, hps)

    mutations = {
        "wrong-iterations": (
            "#define MT6797_A72_SC_ITERATIONS 262144",
            "#define MT6797_A72_SC_ITERATIONS 262143",
        ),
        "wrong-resched-interval": (
            "#define MT6797_A72_SC_RESCHED_INTERVAL 4096",
            "#define MT6797_A72_SC_RESCHED_INTERVAL 4095",
        ),
        "wrong-spin-budget": (
            "#define MT6797_A72_SC_SPIN_BUDGET (1U << 25)",
            "#define MT6797_A72_SC_SPIN_BUDGET (1U << 26)",
        ),
        "wrong-timeout": (
            "#define MT6797_A72_SC_TIMEOUT_MS 2000",
            "#define MT6797_A72_SC_TIMEOUT_MS 3000",
        ),
        "missing-task-context": (
            "!!(current->flags & PF_KTHREAD) && !in_interrupt()",
            "true",
        ),
        "wrong-cpu9": ("&mt6797_a72_sc_result9, 9,", "&mt6797_a72_sc_result9, 8,"),
        "unbounded-ready": (
            "while (atomic_read(&mt6797_a72_sc_ready) != 2) {\n"
            "\t\tif (!budget--) {",
            "while (atomic_read(&mt6797_a72_sc_ready) != 2) {\n"
            "\t\tif (false) {",
        ),
        "missing-resched": ("\t\t\t\tcond_resched();\n", ""),
        "wrong-recurrence": (
            "0x9e3779b97f4a7c15ULL",
            "0x9e3779b97f4a7c14ULL",
        ),
        "missing-ready": ("\tatomic_inc(&mt6797_a72_sc_ready);\n", ""),
        "missing-finished": ("\tatomic_inc(&mt6797_a72_sc_finished);\n", ""),
        "missing-complete": ("\tcomplete(done);\n", ""),
        "missing-parent-gate": (
            "\t\t\tif (mt6797_a72_pl_passed())\n",
            "\t\t\tif (true)\n",
        ),
        "async-wake-omitted": (
            "\tmt6797_a72_sc_result9.wake_result =\n"
            "\t\twake_up_process(mt6797_a72_sc_task9);\n",
            "",
        ),
        "independent-deadline": (
            "deadline = jiffies + msecs_to_jiffies(MT6797_A72_SC_TIMEOUT_MS);",
            "deadline = jiffies + msecs_to_jiffies(MT6797_A72_SC_TIMEOUT_MS * 2);",
        ),
        "missing-wait": (
            "\tmt6797_a72_sc_result9.wait_complete =\n"
            "\t\tmt6797_a72_sc_wait_until(&mt6797_a72_sc_done9, deadline);\n",
            "",
        ),
        "missing-stop": (
            "\t\tmt6797_a72_sc_result9.stop_result =\n"
            "\t\t\tkthread_stop(mt6797_a72_sc_task9);\n",
            "",
        ),
        "missing-stop-result-check": (
            "\t    sc_result9.stop_result == sc_result9.error &&\n",
            "",
        ),
        "missing-clear-after-stop": (
            "\t\tmt6797_a72_sc_result8.stop_result =\n"
            "\t\t\tkthread_stop(mt6797_a72_sc_task8);\n"
            "\t\tmt6797_a72_sc_task8 = NULL;\n",
            "\t\tmt6797_a72_sc_result8.stop_result =\n"
            "\t\t\tkthread_stop(mt6797_a72_sc_task8);\n",
        ),
        "wrong-hash8": (
            "0xf678147669874ecdULL",
            "0xf678147669874eccULL",
        ),
        "missing-hash-gate": (
            "\t    sc_result9.hash == MT6797_A72_SC_HASH9_EXPECTED)\n",
            "\t    sc_result9.hash != 0)\n",
        ),
        "incomplete-terminal": (" sc_hash8=%016llx sc_hash9=%016llx", ""),
    }
    for name, (old, new) in mutations.items():
        require(psci.count(old) >= 1, f"mutation anchor absent: {name}")
        mutated = psci.replace(old, new, 1)
        try:
            validate(mutated, cpu, hps)
        except SystemExit:
            continue
        raise SystemExit(f"error: mutation was not rejected: {name}")

    print("validation=a72-scheduler-context-source")
    print("hash_vectors=2-passed")
    print(f"mutations={len(mutations)}-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
