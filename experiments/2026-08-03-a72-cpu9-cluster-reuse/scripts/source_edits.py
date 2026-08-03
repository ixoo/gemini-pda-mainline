#!/usr/bin/env python3
"""Apply deterministic CPU9 cluster-reuse edits to the exact late parent."""

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


def edit_kconfig(source: Path) -> None:
    path = source / "drivers/misc/mediatek/base/power/Kconfig"
    anchor = """\t  Run one fail-closed CPU8 startup with exact pre-isolation
\t  rollback and post-isolation power retention. CPU9 and CPU-off
\t  are forbidden. This experiment always ends by watchdog reset.
"""
    addition = anchor + """
config MTK_A72_CPU9_CLUSTER_REUSE
\tbool "MT6797 one-way CPU9 cluster-reuse experiment"
\tdepends on MTK_A72_ONE_WAY_CPU8
\tdefault n
\thelp
\t  Permit one natural CPU9 request only after the exact one-way CPU8
\t  completion. Reuse the prepared cluster through standard PSCI and
\t  retain both CPUs until the inherited watchdog reset.
"""
    replace_once(path, anchor, addition)


def edit_psci(source: Path) -> None:
    path = source / "arch/arm64/kernel/psci.c"
    replace_once(
        path,
        "static atomic_t mt6797_a72_hold_hits = ATOMIC_INIT(0);\n"
        "static struct delayed_work mt6797_a72_hold_work;\n",
        "static atomic_t mt6797_a72_hold_hits = ATOMIC_INIT(0);\n"
        "static atomic_t mt6797_a72_cpu9_hits = ATOMIC_INIT(0);\n"
        "static atomic_t mt6797_a72_cpu9_attempted = ATOMIC_INIT(0);\n"
        "static bool mt6797_a72_cpu9_psci_accepted;\n"
        "static struct delayed_work mt6797_a72_hold_work;\n",
    )

    old_work = '''static void mt6797_a72_hold_workfn(struct work_struct *work)
{
\tint observed_cpu = -1;
\tint sample = atomic_read(&mt6797_a72_hold_hits) + 1;
\tint ret;

\tret = smp_call_function_single(8, mt6797_a72_hold_ipi,
\t\t\t\t       &observed_cpu, 1);
\tif (ret || observed_cpu != 8 || !cpu_online(8) || cpu_online(9)) {
\t\tpr_emerg("gemini-a72-hold-v2 result=fault sample=%d cpu=%d cpu8=%d cpu9=%d hits=%d error=%d\\n",
\t\t\t sample, observed_cpu, cpu_online(8), cpu_online(9),
\t\t\t atomic_read(&mt6797_a72_hold_hits), ret);
\t\tconsole_lock();
\t\tconsole_unlock();
\t\treturn;
\t}
\tatomic_inc(&mt6797_a72_hold_hits);
\tif (sample < 3) {
\t\tunsigned long delay = sample == 1 ? 5000 : 4000;

\t\tpr_emerg("gemini-a72-hold-v2 result=sample sample=%d cpu=8 cpu8=1 cpu9=0 hits=%d online=%u\\n",
\t\t\t sample, atomic_read(&mt6797_a72_hold_hits),
\t\t\t num_online_cpus());
\t\tconsole_lock();
\t\tconsole_unlock();
\t\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
\t\t\t\t\t   msecs_to_jiffies(delay))) {
\t\t\tpr_emerg("gemini-a72-hold-v2 result=fault sample=%d cpu=-1 cpu8=%d cpu9=%d hits=%d error=%d\\n",
\t\t\t\t sample + 1, cpu_online(8), cpu_online(9),
\t\t\t\t atomic_read(&mt6797_a72_hold_hits), -EBUSY);
\t\t\tconsole_lock();
\t\t\tconsole_unlock();
\t\t}
\t\treturn;
\t}
\tpr_emerg("gemini-a72-hold-v2 result=pass sample=3 cpu=8 cpu8=1 cpu9=0 hits=3\\n");
\tconsole_lock();
\tconsole_unlock();
}
'''
    new_work = '''static void mt6797_a72_hold_workfn(struct work_struct *work)
{
#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
\tint observed_cpu8 = -1;
\tint observed_cpu9 = -1;
\tint hits8 = atomic_read(&mt6797_a72_hold_hits);
\tint hits9 = atomic_read(&mt6797_a72_cpu9_hits);
\tint sample = hits8 + 1;
\tint ret8 = -EIO;
\tint ret9 = -EIO;

\tif (hits8 == hits9) {
\t\tret8 = smp_call_function_single(8, mt6797_a72_hold_ipi,
\t\t\t\t\t&observed_cpu8, 1);
\t\tret9 = smp_call_function_single(9, mt6797_a72_hold_ipi,
\t\t\t\t\t&observed_cpu9, 1);
\t}
\tif (ret8 || ret9 || observed_cpu8 != 8 || observed_cpu9 != 9 ||
\t    !cpu_online(8) || !cpu_online(9) || hits8 != hits9) {
\t\tpr_emerg("gemini-a72-pair-v1 result=fault sample=%d cpu8=%d cpu9=%d online8=%d online9=%d hits8=%d hits9=%d error8=%d error9=%d\\n",
\t\t\t sample, observed_cpu8, observed_cpu9, cpu_online(8),
\t\t\t cpu_online(9), hits8, hits9, ret8, ret9);
\t\tconsole_lock();
\t\tconsole_unlock();
\t\treturn;
\t}
\tatomic_inc(&mt6797_a72_hold_hits);
\tatomic_inc(&mt6797_a72_cpu9_hits);
\tif (sample < 3) {
\t\tunsigned long delay = sample == 1 ? 5000 : 4000;

\t\tpr_emerg("gemini-a72-pair-v1 result=sample sample=%d cpu8=8 cpu9=9 online8=1 online9=1 hits8=%d hits9=%d\\n",
\t\t\t sample, atomic_read(&mt6797_a72_hold_hits),
\t\t\t atomic_read(&mt6797_a72_cpu9_hits));
\t\tconsole_lock();
\t\tconsole_unlock();
\t\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
\t\t\t\t\t   msecs_to_jiffies(delay))) {
\t\t\tpr_emerg("gemini-a72-pair-v1 result=fault sample=%d cpu8=-1 cpu9=-1 online8=%d online9=%d hits8=%d hits9=%d error8=%d error9=%d\\n",
\t\t\t\t sample + 1, cpu_online(8), cpu_online(9),
\t\t\t\t atomic_read(&mt6797_a72_hold_hits),
\t\t\t\t atomic_read(&mt6797_a72_cpu9_hits), -EBUSY, -EBUSY);
\t\t\tconsole_lock();
\t\t\tconsole_unlock();
\t\t}
\t\treturn;
\t}
\tpr_emerg("gemini-a72-pair-v1 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3\\n");
\tconsole_lock();
\tconsole_unlock();
#else
\tint observed_cpu = -1;
\tint sample = atomic_read(&mt6797_a72_hold_hits) + 1;
\tint ret;

\tret = smp_call_function_single(8, mt6797_a72_hold_ipi,
\t\t\t\t       &observed_cpu, 1);
\tif (ret || observed_cpu != 8 || !cpu_online(8) || cpu_online(9)) {
\t\tpr_emerg("gemini-a72-hold-v2 result=fault sample=%d cpu=%d cpu8=%d cpu9=%d hits=%d error=%d\\n",
\t\t\t sample, observed_cpu, cpu_online(8), cpu_online(9),
\t\t\t atomic_read(&mt6797_a72_hold_hits), ret);
\t\tconsole_lock();
\t\tconsole_unlock();
\t\treturn;
\t}
\tatomic_inc(&mt6797_a72_hold_hits);
\tif (sample < 3) {
\t\tunsigned long delay = sample == 1 ? 5000 : 4000;

\t\tpr_emerg("gemini-a72-hold-v2 result=sample sample=%d cpu=8 cpu8=1 cpu9=0 hits=%d online=%u\\n",
\t\t\t sample, atomic_read(&mt6797_a72_hold_hits),
\t\t\t num_online_cpus());
\t\tconsole_lock();
\t\tconsole_unlock();
\t\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
\t\t\t\t\t   msecs_to_jiffies(delay))) {
\t\t\tpr_emerg("gemini-a72-hold-v2 result=fault sample=%d cpu=-1 cpu8=%d cpu9=%d hits=%d error=%d\\n",
\t\t\t\t sample + 1, cpu_online(8), cpu_online(9),
\t\t\t\t atomic_read(&mt6797_a72_hold_hits), -EBUSY);
\t\t\tconsole_lock();
\t\t\tconsole_unlock();
\t\t}
\t\treturn;
\t}
\tpr_emerg("gemini-a72-hold-v2 result=pass sample=3 cpu=8 cpu8=1 cpu9=0 hits=3\\n");
\tconsole_lock();
\tconsole_unlock();
#endif
}
'''
    replace_once(path, old_work, new_work)

    anchor = "static int mt6797_a72_one_way_boot(unsigned int cpu)\n"
    cpu9_code = '''#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
static void mt6797_a72_cpu9_marker(const char *result,
\t\t\t\t   const char *stage, int error)
{
\tpr_emerg("gemini-a72-cpu9-v1 result=%s stage=%s error=%d cpu8=%d cpu9=%d cluster=%u\\n",
\t\t result, stage, error, cpu_online(8), cpu_online(9),
\t\t g_cl2_online & 1);
\tconsole_lock();
\tconsole_unlock();
}

static int mt6797_a72_cpu9_boot(unsigned int cpu)
{
\tint ret;

\tif (cpu != 9)
\t\treturn -EPERM;
\tif (atomic_xchg(&mt6797_a72_cpu9_attempted, 1))
\t\treturn -EALREADY;
\tif (!READ_ONCE(mt6797_a72_one_way_psci_accepted) ||
\t    !(g_cl2_online & 1) || !cpu_online(8) || cpu_online(9)) {
\t\tmt6797_a72_cpu9_marker("rejected-prestate", "entry", -EINVAL);
\t\treturn -EINVAL;
\t}
\tret = psci_ops.cpu_on(cpu_logical_map(cpu), __pa(secondary_entry));
\tmt6797_a72_obs_lifecycle(cpu, MT6797_A72_PHASE_PSCI_MAPPED, ret,
\t\t\t\t cpu_logical_map(cpu), __pa(secondary_entry));
\tif (ret) {
\t\tmt6797_a72_cpu9_marker("fault-retain-psci", "psci", ret);
\t\treturn ret;
\t}
\tWRITE_ONCE(mt6797_a72_cpu9_psci_accepted, true);
\treturn 0;
}
#endif

'''
    replace_once(path, anchor, cpu9_code + anchor)

    old_complete = '''int mt6797_a72_one_way_secondary_complete(unsigned int cpu,
\t\t\t\t\t\t bool completed)
{
\tint ret;

\tif (cpu != 8)
\t\treturn 0;
\tif (!READ_ONCE(mt6797_a72_one_way_psci_accepted) ||
\t    !completed || !cpu_online(8) || cpu_online(9)) {
\t\tret = -EIO;
\t\tmt6797_a72_obs_rollback_terminal(cpu,
\t\t\tMT6797_A72_ROLLBACK_FAULT_RETAIN);
\t\tmt6797_a72_one_way_marker("fault-retain-postiso",
\t\t\t\t\t    "secondary", ret);
\t\treturn ret;
\t}
\tmt6797_a72_one_way_checkpoint("dcm");
\tret = mt6797_a72_one_way_dcm_enable(cpu);
\tif (ret) {
\t\tmt6797_a72_obs_rollback_terminal(cpu,
\t\t\tMT6797_A72_ROLLBACK_FAULT_RETAIN);
\t\tmt6797_a72_one_way_marker("fault-retain-postiso",
\t\t\t\t\t    "dcm", ret);
\t\treturn ret;
\t}
\tg_cl2_online |= 1;
\tmt6797_a72_one_way_marker("cpu8-online-held",
\t\t\t\t\t    "complete", 0);
\tINIT_DELAYED_WORK(&mt6797_a72_hold_work,
\t\t\t  mt6797_a72_hold_workfn);
\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
\t\t\t\t   msecs_to_jiffies(1000))) {
\t\tmt6797_a72_one_way_marker("fault-retain-postiso",
\t\t\t\t\t    "hold-schedule", -EBUSY);
\t\treturn -EBUSY;
\t}
\treturn 0;
}
'''
    new_complete = '''int mt6797_a72_one_way_secondary_complete(unsigned int cpu,
\t\t\t\t\t\t bool completed)
{
\tint ret;

#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
\tif (cpu == 9) {
\t\tif (!READ_ONCE(mt6797_a72_cpu9_psci_accepted) || !completed ||
\t\t    !(g_cl2_online & 1) || !cpu_online(8) || !cpu_online(9)) {
\t\t\tret = -EIO;
\t\t\tmt6797_a72_cpu9_marker("fault-retain-secondary",
\t\t\t\t\t       "secondary", ret);
\t\t\treturn ret;
\t\t}
\t\tmt6797_a72_cpu9_marker("cpu9-online-held", "complete", 0);
\t\tINIT_DELAYED_WORK(&mt6797_a72_hold_work,
\t\t\t\t  mt6797_a72_hold_workfn);
\t\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
\t\t\t\t\t   msecs_to_jiffies(1000))) {
\t\t\tmt6797_a72_cpu9_marker("fault-retain-secondary",
\t\t\t\t\t       "pair-schedule", -EBUSY);
\t\t\treturn -EBUSY;
\t\t}
\t\treturn 0;
\t}
#endif
\tif (cpu != 8)
\t\treturn 0;
\tif (!READ_ONCE(mt6797_a72_one_way_psci_accepted) ||
\t    !completed || !cpu_online(8) || cpu_online(9)) {
\t\tret = -EIO;
\t\tmt6797_a72_obs_rollback_terminal(cpu,
\t\t\tMT6797_A72_ROLLBACK_FAULT_RETAIN);
\t\tmt6797_a72_one_way_marker("fault-retain-postiso",
\t\t\t\t\t    "secondary", ret);
\t\treturn ret;
\t}
\tmt6797_a72_one_way_checkpoint("dcm");
\tret = mt6797_a72_one_way_dcm_enable(cpu);
\tif (ret) {
\t\tmt6797_a72_obs_rollback_terminal(cpu,
\t\t\tMT6797_A72_ROLLBACK_FAULT_RETAIN);
\t\tmt6797_a72_one_way_marker("fault-retain-postiso",
\t\t\t\t\t    "dcm", ret);
\t\treturn ret;
\t}
\tg_cl2_online |= 1;
\tmt6797_a72_one_way_marker("cpu8-online-held",
\t\t\t\t\t    "complete", 0);
#ifndef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
\tINIT_DELAYED_WORK(&mt6797_a72_hold_work,
\t\t\t  mt6797_a72_hold_workfn);
\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
\t\t\t\t   msecs_to_jiffies(1000))) {
\t\tmt6797_a72_one_way_marker("fault-retain-postiso",
\t\t\t\t\t    "hold-schedule", -EBUSY);
\t\treturn -EBUSY;
\t}
#endif
\treturn 0;
}
'''
    replace_once(path, old_complete, new_complete)

    old_cpu9 = '''\tif (cpu == 9) {
\t\tpr_info("one-way: reject CPU9 before A72 action\\n");
\t\terr = -EPERM;
\t\tgoto mt6797_a72_one_way_out;
\t}
'''
    new_cpu9 = '''\tif (cpu == 9) {
#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
\t\terr = mt6797_a72_cpu9_boot(cpu);
#else
\t\tpr_info("one-way: reject CPU9 before A72 action\\n");
\t\terr = -EPERM;
#endif
\t\tgoto mt6797_a72_one_way_out;
\t}
'''
    replace_once(path, old_cpu9, new_cpu9)


def edit_smp(source: Path) -> None:
    path = source / "arch/arm64/kernel/smp.c"
    replace_once(
        path,
        "\t\tif (cpu == 8)\n"
        "\t\t\tret = mt6797_a72_one_way_secondary_complete(cpu,\n"
        "\t\t\t\tsecondary_completed && cpu_online(cpu));\n",
        "\t\tif (cpu == 8\n"
        "#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE\n"
        "\t\t    || cpu == 9\n"
        "#endif\n"
        "\t\t   )\n"
        "\t\t\tret = mt6797_a72_one_way_secondary_complete(cpu,\n"
        "\t\t\t\tsecondary_completed && cpu_online(cpu));\n",
    )
    replace_once(
        path,
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\t\t\tif (cpu != 8)\n"
        "#endif\n"
        "\t\t\t\tBUG_ON(1);\n",
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\t\t\tif (cpu != 8\n"
        "#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE\n"
        "\t\t\t    && cpu != 9\n"
        "#endif\n"
        "\t\t\t   )\n"
        "#endif\n"
        "\t\t\t\tBUG_ON(1);\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / ".git").exists():
        raise EditError(f"not a Git source tree: {source}")
    edit_kconfig(source)
    edit_psci(source)
    edit_smp(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
