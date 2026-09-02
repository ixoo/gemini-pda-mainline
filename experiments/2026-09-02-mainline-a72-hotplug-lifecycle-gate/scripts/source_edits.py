#!/usr/bin/env python3
"""Apply the no-op-by-default generic CPU-down lifecycle handoffs."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    cpu_h = root / "include/linux/cpu.h"
    cpu_c = root / "kernel/cpu.c"
    cpu_ops = root / "arch/arm64/include/asm/cpu_ops.h"
    smp = root / "arch/arm64/kernel/smp.c"

    replace_once(
        cpu_h,
        "int arch_cpu_up_complete(unsigned int cpu, enum cpuhp_state target);\n",
        "int arch_cpu_up_complete(unsigned int cpu, enum cpuhp_state target);\n"
        "int arch_cpu_down_preflight(unsigned int cpu, enum cpuhp_state target);\n"
        "int arch_cpu_down_validate(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t   enum cpuhp_state target);\n"
        "int arch_cpu_down_complete(unsigned int cpu, enum cpuhp_state target);\n"
        "int arch_cpu_down_failed(unsigned int cpu, enum cpuhp_state target,\n"
        "\t\t\t int error);\n",
    )
    replace_once(
        cpu_ops,
        " * @cpu_up_complete: Optional controller callback after the full "
        "requested\n"
        " *\t\tgeneric CPUHP target completes.\n"
        " * @cpu_boot:\tBoots a cpu into the kernel.\n",
        " * @cpu_up_complete: Optional controller callback after the full "
        "requested\n"
        " *\t\tgeneric CPUHP target completes.\n"
        " * @cpu_down_preflight: Optional controller callback before the CPU "
        "map lock.\n"
        " * @cpu_down_validate: Optional controller callback after the CPU "
        "map lock\n"
        " *\t\tand before the CPU hotplug write lock.\n"
        " * @cpu_down_complete: Optional controller callback after the full "
        "requested\n"
        " *\t\tgeneric CPUHP down target completes.\n"
        " * @cpu_down_failed: Optional controller callback after CPU-map "
        "unlock for a\n"
        " *\t\tfailed down request.\n"
        " * @cpu_boot:\tBoots a cpu into the kernel.\n",
    )
    replace_once(
        cpu_ops,
        "#ifdef CONFIG_HOTPLUG_CPU\n"
        "\tbool\t\t(*cpu_can_disable)(unsigned int cpu);\n",
        "#ifdef CONFIG_HOTPLUG_CPU\n"
        "\tint\t\t(*cpu_down_preflight)(unsigned int cpu,\n"
        "\t\t\t\t\t      enum cpuhp_state target);\n"
        "\tint\t\t(*cpu_down_validate)(unsigned int cpu,\n"
        "\t\t\t\t\t     int tasks_frozen,\n"
        "\t\t\t\t\t     enum cpuhp_state target);\n"
        "\tint\t\t(*cpu_down_complete)(unsigned int cpu,\n"
        "\t\t\t\t\t     enum cpuhp_state target);\n"
        "\tint\t\t(*cpu_down_failed)(unsigned int cpu,\n"
        "\t\t\t\t\t   enum cpuhp_state target,\n"
        "\t\t\t\t\t   int error);\n"
        "\tbool\t\t(*cpu_can_disable)(unsigned int cpu);\n",
    )
    replace_once(
        smp,
        "#ifdef CONFIG_HOTPLUG_CPU\n"
        "static int op_cpu_disable(unsigned int cpu)\n",
        "#ifdef CONFIG_HOTPLUG_CPU\n"
        "int arch_cpu_down_preflight(unsigned int cpu, enum cpuhp_state target)\n"
        "{\n"
        "\tconst struct cpu_operations *ops;\n\n"
        "\tif (cpu >= nr_cpu_ids)\n"
        "\t\treturn 0;\n\n"
        "\tops = get_cpu_ops(cpu);\n"
        "\tif (ops && ops->cpu_down_preflight)\n"
        "\t\treturn ops->cpu_down_preflight(cpu, target);\n\n"
        "\treturn 0;\n"
        "}\n\n"
        "int arch_cpu_down_validate(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t   enum cpuhp_state target)\n"
        "{\n"
        "\tconst struct cpu_operations *ops;\n\n"
        "\tif (cpu >= nr_cpu_ids)\n"
        "\t\treturn 0;\n\n"
        "\tops = get_cpu_ops(cpu);\n"
        "\tif (ops && ops->cpu_down_validate)\n"
        "\t\treturn ops->cpu_down_validate(cpu, tasks_frozen, target);\n\n"
        "\treturn 0;\n"
        "}\n\n"
        "int arch_cpu_down_complete(unsigned int cpu, enum cpuhp_state target)\n"
        "{\n"
        "\tconst struct cpu_operations *ops;\n\n"
        "\tif (cpu >= nr_cpu_ids)\n"
        "\t\treturn 0;\n\n"
        "\tops = get_cpu_ops(cpu);\n"
        "\tif (ops && ops->cpu_down_complete)\n"
        "\t\treturn ops->cpu_down_complete(cpu, target);\n\n"
        "\treturn 0;\n"
        "}\n\n"
        "int arch_cpu_down_failed(unsigned int cpu, enum cpuhp_state target,\n"
        "\t\t\t int error)\n"
        "{\n"
        "\tconst struct cpu_operations *ops;\n\n"
        "\tif (cpu >= nr_cpu_ids)\n"
        "\t\treturn 0;\n\n"
        "\tops = get_cpu_ops(cpu);\n"
        "\tif (ops && ops->cpu_down_failed)\n"
        "\t\treturn ops->cpu_down_failed(cpu, target, error);\n\n"
        "\treturn 0;\n"
        "}\n\n"
        "static int op_cpu_disable(unsigned int cpu)\n",
    )
    replace_once(
        cpu_c,
        "\tstruct cpuhp_cpu_state *st = per_cpu_ptr(&cpuhp_state, cpu);\n"
        "\tint prev_state, ret = 0;\n\n"
        "\tif (num_online_cpus() == 1)\n",
        "\tstruct cpuhp_cpu_state *st = per_cpu_ptr(&cpuhp_state, cpu);\n"
        "\tint prev_state, ret = 0;\n\n"
        "\tret = arch_cpu_down_validate(cpu, tasks_frozen, target);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n\n"
        "\tif (num_online_cpus() == 1)\n",
    )
    replace_once(
        cpu_c,
        "\tif (ret && st->state < prev_state) {\n"
        "\t\tif (st->state == CPUHP_TEARDOWN_CPU) {\n"
        "\t\t\tcpuhp_reset_state(cpu, st, prev_state);\n"
        "\t\t\t__cpuhp_kick_ap(st);\n"
        "\t\t} else {\n"
        "\t\t\tWARN(1, \"DEAD callback error for CPU%d\", cpu);\n"
        "\t\t}\n"
        "\t}\n\n"
        "out:\n",
        "\tif (ret && st->state < prev_state) {\n"
        "\t\tif (st->state == CPUHP_TEARDOWN_CPU) {\n"
        "\t\t\tcpuhp_reset_state(cpu, st, prev_state);\n"
        "\t\t\t__cpuhp_kick_ap(st);\n"
        "\t\t} else {\n"
        "\t\t\tWARN(1, \"DEAD callback error for CPU%d\", cpu);\n"
        "\t\t}\n"
        "\t}\n"
        "\tif (!ret)\n"
        "\t\tret = arch_cpu_down_complete(cpu, target);\n\n"
        "out:\n",
    )
    replace_once(
        cpu_c,
        "static int cpu_down_maps_locked(unsigned int cpu, enum cpuhp_state target)\n",
        "int __weak arch_cpu_down_preflight(unsigned int cpu,\n"
        "\t\t\t\t   enum cpuhp_state target)\n"
        "{\n"
        "\treturn 0;\n"
        "}\n\n"
        "int __weak arch_cpu_down_validate(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t\t  enum cpuhp_state target)\n"
        "{\n"
        "\treturn 0;\n"
        "}\n\n"
        "int __weak arch_cpu_down_complete(unsigned int cpu,\n"
        "\t\t\t\t  enum cpuhp_state target)\n"
        "{\n"
        "\treturn 0;\n"
        "}\n\n"
        "int __weak arch_cpu_down_failed(unsigned int cpu,\n"
        "\t\t\t\tenum cpuhp_state target, int error)\n"
        "{\n"
        "\treturn 0;\n"
        "}\n\n"
        "static int cpu_down_maps_locked(unsigned int cpu, enum cpuhp_state target)\n",
    )
    replace_once(
        cpu_c,
        "static int cpu_down(unsigned int cpu, enum cpuhp_state target)\n"
        "{\n"
        "\tint err;\n\n"
        "\tcpu_maps_update_begin();\n",
        "static int cpu_down(unsigned int cpu, enum cpuhp_state target)\n"
        "{\n"
        "\tint err;\n\n"
        "\terr = arch_cpu_down_preflight(cpu, target);\n"
        "\tif (err)\n"
        "\t\treturn err;\n\n"
        "\tcpu_maps_update_begin();\n",
    )
    replace_once(
        cpu_c,
        "\tcpu_maps_update_begin();\n"
        "\terr = cpu_down_maps_locked(cpu, target);\n"
        "\tcpu_maps_update_done();\n"
        "\treturn err;\n",
        "\tcpu_maps_update_begin();\n"
        "\terr = cpu_down_maps_locked(cpu, target);\n"
        "\tcpu_maps_update_done();\n"
        "\tif (err && arch_cpu_down_failed(cpu, target, err))\n"
        "\t\tpr_err(\"CPU%u down failure publication failed\\n\", cpu);\n"
        "\treturn err;\n",
    )


if __name__ == "__main__":
    main()
