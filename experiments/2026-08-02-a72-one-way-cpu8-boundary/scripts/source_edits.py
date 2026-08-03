#!/usr/bin/env python3
"""Apply deterministic one-way CPU8 edits to patched Gemian source."""

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


def insert_before(path: Path, anchor: str, addition: str) -> None:
    replace_once(path, anchor, addition + anchor)


def watchdog_step(source: Path) -> None:
    header = source / "drivers/watchdog/mediatek/include/ext_wd_drv.h"
    wdt = source / "drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c"
    common = source / "drivers/watchdog/mediatek/wdk/wd_common_drv.c"

    replace_once(
        header,
        "void mtk_wdt_set_time_out_value(unsigned int value);\n",
        "void mtk_wdt_set_time_out_value(unsigned int value);\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "struct mtk_wdt_recovery_state {\n"
        "\tunsigned int owned;\n"
        "\tunsigned int mode_before;\n"
        "\tunsigned int mode_after;\n"
        "\tunsigned int length_after;\n"
        "};\n"
        "int mtk_wdt_recovery_arm(unsigned int timeout,\n"
        "\t\t\t     struct mtk_wdt_recovery_state *state);\n"
        "int mtk_wd_a72_recovery_takeover(struct mtk_wdt_recovery_state *state);\n"
        "#endif\n",
    )
    replace_once(
        wdt,
        "static DEFINE_SPINLOCK(rgu_reg_operation_spinlock);\n",
        "static DEFINE_SPINLOCK(rgu_reg_operation_spinlock);\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "static bool mtk_wdt_recovery_owned;\n"
        "#endif\n",
    )
    replace_once(
        wdt,
        "void mtk_wdt_restart(enum wd_restart_type type)\n{\n",
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
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
        "\t\tMTK_WDT_MODE_DUAL_MODE | MTK_WDT_MODE_EXT_POL |\n"
        "\t\tMTK_WDT_MODE_AUTO_RESTART)) !=\n"
        "\t    (MTK_WDT_MODE_ENABLE | MTK_WDT_MODE_EXTEN |\n"
        "\t     MTK_WDT_MODE_AUTO_RESTART))\n"
        "\t\tret = -EIO;\n"
        "out:\n"
        "\tspin_unlock(&rgu_reg_operation_spinlock);\n"
        "\treturn ret;\n"
        "}\n"
        "#endif\n\n"
        "void mtk_wdt_restart(enum wd_restart_type type)\n{\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\tif (READ_ONCE(mtk_wdt_recovery_owned))\n"
        "\t\treturn;\n"
        "#endif\n",
    )
    insert_before(
        common,
        "static void wdk_work_callback(struct work_struct *work)\n{\n",
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "int mtk_wd_a72_recovery_takeover(struct mtk_wdt_recovery_state *state)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tif (!state)\n"
        "\t\treturn -EINVAL;\n"
        "\t*state = (struct mtk_wdt_recovery_state) { };\n"
        "\tspin_lock(&lock);\n"
        "\tif (!g_kicker_init || !g_wd_api || !g_wd_api->ready) {\n"
        "\t\tret = -EAGAIN;\n"
        "\t\tgoto out;\n"
        "\t}\n"
        "\tg_enable = 0;\n"
        "\tret = mtk_wdt_recovery_arm(12, state);\n"
        "\tif (ret && !state->owned)\n"
        "\t\tg_enable = 1;\n"
        "out:\n"
        "\tspin_unlock(&lock);\n"
        "\treturn ret;\n"
        "}\n"
        "#endif\n\n",
    )


def helpers_step(source: Path) -> None:
    header = source / "include/linux/mt6797_a72_transition_observer.h"
    idvfs = source / "drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c"
    dcm = source / "drivers/misc/mediatek/base/power/mt6797/mt_dcm.c"

    insert_before(
        header,
        "\n#endif\n",
        "\nint mt6797_a72_one_way_sram_set_verify(unsigned int cpu);\n"
        "int mt6797_a72_one_way_dcm_enable(unsigned int cpu);\n"
        "int mt6797_a72_one_way_secondary_complete(unsigned int cpu,\n"
        "\t\t\t\t\t\t bool completed);\n",
    )
    insert_before(
        idvfs,
        "#endif\n\n/* 0x11017000 0x1000, i2c idvfsapb ctrl reg */",
        "\nint mt6797_a72_one_way_sram_set_verify(unsigned int cpu)\n"
        "{\n"
        "\tu32 calibration_first;\n"
        "\tu32 calibration_second;\n"
        "\tu32 selector_first;\n"
        "\tu32 selector_second;\n"
        "\tint ret;\n\n"
        "\tif (cpu != 8 || cpu_online(8) || cpu_online(9))\n"
        "\t\treturn -EPERM;\n"
        "\tret = BigiDVFSSRAMLDOSet(110000);\n"
        "\tudelay(240);\n"
        "\tselector_first = (u32)SEC_BIGIDVFS_READ(0x102222b0);\n"
        "\tcalibration_first = (u32)SEC_BIGIDVFS_READ(0x102222b4);\n"
        "\tselector_second = (u32)SEC_BIGIDVFS_READ(0x102222b0);\n"
        "\tcalibration_second = (u32)SEC_BIGIDVFS_READ(0x102222b4);\n"
        "\tif (ret < 0 || selector_first != selector_second ||\n"
        "\t    calibration_first != calibration_second ||\n"
        "\t    (calibration_second & 0xffff0000) ||\n"
        "\t    !(calibration_second & 0xffff) ||\n"
        "\t    (selector_second & 0xfff) != 0x8fb)\n"
        "\t\tret = -EIO;\n"
        "\telse\n"
        "\t\tret = 0;\n"
        "\tmt6797_a72_obs_lifecycle(cpu, MT6797_A72_PHASE_SRAM_POST,\n"
        "\t\t\t\t ret, selector_second & 0xfff,\n"
        "\t\t\t\t calibration_first == calibration_second);\n"
        "\treturn ret;\n"
        "}\n",
    )
    insert_before(
        dcm,
        "#endif\n\nint dcm_mcusys_little(ENUM_MCUSYS_DCM on)",
        "\nint mt6797_a72_one_way_dcm_enable(unsigned int cpu)\n"
        "{\n"
        "\tstruct mt6797_a72_obs_dcm snapshot = {\n"
        "\t\t.mask = MCUCFG_SYNC_DCM_MP2_MASK,\n"
        "\t\t.on = 1,\n"
        "\t};\n"
        "\tunsigned long flags;\n"
        "\tint ret = 0;\n\n"
        "\tif (cpu != 8 || !cpu_online(8) || cpu_online(9))\n"
        "\t\treturn -EPERM;\n"
        "\tspin_lock_irqsave(&mt6797_a72_obs_mp2_dcm_lock, flags);\n"
        "\tsnapshot.before = reg_read(MCUCFG_SYNC_DCM_MP2_CONFIG);\n"
        "\tif (snapshot.before & snapshot.mask) {\n"
        "\t\tret = -EINVAL;\n"
        "\t\tsnapshot.toggle = snapshot.before;\n"
        "\t\tsnapshot.final = snapshot.before;\n"
        "\t} else {\n"
        "\t\treg_write(MCUCFG_SYNC_DCM_MP2_CONFIG,\n"
        "\t\t\taor(snapshot.before, ~MCUCFG_SYNC_DCM_MP2_MASK,\n"
        "\t\t\t    MCUCFG_SYNC_DCM_MP2_ON |\n"
        "\t\t\t    MCUCFG_SYNC_DCM_MP2_DIV_SEL4 |\n"
        "\t\t\t    MCUCFG_SYNC_DCM_MP2_TOG1));\n"
        "\t\tsnapshot.toggle = reg_read(MCUCFG_SYNC_DCM_MP2_CONFIG);\n"
        "\t\treg_write(MCUCFG_SYNC_DCM_MP2_CONFIG,\n"
        "\t\t\taor(snapshot.toggle, ~MCUCFG_SYNC_DCM_MP2_MASK,\n"
        "\t\t\t    MCUCFG_SYNC_DCM_MP2_ON |\n"
        "\t\t\t    MCUCFG_SYNC_DCM_MP2_DIV_SEL4 |\n"
        "\t\t\t    MCUCFG_SYNC_DCM_MP2_TOG0));\n"
        "\t\tsnapshot.final = reg_read(MCUCFG_SYNC_DCM_MP2_CONFIG);\n"
        "\t\tif ((snapshot.toggle & snapshot.mask) != 0x0f ||\n"
        "\t\t    (snapshot.final & snapshot.mask) != 0x0d)\n"
        "\t\t\tret = -EIO;\n"
        "\t}\n"
        "\tspin_unlock_irqrestore(&mt6797_a72_obs_mp2_dcm_lock, flags);\n"
        "\tmt6797_a72_obs_dcm(cpu, MT6797_A72_PHASE_DCM_ENABLE, &snapshot);\n"
        "\treturn ret;\n"
        "}\n",
    )


def orchestrator_step(source: Path) -> None:
    psci = source / "arch/arm64/kernel/psci.c"
    smp = source / "arch/arm64/kernel/smp.c"
    kconfig = source / "drivers/misc/mediatek/base/power/Kconfig"

    replace_once(
        psci,
        "#include <linux/arm-smccc.h>\n",
        "#include <linux/arm-smccc.h>\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "#include <linux/atomic.h>\n"
        "#include <linux/console.h>\n"
        "#endif\n",
    )
    replace_once(
        kconfig,
        "\t  aid for one pinned downstream kernel and is not an A72 power driver.\n",
        "\t  aid for one pinned downstream kernel and is not an A72 power driver.\n\n"
        "config MTK_A72_ONE_WAY_CPU8\n"
        "\tbool \"MT6797 one-way CPU8 startup experiment\"\n"
        "\tdepends on SMP && HOTPLUG_CPU && CL2_BUCK_CTRL\n"
        "\tdepends on MTK_A72_TRANSITION_OBSERVER\n"
        "\tdepends on MTK_WATCHDOG && MTK_WD_KICKER\n"
        "\tdepends on PSTORE && PSTORE_CONSOLE && PSTORE_RAM\n"
        "\tdefault n\n"
        "\thelp\n"
        "\t  Run one fail-closed CPU8 startup with exact pre-isolation\n"
        "\t  rollback and post-isolation power retention. CPU9 and CPU-off\n"
        "\t  are forbidden. This experiment always ends by watchdog reset.\n",
    )
    insert_before(
        psci,
        "static int cpu_power_on_buck(unsigned int cpu, bool hotplug)\n",
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "static atomic_t mt6797_a72_one_way_attempted = ATOMIC_INIT(0);\n"
        "static bool mt6797_a72_one_way_psci_accepted;\n\n"
        "static void mt6797_a72_one_way_marker(const char *result,\n"
        "\t\t\t\t\t     const char *stage, int error)\n"
        "{\n"
        "\tpr_emerg(\"gemini-a72-oneway-v1 result=%s stage=%s error=%d cpu9=forbidden cpu_off=forbidden\\n\",\n"
        "\t\t result, stage, error);\n"
        "\tconsole_lock();\n"
        "\tconsole_unlock();\n"
        "}\n\n"
        "static void mt6797_a72_one_way_checkpoint(const char *stage)\n"
        "{\n"
        "\tpr_emerg(\"gemini-a72-oneway-v1 state=begin stage=%s\\n\", stage);\n"
        "}\n\n"
        "static int mt6797_a72_one_way_boot(unsigned int cpu)\n"
        "{\n"
        "\tstruct mtk_wdt_recovery_state watchdog;\n"
        "\tstruct mt6797_a72_obs_clock clock;\n"
        "\tvoid __iomem *reg_base;\n"
        "\tu32 ordering_read;\n"
        "\tbool buck_owned = false;\n"
        "\tbool pwrap_owned = false;\n"
        "\tbool reset_owned = false;\n"
        "\tbool reset_flag_owned = false;\n"
        "\tbool rollback_fault = false;\n"
        "\tbool prestate_bad = false;\n"
        "\tconst char *stage = \"entry\";\n"
        "\tint ret;\n\n"
        "\tif (cpu != 8)\n"
        "\t\treturn -EPERM;\n"
        "\tif (!mt6797_a72_obs_accepts_sampling(cpu))\n"
        "\t\treturn -EAGAIN;\n"
        "\tret = mtk_wd_a72_recovery_takeover(&watchdog);\n"
        "\tif (ret && !watchdog.owned)\n"
        "\t\treturn ret;\n"
        "\tif (ret) {\n"
        "\t\tmt6797_a72_one_way_marker(\"rejected-prestate\",\n"
        "\t\t\t\t\t    \"watchdog-readback\", ret);\n"
        "\t\treturn ret;\n"
        "\t}\n"
        "\tif (atomic_xchg(&mt6797_a72_one_way_attempted, 1)) {\n"
        "\t\tmt6797_a72_one_way_marker(\"rejected-prestate\",\n"
        "\t\t\t\t\t    \"one-shot\", -EALREADY);\n"
        "\t\treturn -EALREADY;\n"
        "\t}\n"
        "\tprestate_bad |= g_cl2_online || cpu_online(8) || cpu_online(9);\n"
        "\tret = mt6797_a72_diag_clock_capture(cpu,\n"
        "\t\t\t\t\t    MT6797_A72_PHASE_POWER_ON_PRE, &clock);\n"
        "\tprestate_bad |= !!ret;\n"
        "\tprestate_bad |= !mt6797_a72_diag_secure_zero(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_POWER_ON_PRE);\n"
        "\tprestate_bad |= !mt6797_a72_diag_dcm_zero(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_POWER_ON_PRE);\n"
        "\tprestate_bad |= !!da9214_a72_diag_compare_update(cpu, false, false,\n"
        "\t\t\t\t\t     MT6797_A72_PHASE_POWER_ON_PRE);\n"
        "\tprestate_bad |= !!mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\tMT6797_A72_PHASE_POWER_ON_PRE, 0x218,\n"
        "\t\t0x00010132, 0x00010132);\n"
        "\tprestate_bad |= !!mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\tMT6797_A72_PHASE_POWER_ON_PRE, 0x290, 0x2, 0x2);\n"
        "\tprestate_bad |= !!mt6797_a72_diag_toprgu_compare_update(cpu,\n"
        "\t\tfalse, false, MT6797_A72_PHASE_POWER_ON_PRE);\n"
        "\tspin_lock(&reset_lock);\n"
        "\tprestate_bad |= reset_flags != 0;\n"
        "\tif (!prestate_bad) {\n"
        "\t\treset_flags = 1;\n"
        "\t\treset_flag_owned = true;\n"
        "\t}\n"
        "\tspin_unlock(&reset_lock);\n"
        "\tif (prestate_bad) {\n"
        "\t\tmt6797_a72_obs_rollback_terminal(cpu,\n"
        "\t\t\tMT6797_A72_ROLLBACK_REJECTED_PRESTATE);\n"
        "\t\tmt6797_a72_one_way_marker(\"rejected-prestate\",\n"
        "\t\t\t\t\t    \"entry\", -EINVAL);\n"
        "\t\treturn -EINVAL;\n"
        "\t}\n\n"
        "\tstage = \"spm-reset\";\n"
        "\tmt6797_a72_one_way_checkpoint(stage);\n"
        "\tret = mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\tMT6797_A72_PHASE_SPM_RESET_RELEASE, 0x218,\n"
        "\t\t0x00010132, 0x00010133);\n"
        "\tif (ret) goto rollback;\n"
        "\treset_owned = true;\n"
        "\tstage = \"pll-ordering-read\";\n"
        "\tmt6797_a72_one_way_checkpoint(stage);\n"
        "\treg_base = ioremap(MT6797_IDVFS_BASE_ADDR, 0x1000);\n"
        "\tif (!reg_base) { ret = -ENOMEM; goto rollback; }\n"
        "\tordering_read = readl(reg_base + 0x4a0);\n"
        "\tiounmap(reg_base);\n"
        "\tmt6797_a72_obs_lifecycle(cpu, MT6797_A72_PHASE_PLL_ORDERING_READ,\n"
        "\t\t\t\t 0, ordering_read, 0x102224a0);\n"
        "\tstage = \"pwrap-assert\";\n"
        "\tmt6797_a72_one_way_checkpoint(stage);\n"
        "\tret = mt6797_a72_diag_toprgu_compare_update(cpu, false, true,\n"
        "\t\t\t\t\t    MT6797_A72_PHASE_TOPRGU_ASSERT);\n"
        "\tif (ret) goto rollback;\n"
        "\tpwrap_owned = true;\n"
        "\tstage = \"buck-enable\";\n"
        "\tmt6797_a72_one_way_checkpoint(stage);\n"
        "\tret = da9214_a72_diag_compare_update(cpu, false, true,\n"
        "\t\t\t\t\t     MT6797_A72_PHASE_BUCK_ENABLE);\n"
        "\tif (ret) goto rollback;\n"
        "\tbuck_owned = true;\n"
        "\tudelay(1000);\n"
        "\tstage = \"buck-settle\";\n"
        "\tret = da9214_a72_diag_compare_update(cpu, true, true,\n"
        "\t\t\t\t     MT6797_A72_PHASE_BUCK_ENABLE_SETTLED);\n"
        "\tif (ret) goto rollback;\n\n"
        "\tstage = \"isolation-write\";\n"
        "\tmt6797_a72_one_way_checkpoint(stage);\n"
        "\tret = mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\tMT6797_A72_PHASE_SPM_ISOLATION_CLEAR, 0x290, 0x2, 0x0);\n"
        "\tif (ret) goto postiso_fault;\n"
        "\tstage = \"pwrap-deassert\";\n"
        "\tmt6797_a72_one_way_checkpoint(stage);\n"
        "\tret = mt6797_a72_diag_toprgu_compare_update(cpu, true, false,\n"
        "\t\t\t\t\t    MT6797_A72_PHASE_TOPRGU_DEASSERT);\n"
        "\tif (ret) goto postiso_fault;\n"
        "\tpwrap_owned = false;\n"
        "\tspin_lock(&reset_lock);\n"
        "\tif (reset_flags != 1)\n"
        "\t\tret = -EIO;\n"
        "\telse\n"
        "\t\treset_flags = 0;\n"
        "\tspin_unlock(&reset_lock);\n"
        "\tif (ret) { stage = \"reset-guard-clear\"; goto postiso_fault; }\n"
        "\treset_flag_owned = false;\n"
        "\tudelay(240);\n"
        "\tstage = \"sram-readback\";\n"
        "\tmt6797_a72_one_way_checkpoint(stage);\n"
        "\tret = mt6797_a72_one_way_sram_set_verify(cpu);\n"
        "\tif (ret) goto postiso_fault;\n"
        "\tstage = \"psci\";\n"
        "\tmt6797_a72_one_way_checkpoint(stage);\n"
        "\tret = psci_ops.cpu_on(cpu_logical_map(cpu), __pa(secondary_entry));\n"
        "\tmt6797_a72_obs_lifecycle(cpu, MT6797_A72_PHASE_PSCI_MAPPED, ret,\n"
        "\t\t\t\t cpu_logical_map(cpu), __pa(secondary_entry));\n"
        "\tif (ret) goto postiso_fault;\n"
        "\tWRITE_ONCE(mt6797_a72_one_way_psci_accepted, true);\n"
        "\treturn 0;\n\n"
        "rollback:\n"
        "\tif (buck_owned && da9214_a72_diag_compare_update(cpu, true, false,\n"
        "\t\t\t\t\t MT6797_A72_PHASE_ROLLBACK_BUCK_DISABLE))\n"
        "\t\trollback_fault = true;\n"
        "\tif (reset_owned && mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\tMT6797_A72_PHASE_ROLLBACK_SPM_RESET, 0x218,\n"
        "\t\t0x00010133, 0x00010132))\n"
        "\t\trollback_fault = true;\n"
        "\tif (pwrap_owned && mt6797_a72_diag_toprgu_compare_update(cpu,\n"
        "\t\ttrue, false, MT6797_A72_PHASE_ROLLBACK_PWRAP_DEASSERT))\n"
        "\t\trollback_fault = true;\n"
        "\tif (reset_flag_owned) {\n"
        "\t\tspin_lock(&reset_lock);\n"
        "\t\tif (reset_flags != 1)\n"
        "\t\t\trollback_fault = true;\n"
        "\t\telse\n"
        "\t\t\treset_flags = 0;\n"
        "\t\tspin_unlock(&reset_lock);\n"
        "\t}\n"
        "\tmt6797_a72_obs_rollback_terminal(cpu,\n"
        "\t\trollback_fault ? MT6797_A72_ROLLBACK_FAULT_RETAIN :\n"
        "\t\tMT6797_A72_ROLLBACK_ROLLED_BACK);\n"
        "\tmt6797_a72_one_way_marker(rollback_fault ? \"fault-retain-preiso\" :\n"
        "\t\t\t\t\t    \"rolled-back-preiso\", stage, ret);\n"
        "\treturn ret ?: -ECANCELED;\n\n"
        "postiso_fault:\n"
        "\tif (pwrap_owned)\n"
        "\t\tmt6797_a72_diag_toprgu_compare_update(cpu, true, false,\n"
        "\t\t\t\tMT6797_A72_PHASE_TOPRGU_DEASSERT);\n"
        "\tif (reset_flag_owned) {\n"
        "\t\tspin_lock(&reset_lock);\n"
        "\t\tif (reset_flags == 1)\n"
        "\t\t\treset_flags = 0;\n"
        "\t\tspin_unlock(&reset_lock);\n"
        "\t}\n"
        "\tmt6797_a72_obs_rollback_terminal(cpu,\n"
        "\t\tMT6797_A72_ROLLBACK_FAULT_RETAIN);\n"
        "\tmt6797_a72_one_way_marker(\"fault-retain-postiso\", stage, ret);\n"
        "\treturn ret ?: -EIO;\n"
        "}\n\n"
        "int mt6797_a72_one_way_secondary_complete(unsigned int cpu,\n"
        "\t\t\t\t\t\t bool completed)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tif (cpu != 8)\n"
        "\t\treturn 0;\n"
        "\tif (!READ_ONCE(mt6797_a72_one_way_psci_accepted) ||\n"
        "\t    !completed || !cpu_online(8) || cpu_online(9)) {\n"
        "\t\tret = -EIO;\n"
        "\t\tmt6797_a72_obs_rollback_terminal(cpu,\n"
        "\t\t\tMT6797_A72_ROLLBACK_FAULT_RETAIN);\n"
        "\t\tmt6797_a72_one_way_marker(\"fault-retain-postiso\",\n"
        "\t\t\t\t\t    \"secondary\", ret);\n"
        "\t\treturn ret;\n"
        "\t}\n"
        "\tmt6797_a72_one_way_checkpoint(\"dcm\");\n"
        "\tret = mt6797_a72_one_way_dcm_enable(cpu);\n"
        "\tif (ret) {\n"
        "\t\tmt6797_a72_obs_rollback_terminal(cpu,\n"
        "\t\t\tMT6797_A72_ROLLBACK_FAULT_RETAIN);\n"
        "\t\tmt6797_a72_one_way_marker(\"fault-retain-postiso\",\n"
        "\t\t\t\t\t    \"dcm\", ret);\n"
        "\t\treturn ret;\n"
        "\t}\n"
        "\tg_cl2_online |= 1;\n"
        "\tmt6797_a72_one_way_marker(\"cpu8-online-held\",\n"
        "\t\t\t\t\t    \"complete\", 0);\n"
        "\treturn 0;\n"
        "}\n"
        "#endif\n\n",
    )
    replace_once(
        psci,
        "#ifdef CONFIG_MTK_CPU_HOTPLUG_DEBUG_3\n"
        "\tTIMESTAMP_REC(hotplug_ts_rec, TIMESTAMP_FILTER,  cpu, 0, 0, 0);\n"
        "#endif\n\n"
        "\tif ((cpu == 0) || (cpu == 1) || (cpu == 2) || (cpu == 3)) {",
        "#ifdef CONFIG_MTK_CPU_HOTPLUG_DEBUG_3\n"
        "\tTIMESTAMP_REC(hotplug_ts_rec, TIMESTAMP_FILTER,  cpu, 0, 0, 0);\n"
        "#endif\n\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\tif (cpu == 9) {\n"
        "\t\tpr_info(\"one-way: reject CPU9 before A72 action\\n\");\n"
        "\t\terr = -EPERM;\n"
        "\t\tgoto mt6797_a72_one_way_out;\n"
        "\t}\n"
        "\tif (cpu == 8) {\n"
        "\t\terr = mt6797_a72_one_way_boot(cpu);\n"
        "\t\tgoto mt6797_a72_one_way_out;\n"
        "\t}\n"
        "#endif\n\n"
        "\tif ((cpu == 0) || (cpu == 1) || (cpu == 2) || (cpu == 3)) {",
    )
    insert_before(
        psci,
        "#ifdef MTK_IRQ_NEW_DESIGN\n\tgic_clear_primask();\n#endif\n\n\treturn err;\n",
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "mt6797_a72_one_way_out:\n"
        "#endif\n",
    )
    replace_once(
        psci,
        "static int cpu_psci_cpu_disable(unsigned int cpu)\n{\n"
        "\t/* Fail early if we don't have CPU_OFF support */",
        "static int cpu_psci_cpu_disable(unsigned int cpu)\n{\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\tif (cpu == 8 || cpu == 9)\n"
        "\t\treturn -EPERM;\n"
        "#endif\n"
        "\t/* Fail early if we don't have CPU_OFF support */",
    )
    replace_once(
        smp,
        "int __cpu_up(unsigned int cpu, struct task_struct *idle)\n{\n\tint ret;\n",
        "int __cpu_up(unsigned int cpu, struct task_struct *idle)\n{\n"
        "\tint ret;\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\tunsigned long secondary_completed = 0;\n"
        "#endif\n",
    )
    replace_once(
        smp,
        "\t\t#ifdef CONFIG_ARCH_MT6797\n"
        "\t\twait_for_completion_timeout(&cpu_running,\n"
        "\t\t\t\t\t    msecs_to_jiffies(3000));\n"
        "\t\t#else",
        "\t\t#ifdef CONFIG_ARCH_MT6797\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\t\tsecondary_completed =\n"
        "#endif\n"
        "\t\t\twait_for_completion_timeout(&cpu_running,\n"
        "\t\t\t\t\t    msecs_to_jiffies(3000));\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\t\tif (cpu == 8)\n"
        "\t\t\tret = mt6797_a72_one_way_secondary_complete(cpu,\n"
        "\t\t\t\tsecondary_completed && cpu_online(cpu));\n"
        "#endif\n"
        "\t\t#else",
    )
    replace_once(
        smp,
        "\t\tif (!cpu_online(cpu)) {\n"
        "\t\t\tpr_crit(\"CPU%u: failed to come online\\n\", cpu);\n"
        "\t\t\t#ifdef CONFIG_ARCH_MT6797\n"
        "\t\t\tBUG_ON(1);\n"
        "\t\t\t#endif\n"
        "\t\t\tret = -EIO;\n"
        "\t\t}",
        "\t\tif (!cpu_online(cpu)) {\n"
        "\t\t\tpr_crit(\"CPU%u: failed to come online\\n\", cpu);\n"
        "\t\t\t#ifdef CONFIG_ARCH_MT6797\n"
        "#ifdef CONFIG_MTK_A72_ONE_WAY_CPU8\n"
        "\t\t\tif (cpu != 8)\n"
        "#endif\n"
        "\t\t\t\tBUG_ON(1);\n"
        "\t\t\t#endif\n"
        "\t\t\tret = -EIO;\n"
        "\t\t}",
    )


STEPS = {
    "watchdog": watchdog_step,
    "helpers": helpers_step,
    "orchestrator": orchestrator_step,
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
