#!/usr/bin/env python3
"""Apply deterministic terminal-attribution edits to the exact window parent."""

from __future__ import annotations

import argparse
from pathlib import Path


class EditError(RuntimeError):
    pass


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise EditError(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def edit_hps(source: Path) -> None:
    path = (
        source
        / "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c"
    )
    old = """#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
static atomic_t mt6797_a72_hps_down_reported = ATOMIC_INIT(0);
#endif
"""
    new = """#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
static atomic_t mt6797_a72_hps_down_reported = ATOMIC_INIT(0);
static atomic_t mt6797_a72_hps_down_first_cpu = ATOMIC_INIT(-1);
static atomic_t mt6797_a72_hps_down_first_error = ATOMIC_INIT(0);
static atomic_t mt6797_a72_hps_down_count = ATOMIC_INIT(0);

void mt6797_a72_hps_down_snapshot(int *reported, int *cpu, int *error,
\t\t\t\t  int *count)
{
\t*reported = atomic_read(&mt6797_a72_hps_down_reported);
\tsmp_rmb();
\t*cpu = atomic_read(&mt6797_a72_hps_down_first_cpu);
\t*error = atomic_read(&mt6797_a72_hps_down_first_error);
\t*count = atomic_read(&mt6797_a72_hps_down_count);
}
#endif
"""
    replace_once(path, old, new)
    old = """\t\t\t\t\tif ((cpu == 8 || cpu == 9) &&
\t\t\t\t\t    hotplug_ret == -EPERM) {
\t\t\t\t\t\tif (!atomic_xchg(&mt6797_a72_hps_down_reported, 1))
\t\t\t\t\t\t\tpr_emerg("gemini-a72-retain-v1 result=hps-down-held-first cpu=%d error=%d\\n",
\t\t\t\t\t\t\t\t cpu, hotplug_ret);
\t\t\t\t\t} else
"""
    new = """\t\t\t\t\tif ((cpu == 8 || cpu == 9) &&
\t\t\t\t\t    hotplug_ret == -EPERM) {
\t\t\t\t\t\tatomic_inc(&mt6797_a72_hps_down_count);
\t\t\t\t\t\tif (atomic_cmpxchg(&mt6797_a72_hps_down_reported,
\t\t\t\t\t\t\t\t   0, -1) == 0) {
\t\t\t\t\t\t\tatomic_set(&mt6797_a72_hps_down_first_cpu,
\t\t\t\t\t\t\t\t   cpu);
\t\t\t\t\t\t\tatomic_set(&mt6797_a72_hps_down_first_error,
\t\t\t\t\t\t\t\t   hotplug_ret);
\t\t\t\t\t\t\tsmp_wmb();
\t\t\t\t\t\t\tatomic_set(&mt6797_a72_hps_down_reported, 1);
\t\t\t\t\t\t\tpr_emerg("gemini-a72-retain-v1 result=hps-down-held-first cpu=%d error=%d\\n",
\t\t\t\t\t\t\t\t cpu, hotplug_ret);
\t\t\t\t\t\t}
\t\t\t\t\t} else
"""
    replace_once(path, old, new)


def edit_psci(source: Path) -> None:
    path = source / "arch/arm64/kernel/psci.c"
    anchor = """static void mt6797_a72_hold_workfn(struct work_struct *work)
{
#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
\tint observed_cpu8 = -1;
"""
    replacement = """#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
extern void mt6797_a72_hps_down_snapshot(int *reported, int *cpu, int *error,
\t\t\t\t\t int *count);
#endif

static void mt6797_a72_hold_workfn(struct work_struct *work)
{
#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
\tint hps_reported;
\tint hps_cpu;
\tint hps_error;
\tint hps_count;
\tint observed_cpu8 = -1;
"""
    replace_once(path, anchor, replacement)
    old = """\tpr_emerg("gemini-a72-pair-v2 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3\\n");
"""
    new = """\tmt6797_a72_hps_down_snapshot(&hps_reported, &hps_cpu,
\t\t\t\t      &hps_error, &hps_count);
\tpr_emerg("gemini-a72-pair-v3 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=%d hps_cpu=%d hps_error=%d hps_count=%d\\n",
\t\t hps_reported, hps_cpu, hps_error, hps_count);
"""
    replace_once(path, old, new)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_dir():
        raise EditError("source is not a directory")
    edit_hps(source)
    edit_psci(source)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EditError as exc:
        raise SystemExit(f"error: {exc}")
