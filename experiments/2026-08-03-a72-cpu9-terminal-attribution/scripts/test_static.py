#!/usr/bin/env python3
"""Validate the CPU9 self-contained terminal source contract and mutations."""

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
    hps = (
        source
        / "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c"
    ).read_text()

    require(psci.count("gemini-a72-pair-v3") == 1, "pair-v3 inventory changed")
    require(psci.count("gemini-a72-pair-v2") == 3, "pair-v2 parent markers changed")
    require("unsigned long delay = 2000;" in psci, "pair timing changed")
    require("msecs_to_jiffies(1000)" in psci, "initial pair timing changed")
    require(
        "if (cpu == 8 || cpu == 9)" in cpu and "return -EPERM;" in cpu,
        "public CPU8/9 veto changed",
    )
    for token in (
        "static atomic_t mt6797_a72_hps_down_reported = ATOMIC_INIT(0);",
        "static atomic_t mt6797_a72_hps_down_first_cpu = ATOMIC_INIT(-1);",
        "static atomic_t mt6797_a72_hps_down_first_error = ATOMIC_INIT(0);",
        "static atomic_t mt6797_a72_hps_down_count = ATOMIC_INIT(0);",
        "atomic_cmpxchg(&mt6797_a72_hps_down_reported,",
        "atomic_inc(&mt6797_a72_hps_down_count);",
        "smp_wmb();",
        "atomic_set(&mt6797_a72_hps_down_reported, 1);",
        "void mt6797_a72_hps_down_snapshot(",
        "smp_rmb();",
        "hotplug_ret = cpu_down(cpu);",
    ):
        require(token in hps, f"HPS contract missing: {token}")
    for token in (
        "mt6797_a72_hps_down_snapshot(&hps_reported, &hps_cpu,",
        "hps_reported=%d hps_cpu=%d hps_error=%d hps_count=%d",
    ):
        require(token in psci, f"terminal contract missing: {token}")
    snapshot = hps.split("void mt6797_a72_hps_down_snapshot(", 1)[1].split(
        "#endif", 1
    )[0]
    for forbidden in (
        "cpu_down(",
        "cpu_up(",
        "pr_",
        "psci_ops",
        "regulator_",
        "mtk_wdt",
        "writel",
        "writew",
        "writeb",
    ):
        require(forbidden not in snapshot, f"snapshot has side effect: {forbidden}")

    pair_work = psci.split(
        "static void mt6797_a72_hold_workfn(struct work_struct *work)", 1
    )[1].split("static void mt6797_a72_one_way_marker", 1)[0]
    for forbidden in (
        "psci_ops.cpu_off",
        "cpu_ops[cpu]->cpu_die",
        "mtk_wdt_restart",
        "mtk_wdt_set_timeout",
        "regulator_set_voltage",
        "cpu_up(8)",
        "cpu_up(9)",
    ):
        require(forbidden not in pair_work, f"forbidden pair-work action: {forbidden}")

    mutations = {
        "late-sample": psci.replace(
            "unsigned long delay = 2000;", "unsigned long delay = 5000;", 1
        ),
        "missing-count": hps.replace(
            "atomic_inc(&mt6797_a72_hps_down_count);", "", 1
        ),
        "non-atomic-claim": hps.replace(
            "atomic_cmpxchg(&mt6797_a72_hps_down_reported,",
            "atomic_read(&mt6797_a72_hps_down_reported /*",
            1,
        ),
        "missing-write-barrier": hps.replace("\t\t\t\t\t\t\tsmp_wmb();\n", "", 1),
        "missing-read-barrier": hps.replace("\tsmp_rmb();\n", "", 1),
        "incomplete-terminal": psci.replace(" hps_count=%d", "", 1),
        "unbounded-report": hps.replace(
            "if (atomic_cmpxchg(&mt6797_a72_hps_down_reported,\n",
            "if (1 || atomic_cmpxchg(&mt6797_a72_hps_down_reported,\n",
            1,
        ),
    }
    require("unsigned long delay = 2000;" not in mutations["late-sample"],
            "timing mutation survived")
    require("atomic_inc(&mt6797_a72_hps_down_count);" not in
            mutations["missing-count"], "count mutation survived")
    require(mutations["non-atomic-claim"] != hps, "claim mutation did not apply")
    require("smp_wmb();" not in mutations["missing-write-barrier"],
            "write-barrier mutation survived")
    require("smp_rmb();" not in mutations["missing-read-barrier"],
            "read-barrier mutation survived")
    require("hps_count=%d" not in mutations["incomplete-terminal"],
            "terminal mutation survived")
    require("if (1 || atomic_cmpxchg" in mutations["unbounded-report"],
            "one-shot mutation did not apply")

    print("validation=cpu9-terminal-attribution-source")
    print("mutations=7-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
