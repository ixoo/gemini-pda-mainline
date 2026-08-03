#!/usr/bin/env python3
"""Apply deterministic retention-window edits to the exact CPU9 parent."""

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


def edit_psci(source: Path) -> None:
    path = source / "arch/arm64/kernel/psci.c"
    replace_once(
        path,
        "unsigned long delay = sample == 1 ? 5000 : 4000;",
        "unsigned long delay = 2000;",
    )
    text = path.read_text()
    count = text.count("gemini-a72-pair-v1")
    if count != 4:
        raise EditError(f"{path}: expected four pair-v1 markers, found {count}")
    path.write_text(text.replace("gemini-a72-pair-v1", "gemini-a72-pair-v2"))


def edit_cpu_down(source: Path) -> None:
    path = source / "kernel/cpu.c"
    old = '''#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8
\tif (cpu == 8 || cpu == 9) {
\t\tpr_emerg("gemini-a72-hold-v1 result=down-veto cpu=%u stage=entry\\n",
\t\t\t cpu);
\t\treturn -EPERM;
\t}
#endif
'''
    new = '''#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8
\tif (cpu == 8 || cpu == 9) {
#ifndef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
\t\tpr_emerg("gemini-a72-hold-v1 result=down-veto cpu=%u stage=entry\\n",
\t\t\t cpu);
#endif
\t\treturn -EPERM;
\t}
#endif
'''
    replace_once(path, old, new)


def edit_hps(source: Path) -> None:
    path = (
        source
        / "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c"
    )
    anchor = "static int hps_algo_do_cluster_action(unsigned int cluster_id)\n"
    addition = '''#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
static atomic_t mt6797_a72_hps_down_reported = ATOMIC_INIT(0);
#endif

'''
    replace_once(path, anchor, addition + anchor)
    old = '''\t\t\t\tif (hotplug_ret)
\t\t\t\t\thps_warn("[Info]CPU %d --!\\n", cpu);
'''
    new = '''\t\t\t\tif (hotplug_ret) {
#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
\t\t\t\t\tif ((cpu == 8 || cpu == 9) &&
\t\t\t\t\t    hotplug_ret == -EPERM) {
\t\t\t\t\t\tif (!atomic_xchg(&mt6797_a72_hps_down_reported, 1))
\t\t\t\t\t\t\tpr_emerg("gemini-a72-retain-v1 result=hps-down-held-first cpu=%d error=%d\\n",
\t\t\t\t\t\t\t\t cpu, hotplug_ret);
\t\t\t\t\t} else
#endif
\t\t\t\t\t\thps_warn("[Info]CPU %d --!\\n", cpu);
\t\t\t\t}
'''
    replace_once(path, old, new)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_dir():
        raise EditError("source is not a directory")
    edit_psci(source)
    edit_cpu_down(source)
    edit_hps(source)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EditError as exc:
        raise SystemExit(f"error: {exc}")
