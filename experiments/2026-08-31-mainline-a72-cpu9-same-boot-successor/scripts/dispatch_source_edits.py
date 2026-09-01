#!/usr/bin/env python3
"""Apply the production CPU9 dispatch adapter source changes."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
from textwrap import dedent


HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
PARENT_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "6e6bcbbb4a4a4f15788cff2ba397053bc330c46489218c5b9ab8c0dd773b536f",
    "drivers/soc/mediatek/Makefile":
        "ffd78a82bd5e7c0fb0dbd7ff74855b4b3beb1516d1f342804ceb160e640a778a",
    "arch/arm64/kernel/mt6797_psci.c":
        "e2ad760ebbebcd9e0444547afa551bb0a301b169ab609e5685bfa2e0314eb434",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "d21815b0870ae50ca6020f935a5028d4fb700f3e974593f630750615b0f0f15f",
}
NEW_PATHS = (
    "include/linux/soc/mediatek/mt6797-a72-cpu9-binder.h",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder-internal.h",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder-test.c",
)

KCONFIG = dedent("""\
    config MTK_MT6797_A72_CPU9_BINDER
    \tbool "MediaTek MT6797 retained-cluster CPU9 dispatch binder"
    \tdepends on ARM64 && ARCH_MEDIATEK
    \tdepends on MTK_MT6797_A72_DEFAULT_OFF_BINDER
    \tdepends on MTK_MT6797_A72_CPU9_EXECUTOR
    \tdepends on ARM64_MT6797_A72_P30E_WIRE
    \tdefault n
    \thelp
    \t  Bind the separate CPU9 executor to the existing CPU9 P30E slot,
    \t  standard PSCI CPU_ON, generic secondary completion, one synchronous
    \t  IPI, CPU9 membership, and the independent retained ledger.

    \t  The proven CPU8 binder remains separate. This option adds PSCI
    \t  dispatch adapters but no controller, add_cpu caller, userspace
    \t  trigger, watchdog action, cluster effect, CPU_OFF, or retry path.
    \t  If unsure, say N.

    config MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST
    \tbool "KUnit tests for the MT6797 retained-cluster CPU9 binder"
    \tdepends on KUNIT=y
    \tdepends on MTK_MT6797_A72_CPU9_BINDER
    \tdefault n
    \thelp
    \t  Exercise request staging, PSCI-shaped dispatch, exact P30E and
    \t  membership sequencing, split completion, terminal mapping, failure
    \t  publication, and the absence of CPU_OFF and retry behavior.

    \t  Tests inject memory-only callbacks and perform no physical CPU,
    \t  retained-RAM, watchdog, regulator, clock, or device action.

    """)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"parent source is absent or unsafe: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"parent source changed: {relative}: {actual}")
    for relative in NEW_PATHS:
        if (root / relative).exists():
            raise SystemExit(f"new CPU9 binder path already exists: {relative}")


def copy_new(root: Path, relative: str) -> None:
    source = TEMPLATES / Path(relative).name
    target = root / relative
    if not source.is_file() or source.is_symlink():
        raise SystemExit(f"template is absent or unsafe: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def apply(root: Path) -> None:
    root = root.resolve()
    validate_parent(root)
    replace_once(
        root / "drivers/soc/mediatek/Kconfig",
        "config MTK_MT6797_A72_DEFAULT_OFF_BINDER\n",
        KCONFIG + "config MTK_MT6797_A72_DEFAULT_OFF_BINDER\n",
    )
    replace_once(
        root / "drivers/soc/mediatek/Makefile",
        "obj-$(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) += "
        "mt6797-a72-binder.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_CPU9_BINDER) += "
        "mt6797-a72-cpu9-binder.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST) += "
        "mt6797-a72-cpu9-binder-test.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) += "
        "mt6797-a72-binder.o\n",
    )
    psci = root / "arch/arm64/kernel/mt6797_psci.c"
    replace_once(
        psci,
        "#include <linux/soc/mediatek/mt6797-a72-binder.h>\n",
        "#include <linux/soc/mediatek/mt6797-a72-binder.h>\n"
        "#include <linux/soc/mediatek/mt6797-a72-cpu9-binder.h>\n",
    )
    replace_once(
        psci,
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER))\n"
        "\t\treturn mt6797_a72_binder_preflight(cpu, target);\n",
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)) {\n"
        "\t\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n"
        "\t\t\treturn mt6797_a72_cpu9_binder_preflight(cpu, target);\n"
        "\t\treturn mt6797_a72_binder_preflight(cpu, target);\n"
        "\t}\n",
    )
    replace_once(
        psci,
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER))\n"
        "\t\treturn mt6797_a72_binder_validate(cpu, tasks_frozen, target);\n",
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)) {\n"
        "\t\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n"
        "\t\t\treturn mt6797_a72_cpu9_binder_validate(\n"
        "\t\t\t\tcpu, tasks_frozen, target);\n"
        "\t\treturn mt6797_a72_binder_validate(cpu, tasks_frozen, target);\n"
        "\t}\n",
    )
    replace_once(
        psci,
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) &&\n"
        "\t    cpu == 8) {\n"
        "\t\tret = mt6797_a72_binder_failure(cpu, error, &publish_p32);\n"
        "\t\tif (ret || !publish_p32)\n"
        "\t\t\treturn ret;\n"
        "\t}\n",
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) &&\n"
        "\t    cpu == 8) {\n"
        "\t\tret = mt6797_a72_binder_failure(cpu, error, &publish_p32);\n"
        "\t\tif (ret || !publish_p32)\n"
        "\t\t\treturn ret;\n"
        "\t} else if (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) &&\n"
        "\t\t   cpu == 9) {\n"
        "\t\tret = mt6797_a72_cpu9_binder_failure(\n"
        "\t\t\tcpu, error, &publish_p32);\n"
        "\t\tif (ret || !publish_p32)\n"
        "\t\t\treturn ret;\n"
        "\t}\n",
    )
    replace_once(
        psci,
        "static int mt6797_psci_cpu_up_secondary_complete(unsigned int cpu)\n"
        "{\n"
        "\treturn mt6797_a72_binder_secondary_complete(cpu);\n"
        "}\n\n"
        "static int mt6797_psci_cpu_up_complete(unsigned int cpu,\n"
        "\t\t\t\t       enum cpuhp_state target)\n"
        "{\n"
        "\treturn mt6797_a72_binder_complete(cpu, target);\n"
        "}\n",
        "static int mt6797_psci_cpu_up_secondary_complete(unsigned int cpu)\n"
        "{\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n"
        "\t\treturn mt6797_a72_cpu9_binder_secondary_complete(cpu);\n"
        "\treturn mt6797_a72_binder_secondary_complete(cpu);\n"
        "}\n\n"
        "static int mt6797_psci_cpu_up_complete(unsigned int cpu,\n"
        "\t\t\t\t       enum cpuhp_state target)\n"
        "{\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n"
        "\t\treturn mt6797_a72_cpu9_binder_complete(cpu, target);\n"
        "\treturn mt6797_a72_binder_complete(cpu, target);\n"
        "}\n",
    )
    replace_once(
        psci,
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) && cpu == 8)\n"
        "\t\treturn mt6797_a72_binder_cpu_boot(cpu, cpu_psci_ops.cpu_boot);\n",
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) && cpu == 8)\n"
        "\t\treturn mt6797_a72_binder_cpu_boot(cpu, cpu_psci_ops.cpu_boot);\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n"
        "\t\treturn mt6797_a72_cpu9_binder_cpu_boot(\n"
        "\t\t\tcpu, cpu_psci_ops.cpu_boot);\n",
    )
    membership = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    replace_once(
        membership,
        "\tbool cpu8_on_ready;\n",
        "\tbool cpu8_on_ready;\n\tbool cpu9_on_ready;\n",
    )
    replace_once(
        membership,
        "\t\ta72_owner.active.provider_acquire_valid &&\n"
        "\t\ta72_owner.active.budgets.cpu_on == MT6797_A72_BUDGET_AVAILABLE;\n"
        "\tif (a72_owner.health != MT6797_A72_OWNER_AVAILABLE ||\n",
        "\t\ta72_owner.active.provider_acquire_valid &&\n"
        "\t\ta72_owner.active.budgets.cpu_on == MT6797_A72_BUDGET_AVAILABLE;\n"
        "\tcpu9_on_ready = identity->operation ==\n"
        "\t\tARM64_LATE_CPU_STARTUP_OP_CPU9_UP &&\n"
        "\t\ta72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&\n"
        "\t\ta72_owner.members == BIT(0) &&\n"
        "\t\ta72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&\n"
        "\t\ta72_owner.provider_identity.generation &&\n"
        "\t\ta72_owner.provider_identity.cookie &&\n"
        "\t\ta72_owner.active.p17_p18_published &&\n"
        "\t\ta72_owner.active.budgets.cpu_on == MT6797_A72_BUDGET_AVAILABLE &&\n"
        "\t\t!a72_owner.active.p27_valid &&\n"
        "\t\t!a72_owner.active.provider_acquire_valid &&\n"
        "\t\t!a72_owner.active.provider_abort_valid &&\n"
        "\t\t!a72_owner.active.p28_valid && !a72_owner.active.p29_valid &&\n"
        "\t\t!memcmp(&a72_owner.active.provider_identity,\n"
        "\t\t\t&a72_owner.provider_identity,\n"
        "\t\t\tsizeof(a72_owner.provider_identity));\n"
        "\tif (a72_owner.health != MT6797_A72_OWNER_AVAILABLE ||\n",
    )
    replace_once(
        membership,
        "\t    (a72_owner.phase != MT6797_A72_PHASE_FROZEN && !cpu8_on_ready) ||\n",
        "\t    (a72_owner.phase != MT6797_A72_PHASE_FROZEN &&\n"
        "\t     !cpu8_on_ready && !cpu9_on_ready) ||\n",
    )
    for relative in NEW_PATHS:
        copy_new(root, relative)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root)
