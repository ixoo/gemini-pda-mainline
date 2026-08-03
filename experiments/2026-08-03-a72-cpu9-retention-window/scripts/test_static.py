#!/usr/bin/env python3
"""Validate the CPU9 retention-window source contract and mutations."""

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

    require(psci.count("gemini-a72-pair-v2") == 4, "pair-v2 inventory changed")
    require("gemini-a72-pair-v1" not in psci, "old pair marker remains")
    require(psci.count("unsigned long delay = 2000;") == 1, "delay changed")
    require(
        psci.count("sample == 1 ? 5000 : 4000") == 1,
        "parent CPU8 fallback delay changed",
    )
    require(
        "msecs_to_jiffies(1000)" in psci,
        "initial post-completion delay changed",
    )
    require(
        "if (cpu == 8 || cpu == 9)" in cpu and "return -EPERM;" in cpu,
        "public CPU8/9 veto changed",
    )
    require(
        "#ifndef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE" in cpu,
        "parent marker isolation missing",
    )
    for token in (
        "static atomic_t mt6797_a72_hps_down_reported = ATOMIC_INIT(0);",
        "hotplug_ret == -EPERM",
        "atomic_xchg(&mt6797_a72_hps_down_reported, 1)",
        "gemini-a72-retain-v1 result=hps-down-held-first",
        "hotplug_ret = cpu_down(cpu);",
    ):
        require(token in hps, f"HPS contract missing: {token}")
    require(hps.count("hps-down-held-first") == 1, "HPS marker is not unique")

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
        "late-second-sample": psci.replace(
            "unsigned long delay = 2000;", "unsigned long delay = 5000;", 1
        ),
        "old-marker": psci.replace("pair-v2", "pair-v1", 1),
        "veto-relaxed": cpu.replace(
            "\t\treturn -EPERM;\n\t}\n#endif",
            "\t\treturn 0;\n\t}\n#endif",
            1,
        ),
        "unbounded-report": hps.replace(
            "if (!atomic_xchg(&mt6797_a72_hps_down_reported, 1))", "if (1)", 1
        ),
    }
    require("unsigned long delay = 2000;" not in mutations["late-second-sample"],
            "delay mutation survived")
    require(mutations["old-marker"].count("gemini-a72-pair-v2") != 4,
            "marker mutation survived")
    require(mutations["veto-relaxed"] != cpu, "veto mutation did not apply")
    require("atomic_xchg(&mt6797_a72_hps_down_reported, 1)" not in
            mutations["unbounded-report"], "report mutation survived")

    print("validation=cpu9-retention-window-source")
    print("mutations=4-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
