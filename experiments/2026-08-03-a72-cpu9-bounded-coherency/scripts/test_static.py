#!/usr/bin/env python3
"""Validate the bounded CPU8/CPU9 coherency source contract and mutations."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    source = args.source
    psci = (source / "arch/arm64/kernel/psci.c").read_text()
    cpu = (source / "kernel/cpu.c").read_text()
    hps = (source / "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c").read_text()

    require(psci.count("gemini-a72-pair-v4") == 2, "pair-v4 inventory changed")
    require(psci.count("gemini-a72-pair-v3") == 0, "obsolete pair-v3 remains")
    require(psci.count("gemini-a72-pair-v2") == 3, "inherited pair-v2 markers changed")
    for token in ("unsigned long delay = 2000;", "msecs_to_jiffies(1000)"):
        require(token in psci, f"pair timing changed: {token}")
    require("if (cpu == 8 || cpu == 9)" in cpu and "return -EPERM;" in cpu, "public CPU8/9 veto changed")

    for token in (
        "#define MT6797_A72_COH_ROUNDS 1024",
        "#define MT6797_A72_COH_SPIN_BUDGET (1U << 24)",
        "while (READ_ONCE(mt6797_a72_coh_turn) != expected)",
        "if (!(*budget)--)",
        "cpu_relax();",
        "WRITE_ONCE(mt6797_a72_coh_seq8, round);",
        "WRITE_ONCE(mt6797_a72_coh_seq9, round);",
        "WRITE_ONCE(mt6797_a72_coh_turn, 8);",
        "WRITE_ONCE(mt6797_a72_coh_turn, 9);",
        "smp_wmb();",
        "smp_rmb();",
        "cpumask_set_cpu(8, &targets);",
        "cpumask_set_cpu(9, &targets);",
        "smp_call_function_many(&targets, mt6797_a72_coh_ipi, NULL, true);",
        "schedule_work_on(0, &mt6797_a72_coh_work)",
        "if (sample == 2)",
        "mt6797_a72_coh_snapshot(&coh_reported, &coh_rounds,",
        "coh_reported=%d coh_rounds=%d coh_cpu8=%d coh_cpu9=%d",
        "coh_error8=%d coh_error9=%d coh_seq8=%d coh_seq9=%d",
    ):
        require(token in psci, f"coherency contract missing: {token}")
    require(psci.count("smp_call_function_many(") == 1, "cross-call count changed")
    require(psci.count("mt6797_a72_coh_schedule();") == 1, "coherency schedule count changed")

    for token in (
        "atomic_cmpxchg(&mt6797_a72_hps_down_reported,",
        "atomic_inc(&mt6797_a72_hps_down_count);",
        "void mt6797_a72_hps_down_snapshot(",
        "hotplug_ret = cpu_down(cpu);",
    ):
        require(token in hps, f"inherited HPS contract missing: {token}")

    coherency = psci.split("#define MT6797_A72_COH_ROUNDS", 1)[1].split(
        "static void mt6797_a72_hold_workfn", 1
    )[0]
    for forbidden in (
        "cpu_down(", "cpu_up(", "psci_ops", "regulator_", "mtk_wdt",
        "writel", "writew", "writeb", "schedule_timeout", "msleep",
    ):
        require(forbidden not in coherency, f"coherency path has forbidden action: {forbidden}")

    mutations = {
        "wrong-rounds": psci.replace("#define MT6797_A72_COH_ROUNDS 1024", "#define MT6797_A72_COH_ROUNDS 1023", 1),
        "unbounded-wait": psci.replace("\t\tif (!(*budget)--)\n\t\t\treturn -ETIMEDOUT;\n", "", 1),
        "missing-read-once": psci.replace("READ_ONCE(mt6797_a72_coh_turn)", "mt6797_a72_coh_turn", 1),
        "missing-write-once": psci.replace("WRITE_ONCE(mt6797_a72_coh_turn, 9);", "mt6797_a72_coh_turn = 9;", 1),
        "missing-read-barrier": psci.replace("\tsmp_rmb();\n", "", 1),
        "missing-write-barrier": psci.replace("\t\t\tsmp_wmb();\n", "", 1),
        "wrong-mask": psci.replace("cpumask_set_cpu(9, &targets);", "cpumask_set_cpu(7, &targets);", 1),
        "asynchronous": psci.replace("mt6797_a72_coh_ipi, NULL, true);", "mt6797_a72_coh_ipi, NULL, false);", 1),
        "wrong-worker-cpu": psci.replace("schedule_work_on(0, &mt6797_a72_coh_work)", "schedule_work_on(8, &mt6797_a72_coh_work)", 1),
        "late-sample": psci.replace("unsigned long delay = 2000;", "unsigned long delay = 5000;", 1),
        "incomplete-terminal": psci.replace(" coh_seq9=%d", "", 1),
    }
    require("1024" not in mutations["wrong-rounds"].split("#define MT6797_A72_COH_ROUNDS", 1)[1].splitlines()[0], "round mutation survived")
    require("if (!(*budget)--" not in mutations["unbounded-wait"], "wait mutation survived")
    require("READ_ONCE(mt6797_a72_coh_turn)" not in mutations["missing-read-once"].split("mt6797_a72_coh_wait_turn", 1)[1].split("}", 1)[0], "read-once mutation survived")
    require("mt6797_a72_coh_turn = 9" in mutations["missing-write-once"], "write-once mutation failed")
    require(mutations["missing-read-barrier"] != psci, "read-barrier mutation failed")
    require(mutations["missing-write-barrier"] != psci, "write-barrier mutation failed")
    require("cpumask_set_cpu(7, &targets);" in mutations["wrong-mask"], "mask mutation failed")
    require("NULL, false);" in mutations["asynchronous"], "wait mutation failed")
    require("schedule_work_on(8" in mutations["wrong-worker-cpu"], "worker mutation failed")
    require("unsigned long delay = 2000;" not in mutations["late-sample"], "timing mutation survived")
    require(
        mutations["incomplete-terminal"].count("coh_seq9=%d")
        == psci.count("coh_seq9=%d") - 1,
        "terminal mutation did not remove exactly one field",
    )

    print("validation=cpu9-bounded-coherency-source")
    print("mutations=11-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
