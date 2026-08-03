#!/usr/bin/env python3
"""Apply deterministic CPU8 held-online edits to the exact one-way parent."""

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


def generic_veto(source: Path) -> None:
    cpu = source / "kernel/cpu.c"
    replace_once(
        cpu,
        "int __ref cpu_down(unsigned int cpu)\n{\n\tint err;\n",
        "int __ref cpu_down(unsigned int cpu)\n{\n"
        "\tint err;\n\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\tif (cpu == 8 || cpu == 9) {\n"
        "\t\tpr_emerg(\"gemini-a72-hold-v1 result=down-veto cpu=%u stage=entry\\n\",\n"
        "\t\t\t cpu);\n"
        "\t\treturn -EPERM;\n"
        "\t}\n"
        "#endif\n",
    )


def hps_floor(source: Path) -> None:
    hps = (
        source
        / "drivers/misc/mediatek/base/power/mt6797"
        / "mt_hotplug_strategy_algo.c"
    )
    replace_once(
        hps,
        "\tcpu_id_min = hps_sys.cluster_info[cluster_id].cpu_id_min;\n"
        "\tcpu_id_max = hps_sys.cluster_info[cluster_id].cpu_id_max;\n\n"
        "\tif (target_cores > online_cores) {\t/*Power up cpus */",
        "\tcpu_id_min = hps_sys.cluster_info[cluster_id].cpu_id_min;\n"
        "\tcpu_id_max = hps_sys.cluster_info[cluster_id].cpu_id_max;\n\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\tif (cpu_id_min == 8 && cpu_id_max == 9 &&\n"
        "\t    cpu_online(8) && target_cores < 1)\n"
        "\t\ttarget_cores = 1;\n"
        "#endif\n\n"
        "\tif (target_cores > online_cores) {\t/*Power up cpus */",
    )


def hold_probe(source: Path) -> None:
    psci = source / "arch/arm64/kernel/psci.c"
    replace_once(
        psci,
        "#include <linux/console.h>\n#endif\n",
        "#include <linux/console.h>\n"
        "#include <linux/workqueue.h>\n"
        "#endif\n",
    )
    replace_once(
        psci,
        "static bool mt6797_a72_one_way_psci_accepted;\n\n"
        "static void mt6797_a72_one_way_marker",
        "static bool mt6797_a72_one_way_psci_accepted;\n"
        "static atomic_t mt6797_a72_hold_hits = ATOMIC_INIT(0);\n"
        "static struct delayed_work mt6797_a72_hold_work;\n\n"
        "static void mt6797_a72_hold_ipi(void *data)\n"
        "{\n"
        "\tint *observed_cpu = data;\n\n"
        "\t*observed_cpu = smp_processor_id();\n"
        "\tsmp_mb();\n"
        "}\n\n"
        "static void mt6797_a72_hold_workfn(struct work_struct *work)\n"
        "{\n"
        "\tint observed_cpu = -1;\n"
        "\tint sample = atomic_read(&mt6797_a72_hold_hits) + 1;\n"
        "\tint ret;\n\n"
        "\tret = smp_call_function_single(8, mt6797_a72_hold_ipi,\n"
        "\t\t\t\t       &observed_cpu, 1);\n"
        "\tif (ret || observed_cpu != 8 || !cpu_online(8) || cpu_online(9)) {\n"
        "\t\tpr_emerg(\"gemini-a72-hold-v1 result=fault sample=%d cpu=%d cpu8=%d cpu9=%d error=%d\\n\",\n"
        "\t\t\t sample, observed_cpu, cpu_online(8), cpu_online(9), ret);\n"
        "\t\tconsole_lock();\n"
        "\t\tconsole_unlock();\n"
        "\t\treturn;\n"
        "\t}\n"
        "\tatomic_inc(&mt6797_a72_hold_hits);\n"
        "\tif (sample == 1) {\n"
        "\t\tpr_emerg(\"gemini-a72-hold-v1 result=sample sample=1 cpu=8 cpu8=1 cpu9=0 online=%u\\n\",\n"
        "\t\t\t num_online_cpus());\n"
        "\t\tconsole_lock();\n"
        "\t\tconsole_unlock();\n"
        "\t\tif (!schedule_delayed_work(&mt6797_a72_hold_work,\n"
        "\t\t\t\t\t   msecs_to_jiffies(5000))) {\n"
        "\t\t\tpr_emerg(\"gemini-a72-hold-v1 result=fault sample=2 cpu=-1 cpu8=%d cpu9=%d error=%d\\n\",\n"
        "\t\t\t\t cpu_online(8), cpu_online(9), -EBUSY);\n"
        "\t\t\tconsole_lock();\n"
        "\t\t\tconsole_unlock();\n"
        "\t\t}\n"
        "\t\treturn;\n"
        "\t}\n"
        "\tpr_emerg(\"gemini-a72-hold-v1 result=pass sample=2 cpu=8 cpu8=1 cpu9=0\\n\");\n"
        "\tconsole_lock();\n"
        "\tconsole_unlock();\n"
        "}\n\n"
        "static void mt6797_a72_one_way_marker",
    )
    replace_once(
        psci,
        "\tmt6797_a72_one_way_marker(\"cpu8-online-held\",\n"
        "\t\t\t\t\t    \"complete\", 0);\n"
        "\treturn 0;\n",
        "\tmt6797_a72_one_way_marker(\"cpu8-online-held\",\n"
        "\t\t\t\t\t    \"complete\", 0);\n"
        "\tINIT_DELAYED_WORK(&mt6797_a72_hold_work,\n"
        "\t\t\t  mt6797_a72_hold_workfn);\n"
        "\tif (!schedule_delayed_work(&mt6797_a72_hold_work,\n"
        "\t\t\t\t   msecs_to_jiffies(1000))) {\n"
        "\t\tmt6797_a72_one_way_marker(\"fault-retain-postiso\",\n"
        "\t\t\t\t\t    \"hold-schedule\", -EBUSY);\n"
        "\t\treturn -EBUSY;\n"
        "\t}\n"
        "\treturn 0;\n",
    )


STEPS = {
    "generic-veto": generic_veto,
    "hps-floor": hps_floor,
    "hold-probe": hold_probe,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--step", required=True, choices=tuple(STEPS))
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / ".git").exists():
        raise EditError(f"not a Git source tree: {source}")
    STEPS[args.step](source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
