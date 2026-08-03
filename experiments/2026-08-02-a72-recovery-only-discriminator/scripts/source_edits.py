#!/usr/bin/env python3
"""Apply deterministic recovery-only edits to pinned Gemian source."""

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


def guard_step(source: Path) -> None:
    kconfig = source / "drivers/watchdog/mediatek/wdt/Kconfig"
    psci = source / "arch/arm64/kernel/psci.c"

    replace_once(
        kconfig,
        "# common watchdog driver\n",
        "config MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "\tbool \"Gemini A72 recovery-only discriminator\"\n"
        "\tdepends on MTK_WATCHDOG && MTK_WD_KICKER\n"
        "\tdepends on PSTORE && PSTORE_CONSOLE && PSTORE_RAM\n"
        "\tdefault n\n"
        "\thelp\n"
        "\t  Experiment-only watchdog and console-ramoops recovery gate.\n"
        "\t  Rejects CPU8 and CPU9 before any platform or firmware action.\n\n"
        "# common watchdog driver\n",
    )
    replace_once(
        psci,
        "static int cpu_psci_cpu_boot(unsigned int cpu)\n{\n"
        "#ifdef CONFIG_ARCH_MT6797\n"
        "\tint err = 0;\n",
        "static int cpu_psci_cpu_boot(unsigned int cpu)\n{\n"
        "#ifdef CONFIG_ARCH_MT6797\n"
        "\tint err = 0;\n\n"
        "#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "\tif (cpu == 8 || cpu == 9) {\n"
        "\t\tpr_info(\"recovery-only: reject CPU%u before A72 action\\n\", cpu);\n"
        "\t\treturn -EPERM;\n"
        "\t}\n"
        "#endif\n",
    )


def owner_step(source: Path) -> None:
    header = source / "drivers/watchdog/mediatek/include/ext_wd_drv.h"
    wdt = source / "drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c"

    replace_once(
        header,
        "void mtk_wdt_set_time_out_value(unsigned int value);\n",
        "void mtk_wdt_set_time_out_value(unsigned int value);\n"
        "#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "struct mtk_wdt_recovery_state {\n"
        "\tunsigned int owned;\n"
        "\tunsigned int mode_before;\n"
        "\tunsigned int mode_after;\n"
        "\tunsigned int length_after;\n"
        "};\n"
        "int mtk_wdt_recovery_arm(unsigned int timeout,\n"
        "\t\t\t     struct mtk_wdt_recovery_state *state);\n"
        "#endif\n",
    )
    replace_once(
        wdt,
        "static DEFINE_SPINLOCK(rgu_reg_operation_spinlock);\n",
        "static DEFINE_SPINLOCK(rgu_reg_operation_spinlock);\n"
        "#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "static bool mtk_wdt_recovery_owned;\n"
        "#endif\n",
    )
    replace_once(
        wdt,
        "void mtk_wdt_restart(enum wd_restart_type type)\n{\n",
        "#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "int mtk_wdt_recovery_arm(unsigned int timeout,\n"
        "\t\t\t     struct mtk_wdt_recovery_state *state)\n"
        "{\n"
        "\tunsigned int length;\n"
        "\tunsigned int mode;\n"
        "\tint ret = 0;\n\n"
        "\tif (!state || timeout != 12)\n"
        "\t\treturn -EINVAL;\n"
        "\t*state = (struct mtk_wdt_recovery_state) { };\n"
        "\tspin_lock(&rgu_reg_operation_spinlock);\n"
        "\tif (!toprgu_base) {\n"
        "\t\tret = -ENODEV;\n"
        "\t\tgoto out;\n"
        "\t}\n"
        "\tif (mtk_wdt_recovery_owned) {\n"
        "\t\tstate->owned = 1;\n"
        "\t\tret = -EALREADY;\n"
        "\t\tgoto out;\n"
        "\t}\n"
        "\tstate->mode_before = __raw_readl(MTK_WDT_MODE);\n"
        "\tlength = (timeout * (1 << 6)) << 5;\n"
        "\tmode = state->mode_before | MTK_WDT_MODE_KEY;\n"
        "\tmode &= ~(MTK_WDT_MODE_IRQ | MTK_WDT_MODE_DUAL_MODE |\n"
        "\t\t  MTK_WDT_MODE_EXT_POL);\n"
        "\tmode |= MTK_WDT_MODE_ENABLE | MTK_WDT_MODE_EXTEN |\n"
        "\t\tMTK_WDT_MODE_AUTO_RESTART;\n"
        "\tmtk_wdt_recovery_owned = true;\n"
        "\tstate->owned = 1;\n"
        "\tmt_reg_sync_writel(length | MTK_WDT_LENGTH_KEY, MTK_WDT_LENGTH);\n"
        "\tmt_reg_sync_writel(mode, MTK_WDT_MODE);\n"
        "\tmt_reg_sync_writel(MTK_WDT_RESTART_KEY, MTK_WDT_RESTART);\n"
        "\tstate->length_after = __raw_readl(MTK_WDT_LENGTH);\n"
        "\tstate->mode_after = __raw_readl(MTK_WDT_MODE);\n"
        "\tif ((state->length_after & MTK_WDT_LENGTH_TIME_OUT) != length ||\n"
        "\t    (state->mode_after & (MTK_WDT_MODE_ENABLE |\n"
        "\t\tMTK_WDT_MODE_EXTEN | MTK_WDT_MODE_IRQ |\n"
        "\t\tMTK_WDT_MODE_DUAL_MODE)) !=\n"
        "\t    (MTK_WDT_MODE_ENABLE | MTK_WDT_MODE_EXTEN))\n"
        "\t\tret = -EIO;\n"
        "out:\n"
        "\tspin_unlock(&rgu_reg_operation_spinlock);\n"
        "\treturn ret;\n"
        "}\n"
        "#endif\n\n"
        "void mtk_wdt_restart(enum wd_restart_type type)\n{\n"
        "#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "\tif (READ_ONCE(mtk_wdt_recovery_owned))\n"
        "\t\treturn;\n"
        "#endif\n",
    )


def trigger_step(source: Path) -> None:
    common = source / "drivers/watchdog/mediatek/wdk/wd_common_drv.c"

    replace_once(
        common,
        "#include <linux/jiffies.h>\n",
        "#include <linux/jiffies.h>\n"
        "#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "#include <linux/console.h>\n"
        "#endif\n",
    )
    replace_once(
        common,
        "static struct work_struct wdk_work;\n",
        "static struct work_struct wdk_work;\n"
        "#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "static struct delayed_work recovery_discriminator_work;\n"
        "#endif\n",
    )
    replace_once(
        common,
        "static void wdk_work_callback(struct work_struct *work)\n{\n",
        "#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "static void recovery_discriminator_callback(struct work_struct *work)\n"
        "{\n"
        "\tstruct mtk_wdt_recovery_state state;\n"
        "\tint ret;\n\n"
        "\tcpu_hotplug_disable();\n"
        "\tspin_lock(&lock);\n"
        "\tif (!g_kicker_init || !g_wd_api || !g_wd_api->ready) {\n"
        "\t\tspin_unlock(&lock);\n"
        "\t\tcpu_hotplug_enable();\n"
        "\t\tpr_err(\"gemini-a72-recovery-v1 stage=preowner-reject reason=not-ready\\n\");\n"
        "\t\treturn;\n"
        "\t}\n"
        "\tg_enable = 0;\n"
        "\tret = mtk_wdt_recovery_arm(12, &state);\n"
        "\tif (ret && !state.owned)\n"
        "\t\tg_enable = 1;\n"
        "\tspin_unlock(&lock);\n\n"
        "\tif (ret && !state.owned) {\n"
        "\t\tcpu_hotplug_enable();\n"
        "\t\tpr_err(\"gemini-a72-recovery-v1 stage=preowner-reject error=%d\\n\", ret);\n"
        "\t\treturn;\n"
        "\t}\n"
        "\tif (ret)\n"
        "\t\tpr_emerg(\"gemini-a72-recovery-v1 stage=owned-readback-fault error=%d timeout=12s a72=forbidden\\n\", ret);\n"
        "\telse\n"
        "\t\tpr_emerg(\"gemini-a72-recovery-v1 stage=armed timeout=12s a72=forbidden\\n\");\n"
        "\tconsole_lock();\n"
        "\tconsole_unlock();\n"
        "}\n"
        "#endif\n\n"
        "static void wdk_work_callback(struct work_struct *work)\n{\n",
    )
    replace_once(
        common,
        "\tpr_alert(\"[WDK]init_wk done late_initcall cpus_kick_bit=0x%x -----\\n\", cpus_kick_bit);\n\n"
        "}\n",
        "\tpr_alert(\"[WDK]init_wk done late_initcall cpus_kick_bit=0x%x -----\\n\", cpus_kick_bit);\n"
        "#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n"
        "\tINIT_DELAYED_WORK(&recovery_discriminator_work,\n"
        "\t\t\t  recovery_discriminator_callback);\n"
        "\tschedule_delayed_work(&recovery_discriminator_work, 15 * HZ);\n"
        "#endif\n\n"
        "}\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--step", required=True, choices=("guard", "owner", "trigger"))
    args = parser.parse_args()
    source = args.source.resolve()
    {"guard": guard_step, "owner": owner_step, "trigger": trigger_step}[args.step](
        source
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
