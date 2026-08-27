#!/usr/bin/env python3
"""Apply deterministic CPU8 PSCI/generic-hotplug lifecycle bridge edits."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES = SCRIPT_DIR.parent / "templates"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(
            f"{path}: expected one anchor: {old.splitlines()[0]}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_file(root: Path, relative: str, template: str) -> None:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"source path is not an exact regular file: {relative}")
    shutil.copyfile(TEMPLATES / template, path)


def apply_production(root: Path) -> None:
    cpu_h = root / "include/linux/cpu.h"
    cpu_c = root / "kernel/cpu.c"
    cpu_ops = root / "arch/arm64/include/asm/cpu_ops.h"
    smp = root / "arch/arm64/kernel/smp.c"
    test = root / "drivers/soc/mediatek/mt6797-a72-transition-test.c"

    replace_once(
        cpu_h,
        "int arch_cpu_up_validate(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t enum cpuhp_state target);\n",
        "int arch_cpu_up_validate(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t enum cpuhp_state target);\n"
        "int arch_cpu_up_secondary_complete(unsigned int cpu);\n"
        "int arch_cpu_up_complete(unsigned int cpu, enum cpuhp_state target);\n",
    )
    replace_once(
        cpu_ops,
        " * @cpu_up_rollback: Optional controller-side publication before "
        "generic CPUHP\n"
        " *\t\touter rollback. It receives the failing callback state, "
        "result, and trace.\n"
        " * @cpu_boot:\tBoots a cpu into the kernel.\n",
        " * @cpu_up_rollback: Optional controller-side publication before "
        "generic CPUHP\n"
        " *\t\touter rollback. It receives the failing callback state, "
        "result, and trace.\n"
        " * @cpu_up_secondary_complete: Optional controller callback "
        "immediately after\n"
        " *\t\ta successful architecture secondary completion.\n"
        " * @cpu_up_complete: Optional controller callback after the full "
        "requested\n"
        " *\t\tgeneric CPUHP target completes.\n"
        " * @cpu_boot:\tBoots a cpu into the kernel.\n",
    )
    replace_once(
        cpu_ops,
        "\tint\t\t(*cpu_up_rollback)(unsigned int cpu, "
        "enum cpuhp_state state,\n"
        "\t\t\t\t\t   int error, const struct "
        "cpu_up_rollback_trace *trace);\n"
        "\tint\t\t(*cpu_boot)(unsigned int);\n",
        "\tint\t\t(*cpu_up_rollback)(unsigned int cpu, "
        "enum cpuhp_state state,\n"
        "\t\t\t\t\t   int error, const struct "
        "cpu_up_rollback_trace *trace);\n"
        "\tint\t\t(*cpu_up_secondary_complete)(unsigned int cpu);\n"
        "\tint\t\t(*cpu_up_complete)(unsigned int cpu,\n"
        "\t\t\t\t\t   enum cpuhp_state target);\n"
        "\tint\t\t(*cpu_boot)(unsigned int);\n",
    )
    replace_once(
        smp,
        "int arch_cpu_up_rollback(unsigned int cpu, enum cpuhp_state state, "
        "int error,\n",
        "int arch_cpu_up_secondary_complete(unsigned int cpu)\n"
        "{\n"
        "\tconst struct cpu_operations *ops;\n\n"
        "\tif (cpu >= nr_cpu_ids)\n"
        "\t\treturn 0;\n\n"
        "\tops = get_cpu_ops(cpu);\n"
        "\tif (ops && ops->cpu_up_secondary_complete)\n"
        "\t\treturn ops->cpu_up_secondary_complete(cpu);\n\n"
        "\treturn 0;\n"
        "}\n\n"
        "int arch_cpu_up_complete(unsigned int cpu, enum cpuhp_state target)\n"
        "{\n"
        "\tconst struct cpu_operations *ops;\n\n"
        "\tif (cpu >= nr_cpu_ids)\n"
        "\t\treturn 0;\n\n"
        "\tops = get_cpu_ops(cpu);\n"
        "\tif (ops && ops->cpu_up_complete)\n"
        "\t\treturn ops->cpu_up_complete(cpu, target);\n\n"
        "\treturn 0;\n"
        "}\n\n"
        "int arch_cpu_up_rollback(unsigned int cpu, enum cpuhp_state state, "
        "int error,\n",
    )
    replace_once(
        cpu_c,
        "\tret = __cpu_up(cpu, idle);\n"
        "\tif (ret)\n"
        "\t\tgoto out_unlock;\n\n"
        "\tret = cpuhp_bp_sync_alive(cpu);\n",
        "\tret = __cpu_up(cpu, idle);\n"
        "\tif (ret)\n"
        "\t\tgoto out_unlock;\n\n"
        "\tret = arch_cpu_up_secondary_complete(cpu);\n"
        "\tif (ret)\n"
        "\t\tgoto out_unlock;\n\n"
        "\tret = cpuhp_bp_sync_alive(cpu);\n",
    )
    replace_once(
        cpu_c,
        "\ttarget = min((int)target, CPUHP_BRINGUP_CPU);\n"
        "\tret = cpuhp_up_callbacks(cpu, st, target);\n"
        "out:\n",
        "\ttarget = min((int)target, CPUHP_BRINGUP_CPU);\n"
        "\tret = cpuhp_up_callbacks(cpu, st, target);\n"
        "\tif (!ret)\n"
        "\t\tret = arch_cpu_up_complete(cpu, st->target);\n"
        "out:\n",
    )
    replace_once(
        cpu_c,
        "int __weak arch_cpu_up_validate(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t\tenum cpuhp_state target)\n"
        "{\n"
        "\treturn 0;\n"
        "}\n\n"
        "/**\n",
        "int __weak arch_cpu_up_validate(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t\tenum cpuhp_state target)\n"
        "{\n"
        "\treturn 0;\n"
        "}\n\n"
        "int __weak arch_cpu_up_secondary_complete(unsigned int cpu)\n"
        "{\n"
        "\treturn 0;\n"
        "}\n\n"
        "int __weak arch_cpu_up_complete(unsigned int cpu,\n"
        "\t\t\t\tenum cpuhp_state target)\n"
        "{\n"
        "\treturn 0;\n"
        "}\n\n"
        "/**\n",
    )
    replace_file(
        root,
        "drivers/soc/mediatek/mt6797-a72-transition-internal.h",
        "mt6797-a72-transition-internal.h",
    )
    replace_file(
        root,
        "drivers/soc/mediatek/mt6797-a72-transition.c",
        "mt6797-a72-transition.c",
    )
    replace_once(test, "\tunsigned int online_timeout_ms;\n", "")
    replace_once(
        test,
        "static int mt6797_test_online_wait(void *context, unsigned int cpu,\n"
        "\t\t\t\t   unsigned int timeout_ms)\n"
        "{\n"
        "\tstruct mt6797_transition_test_state *state = context;\n\n"
        "\tstate->online_target = cpu;\n"
        "\tstate->online_timeout_ms = timeout_ms;\n"
        "\treturn mt6797_test_effect(state,\n"
        "\t\t\tMT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);\n"
        "}\n",
        "static int mt6797_test_secondary_complete(void *context, "
        "unsigned int cpu)\n"
        "{\n"
        "\tstruct mt6797_transition_test_state *state = context;\n\n"
        "\tstate->online_target = cpu;\n"
        "\treturn mt6797_test_effect(state,\n"
        "\t\t\tMT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);\n"
        "}\n",
    )
    replace_once(
        test,
        "\t.online_wait = mt6797_test_online_wait,\n",
        "\t.secondary_complete = mt6797_test_secondary_complete,\n",
    )
    replace_once(
        test,
        "\tKUNIT_EXPECT_EQ(test, state.online_timeout_ms,\n"
        "\t\t\tMT6797_A72_TRANSITION_CPU_ON_WAIT_MS);\n",
        "",
    )
    replace_once(
        test,
        "\t\tif (stage >= MT6797_A72_TRANSITION_STAGE_IPI)\n"
        "\t\t\texpected_retained |= MT6797_A72_TRANSITION_OWNED_CPU8;\n",
        "\t\tif (stage >= MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT)\n"
        "\t\t\texpected_retained |= MT6797_A72_TRANSITION_OWNED_CPU8;\n",
    )
    replace_once(
        test,
        "\t\tKUNIT_EXPECT_EQ(test, result.cpu8_online,\n"
        "\t\t\t\tstage >= MT6797_A72_TRANSITION_STAGE_IPI);\n",
        "\t\tKUNIT_EXPECT_EQ(test, result.cpu8_online,\n"
        "\t\t\t\tstage >=\n"
        "\t\t\t\tMT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);\n",
    )


def apply_tests(root: Path) -> None:
    replace_file(
        root,
        "drivers/soc/mediatek/mt6797-a72-transition-test.c",
        "mt6797-a72-transition-test.c",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "production":
        apply_production(root)
    else:
        apply_tests(root)


if __name__ == "__main__":
    main()
