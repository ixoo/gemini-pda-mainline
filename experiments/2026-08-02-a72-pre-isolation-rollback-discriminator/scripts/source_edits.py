#!/usr/bin/env python3
"""Apply deterministic logical edits to the pinned, patched Gemian source.

This script is executed only on Buildbox.  It refuses source drift by requiring
every replacement anchor exactly once; the caller commits each named step and
uses git format-patch there.
"""

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


def abi_step(source: Path) -> None:
    header = source / "include/linux/mt6797_a72_transition_observer.h"
    core = (
        source
        / "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c"
    )

    replace_once(
        header,
        "\tMT6797_A72_PHASE_BUCK_ENABLE_SETTLED,\n"
        "\tMT6797_A72_PHASE_SPM_ISOLATION_CLEAR,",
        "\tMT6797_A72_PHASE_BUCK_ENABLE_SETTLED,\n"
        "\tMT6797_A72_PHASE_PREISO_INJECT_STOP,\n"
        "\tMT6797_A72_PHASE_ROLLBACK_BUCK_DISABLE,\n"
        "\tMT6797_A72_PHASE_ROLLBACK_SPM_RESET,\n"
        "\tMT6797_A72_PHASE_ROLLBACK_PWRAP_DEASSERT,\n"
        "\tMT6797_A72_PHASE_ROLLBACK_FINAL,\n"
        "\tMT6797_A72_PHASE_SPM_ISOLATION_CLEAR,",
    )
    insert_before(
        header,
        "enum mt6797_a72_obs_event {\n",
        "enum mt6797_a72_rollback_disposition {\n"
        "\tMT6797_A72_ROLLBACK_ROLLED_BACK = 1,\n"
        "\tMT6797_A72_ROLLBACK_FAULT_RETAIN,\n"
        "\tMT6797_A72_ROLLBACK_REJECTED_PRESTATE,\n"
        "};\n\n",
    )
    insert_before(
        header,
        "\nint da9214_a72_obs_snapshot(unsigned int cpu, u16 phase);\n",
        "\nvoid mt6797_a72_obs_rollback_terminal(unsigned int cpu,\n"
        "\t\tenum mt6797_a72_rollback_disposition disposition);\n",
    )

    replace_once(
        core,
        "\tMT6797_A72_OBS_FROZEN_OVERFLOW,\n};",
        "\tMT6797_A72_OBS_FROZEN_OVERFLOW,\n"
        "\tMT6797_A72_OBS_ROLLED_BACK,\n"
        "\tMT6797_A72_OBS_FAULT_RETAIN,\n"
        "\tMT6797_A72_OBS_REJECTED_PRESTATE,\n};",
    )
    replace_once(
        core,
        "\t} else if (mt6797_a72_obs_state == MT6797_A72_OBS_CAPTURE_UP) {\n"
        "\t\tretain = true;\n"
        "\t\tif (record->header.transaction !=",
        "\t} else if (mt6797_a72_obs_state == MT6797_A72_OBS_CAPTURE_UP) {\n"
        "\t\tretain = true;\n"
        "\t\tif (mt6797_a72_obs_is_boundary(record,\n"
        "\t\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL)) {\n"
        "\t\t\tswitch (record->payload.lifecycle.result) {\n"
        "\t\t\tcase MT6797_A72_ROLLBACK_ROLLED_BACK:\n"
        "\t\t\t\tnext_state = MT6797_A72_OBS_ROLLED_BACK;\n"
        "\t\t\t\tbreak;\n"
        "\t\t\tcase MT6797_A72_ROLLBACK_FAULT_RETAIN:\n"
        "\t\t\t\tnext_state = MT6797_A72_OBS_FAULT_RETAIN;\n"
        "\t\t\t\tbreak;\n"
        "\t\t\tcase MT6797_A72_ROLLBACK_REJECTED_PRESTATE:\n"
        "\t\t\t\tnext_state = MT6797_A72_OBS_REJECTED_PRESTATE;\n"
        "\t\t\t\tbreak;\n"
        "\t\t\tdefault:\n"
        "\t\t\t\tnext_state = MT6797_A72_OBS_FROZEN_PROTOCOL;\n"
        "\t\t\t}\n"
        "\t\t} else if (record->header.transaction !=",
    )
    insert_before(
        core,
        "static const char *mt6797_a72_obs_state_name(u16 state)\n",
        "void mt6797_a72_obs_rollback_terminal(unsigned int cpu,\n"
        "\t\tenum mt6797_a72_rollback_disposition disposition)\n"
        "{\n"
        "\tmt6797_a72_obs_lifecycle(cpu, MT6797_A72_PHASE_ROLLBACK_FINAL,\n"
        "\t\t\t\tdisposition, 0, 0);\n"
        "}\n\n",
    )
    replace_once(
        core,
        "\tcase MT6797_A72_OBS_FROZEN_OVERFLOW: return \"frozen-overflow\";\n",
        "\tcase MT6797_A72_OBS_FROZEN_OVERFLOW: return \"frozen-overflow\";\n"
        "\tcase MT6797_A72_OBS_ROLLED_BACK: return \"rolled-back\";\n"
        "\tcase MT6797_A72_OBS_FAULT_RETAIN: return \"fault-retain\";\n"
        "\tcase MT6797_A72_OBS_REJECTED_PRESTATE:\n"
        "\t\treturn \"rejected-prestate\";\n",
    )
    replace_once(
        core,
        "abi=mt6797-a72-transition-observer-v2 state=%s",
        "abi=mt6797-a72-transition-observer-v3 state=%s",
    )


def owner_step(source: Path) -> None:
    header = source / "include/linux/mt6797_a72_transition_observer.h"
    da9214 = source / "drivers/misc/mediatek/power/mt6797/da9214.c"
    spm = source / "drivers/misc/mediatek/base/power/spm_v2/mt_spm.c"
    wdt = source / "drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c"
    idvfs = source / "drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c"
    dcm = source / "drivers/misc/mediatek/base/power/mt6797/mt_dcm.c"
    clock = source / "drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c"

    insert_before(
        header,
        "\n#endif\n",
        "\nint da9214_a72_diag_compare_update(unsigned int cpu, bool expected,\n"
        "\t\tbool requested, u16 phase);\n"
        "int mt6797_a72_diag_spm_compare_update(unsigned int cpu, u16 phase,\n"
        "\t\tu32 offset, u32 expected, u32 requested);\n"
        "int mt6797_a72_diag_toprgu_compare_update(unsigned int cpu,\n"
        "\t\tbool expected, bool requested, u16 phase);\n"
        "bool mt6797_a72_diag_secure_zero(unsigned int cpu, u16 phase);\n"
        "bool mt6797_a72_diag_dcm_zero(unsigned int cpu, u16 phase);\n"
        "int mt6797_a72_diag_clock_capture(unsigned int cpu, u16 phase,\n"
        "\t\tstruct mt6797_a72_obs_clock *snapshot);\n",
    )

    insert_before(
        da9214,
        "#endif\n\n/*\n *   [Read / Write Function]\n */",
        "int da9214_a72_diag_compare_update(unsigned int cpu, bool expected,\n"
        "\t\tbool requested, u16 phase)\n"
        "{\n"
        "\tstruct mt6797_a72_obs_da9214 snapshot = { };\n"
        "\tunsigned char buck = 0;\n"
        "\tint ret = -ENODEV;\n\n"
        "\tif (!new_client)\n"
        "\t\tgoto record;\n"
        "\tmutex_lock(&da9214_i2c_access);\n"
        "\tret = da9214_a72_read_locked(DA9214_A72_REG_PAGE,\n"
        "\t\t\t\t     &snapshot.page_before);\n"
        "\tif (ret < 0)\n"
        "\t\tgoto unlock;\n"
        "\tsnapshot.valid |= DA9214_A72_VALID_PAGE_BEFORE;\n"
        "\tif (snapshot.page_before != 0x80) {\n"
        "\t\tret = -EINVAL;\n"
        "\t\tgoto unlock;\n"
        "\t}\n"
        "\tsnapshot.page_selected = snapshot.page_before;\n"
        "\tsnapshot.valid |= DA9214_A72_VALID_PAGE_SELECTED;\n"
        "\tret = da9214_a72_read_locked(DA9214_A72_REG_BUCKB, &buck);\n"
        "\tif (ret < 0)\n"
        "\t\tgoto unlock;\n"
        "\tsnapshot.buck_enable_before = buck;\n"
        "\tsnapshot.valid |= DA9214_A72_VALID_BUCK_BEFORE;\n"
        "\tret = da9214_a72_read_locked(DA9214_A72_REG_BUCKB_VSEL,\n"
        "\t\t\t\t     &snapshot.buck_vsel);\n"
        "\tif (ret < 0)\n"
        "\t\tgoto unlock;\n"
        "\tsnapshot.valid |= DA9214_A72_VALID_VSEL;\n"
        "\tif (!!(buck & 1) != expected || snapshot.buck_vsel != 0x46) {\n"
        "\t\tret = -EINVAL;\n"
        "\t\tgoto unlock;\n"
        "\t}\n"
        "\tif (requested != expected) {\n"
        "\t\tret = da9214_a72_write_locked(DA9214_A72_REG_BUCKB,\n"
        "\t\t\t\t\t      (buck & ~1) | requested);\n"
        "\t\tif (ret < 0)\n"
        "\t\t\tgoto unlock;\n"
        "\t}\n"
        "\tret = da9214_a72_read_locked(DA9214_A72_REG_BUCKB, &buck);\n"
        "\tif (ret < 0)\n"
        "\t\tgoto unlock;\n"
        "\tsnapshot.buck_enable_after = buck;\n"
        "\tsnapshot.valid |= DA9214_A72_VALID_BUCK_AFTER;\n"
        "\tret = da9214_a72_read_locked(DA9214_A72_REG_BUCKB_VSEL,\n"
        "\t\t\t\t     &snapshot.buck_vsel);\n"
        "\tif (ret < 0)\n"
        "\t\tgoto unlock;\n"
        "\tret = da9214_a72_read_locked(DA9214_A72_REG_PAGE,\n"
        "\t\t\t\t     &snapshot.page_after);\n"
        "\tif (ret < 0)\n"
        "\t\tgoto unlock;\n"
        "\tsnapshot.valid |= DA9214_A72_VALID_PAGE_VERIFY;\n"
        "\tif (!!(buck & 1) != requested || snapshot.buck_vsel != 0x46 ||\n"
        "\t    snapshot.page_after != 0x80)\n"
        "\t\tret = -EIO;\n"
        "\telse\n"
        "\t\tret = 0;\n"
        "unlock:\n"
        "\tmutex_unlock(&da9214_i2c_access);\n"
        "record:\n"
        "\tsnapshot.status = ret;\n"
        "\tmt6797_a72_obs_da9214(cpu, phase, &snapshot);\n"
        "\treturn ret;\n"
        "}\n\n",
    )

    insert_before(
        spm,
        "#endif\n\nvoid unmask_edge_trig_irqs_for_cirq(void)",
        "int mt6797_a72_diag_spm_compare_update(unsigned int cpu, u16 phase,\n"
        "\t\tu32 offset, u32 expected, u32 requested)\n"
        "{\n"
        "\tstruct mt6797_a72_obs_mutation mutation = {\n"
        "\t\t.address = MT6797_A72_SPM_PHYS + offset,\n"
        "\t\t.mask = ~0U,\n"
        "\t\t.requested = requested,\n"
        "\t};\n"
        "\tvoid __iomem *base;\n"
        "\tunsigned long flags;\n"
        "\tbool temporary;\n"
        "\tint ret = 0;\n\n"
        "\tif (offset != 0x218 && offset != 0x290)\n"
        "\t\treturn -EINVAL;\n"
        "\tbase = mt6797_a72_obs_spm_base(&temporary);\n"
        "\tif (!base) {\n"
        "\t\tmutation.status = -ENOMEM;\n"
        "\t\tmt6797_a72_obs_mutation(cpu, phase, &mutation);\n"
        "\t\treturn -ENOMEM;\n"
        "\t}\n"
        "\tspin_lock_irqsave(&__spm_lock, flags);\n"
        "\tmutation.before = readl_relaxed(base + offset);\n"
        "\tif (mutation.before != expected) {\n"
        "\t\tret = -EINVAL;\n"
        "\t\tmutation.after = mutation.before;\n"
        "\t} else {\n"
        "\t\tif (requested != expected)\n"
        "\t\t\twritel_relaxed(requested, base + offset);\n"
        "\t\tmutation.after = readl_relaxed(base + offset);\n"
        "\t\tif (mutation.after != requested)\n"
        "\t\t\tret = -EIO;\n"
        "\t}\n"
        "\tspin_unlock_irqrestore(&__spm_lock, flags);\n"
        "\tif (temporary)\n"
        "\t\tiounmap(base);\n"
        "\tmutation.status = ret;\n"
        "\tmt6797_a72_obs_mutation(cpu, phase, &mutation);\n"
        "\treturn ret;\n"
        "}\n",
    )

    insert_before(
        wdt,
        "int mtk_wdt_swsysret_config(int bit, int set_value)\n{\n",
        "#ifdef CONFIG_MTK_A72_TRANSITION_OBSERVER\n"
        "int mt6797_a72_diag_toprgu_compare_update(unsigned int cpu,\n"
        "\t\tbool expected, bool requested, u16 phase)\n"
        "{\n"
        "\tstruct mt6797_a72_obs_toprgu snapshot = {\n"
        "\t\t.mask = MTK_WDT_SWSYS_RST_PWRAP_SPI_CTL_RST,\n"
        "\t};\n"
        "\tunsigned int value;\n"
        "\tint ret = 0;\n\n"
        "\tspin_lock(&rgu_reg_operation_spinlock);\n"
        "\tvalue = __raw_readl(MTK_WDT_SWSYSRST);\n"
        "\tsnapshot.before = value;\n"
        "\tif (!!(value & snapshot.mask) != expected) {\n"
        "\t\tret = -EINVAL;\n"
        "\t\tsnapshot.requested = value;\n"
        "\t\tsnapshot.after = value;\n"
        "\t} else {\n"
        "\t\tvalue |= MTK_WDT_SWSYS_RST_KEY;\n"
        "\t\tif (requested)\n"
        "\t\t\tvalue |= snapshot.mask;\n"
        "\t\telse\n"
        "\t\t\tvalue &= ~snapshot.mask;\n"
        "\t\tsnapshot.requested = value;\n"
        "\t\tif (requested != expected)\n"
        "\t\t\tmt_reg_sync_writel(value, MTK_WDT_SWSYSRST);\n"
        "\t\tsnapshot.after = __raw_readl(MTK_WDT_SWSYSRST);\n"
        "\t\tif (!!(snapshot.after & snapshot.mask) != requested)\n"
        "\t\t\tret = -EIO;\n"
        "\t}\n"
        "\tspin_unlock(&rgu_reg_operation_spinlock);\n"
        "\tsnapshot.status = ret;\n"
        "\tmt6797_a72_obs_toprgu(cpu, phase, &snapshot);\n"
        "\treturn ret;\n"
        "}\n"
        "#endif\n\n",
    )

    insert_before(
        idvfs,
        "#endif\n\n/* 0x11017000 0x1000, i2c idvfsapb ctrl reg */",
        "bool mt6797_a72_diag_secure_zero(unsigned int cpu, u16 phase)\n"
        "{\n"
        "\tstruct mt6797_a72_obs_secure snapshot = { };\n"
        "\tbool zero = true;\n"
        "\tunsigned int i;\n\n"
        "\tfor (i = 0; i < ARRAY_SIZE(mt6797_a72_secure_registers); i++) {\n"
        "\t\tsnapshot.values[i] = (u32)SEC_BIGIDVFS_READ(\n"
        "\t\t\tmt6797_a72_secure_registers[i]);\n"
        "\t\tsnapshot.valid |= BIT(i);\n"
        "\t\tzero &= snapshot.values[i] == 0;\n"
        "\t}\n"
        "\tsnapshot.sentinel_after =\n"
        "\t\t(u32)SEC_BIGIDVFS_READ(mt6797_a72_secure_registers[0]);\n"
        "\tsnapshot.stable =\n"
        "\t\tsnapshot.sentinel_after == snapshot.values[0];\n"
        "\tmt6797_a72_obs_secure(cpu, phase, &snapshot);\n"
        "\treturn zero && snapshot.stable;\n"
        "}\n",
    )

    insert_before(
        dcm,
        "#endif\n\nint dcm_mcusys_little(ENUM_MCUSYS_DCM on)",
        "bool mt6797_a72_diag_dcm_zero(unsigned int cpu, u16 phase)\n"
        "{\n"
        "\tstruct mt6797_a72_obs_dcm snapshot = {\n"
        "\t\t.mask = MCUCFG_SYNC_DCM_MP2_MASK,\n"
        "\t};\n"
        "\tunsigned long flags;\n\n"
        "\tspin_lock_irqsave(&mt6797_a72_obs_mp2_dcm_lock, flags);\n"
        "\tsnapshot.before = reg_read(MCUCFG_SYNC_DCM_MP2_CONFIG);\n"
        "\tsnapshot.toggle = snapshot.before;\n"
        "\tsnapshot.final = snapshot.before;\n"
        "\tspin_unlock_irqrestore(&mt6797_a72_obs_mp2_dcm_lock, flags);\n"
        "\tmt6797_a72_obs_dcm(cpu, phase, &snapshot);\n"
        "\treturn !(snapshot.before & snapshot.mask);\n"
        "}\n",
    )

    insert_before(
        clock,
        "#endif\n\n/*****************************************************************************/\n"
        "/* Function */",
        "int mt6797_a72_diag_clock_capture(unsigned int cpu, u16 phase,\n"
        "\t\tstruct mt6797_a72_obs_clock *snapshot)\n"
        "{\n"
        "\tunsigned long flags;\n\n"
        "\tif (!snapshot)\n"
        "\t\treturn -EINVAL;\n"
        "\t*snapshot = (struct mt6797_a72_obs_clock) { .status = -ENODEV };\n"
        "\tif (!spin_trylock_irqsave(&g_mt6797_0x1001AXXX_lock, flags)) {\n"
        "\t\tsnapshot->status = -EBUSY;\n"
        "\t\tgoto record;\n"
        "\t}\n"
        "\tsnapshot->semaphore |= BIT(2);\n"
        "\tif (!g_mcumixed_base || !g_reg_sema3_m0 ||\n"
        "\t    !g_reg_cspm_poweron_en)\n"
        "\t\tgoto unlock;\n"
        "\tsnapshot->semaphore |= BIT(3);\n"
        "\ths_write32(g_reg_cspm_poweron_en, 0x0b160001);\n"
        "\ths_write32(g_reg_sema3_m0, 0x1);\n"
        "\tif (!(hs_read32(g_reg_sema3_m0) & 0x1)) {\n"
        "\t\tsnapshot->status = -EBUSY;\n"
        "\t\tgoto unlock;\n"
        "\t}\n"
        "\tsnapshot->semaphore |= BIT(0);\n"
        "\tndelay(200);\n"
        "\tsnapshot->pll_con1 = readl(g_mcumixed_base +\n"
        "\t\t\t\t\t MT6797_A72_CLOCK_PLL_CON1);\n"
        "\tsnapshot->muxsel = readl(g_mcumixed_base +\n"
        "\t\t\t\t       MT6797_A72_CLOCK_MUXSEL);\n"
        "\tsnapshot->ckdiv = readl(g_mcumixed_base +\n"
        "\t\t\t\t      MT6797_A72_CLOCK_CKDIV);\n"
        "\tsnapshot->status = 0;\n"
        "\ths_write32(g_reg_sema3_m0, 0x1);\n"
        "\tif (!(hs_read32(g_reg_sema3_m0) & 0x1))\n"
        "\t\tsnapshot->semaphore |= BIT(1);\n"
        "\telse\n"
        "\t\tsnapshot->status = -EIO;\n"
        "unlock:\n"
        "\tspin_unlock_irqrestore(&g_mt6797_0x1001AXXX_lock, flags);\n"
        "record:\n"
        "\tmt6797_a72_obs_clock(cpu, phase, snapshot);\n"
        "\treturn snapshot->status;\n"
        "}\n",
    )


def orchestrator_step(source: Path) -> None:
    psci = source / "arch/arm64/kernel/psci.c"
    kconfig = source / "drivers/misc/mediatek/base/power/Kconfig"

    replace_once(
        psci,
        "#include <linux/arm-smccc.h>\n",
        "#include <linux/arm-smccc.h>\n#include <linux/atomic.h>\n#include <linux/cpu.h>\n",
    )
    replace_once(
        kconfig,
        "\t  aid for one pinned downstream kernel and is not an A72 power driver.\n",
        "\t  aid for one pinned downstream kernel and is not an A72 power driver.\n\n"
        "config MTK_A72_PREISO_ROLLBACK_DISCRIMINATOR\n"
        "\tbool \"MT6797 CPU8 pre-isolation rollback discriminator\"\n"
        "\tdepends on MTK_A72_TRANSITION_OBSERVER\n"
        "\tdefault n\n"
        "\thelp\n"
        "\t  Run one compiled CPU8-only diagnostic attempt that stops before\n"
        "\t  external-isolation clear and rolls back only exactly owned state.\n"
        "\t  This option has no userspace trigger and is not for deployment.\n",
    )

    insert_before(
        psci,
        "static int cpu_power_on_buck(unsigned int cpu, bool hotplug)\n",
        "#ifdef CONFIG_MTK_A72_PREISO_ROLLBACK_DISCRIMINATOR\n"
        "static atomic_t mt6797_a72_preiso_attempted = ATOMIC_INIT(0);\n\n"
        "static int mt6797_a72_preiso_rollback(unsigned int cpu)\n"
        "{\n"
        "\tbool buck_owned = false;\n"
        "\tbool pwrap_owned = false;\n"
        "\tbool reset_owned = false;\n"
        "\tbool reset_flag_owned = false;\n"
        "\tbool fault = false;\n"
        "\tbool prestate_bad = false;\n"
        "\tstruct mt6797_a72_obs_clock entry_clock;\n"
        "\tstruct mt6797_a72_obs_clock final_clock;\n"
        "\tint ret;\n\n"
        "\tif (cpu != 8 || atomic_xchg(&mt6797_a72_preiso_attempted, 1))\n"
        "\t\treturn -EALREADY;\n"
        "\tprestate_bad |= g_cl2_online || cpu_online(8) || cpu_online(9);\n"
        "\tret = mt6797_a72_diag_clock_capture(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_POWER_ON_PRE, &entry_clock);\n"
        "\tprestate_bad |= !!ret;\n"
        "\tprestate_bad |= !mt6797_a72_diag_secure_zero(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_POWER_ON_PRE);\n"
        "\tprestate_bad |= !mt6797_a72_diag_dcm_zero(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_POWER_ON_PRE);\n"
        "\tret = da9214_a72_diag_compare_update(cpu, false, false,\n"
        "\t\t\tMT6797_A72_PHASE_POWER_ON_PRE);\n"
        "\tprestate_bad |= !!ret;\n"
        "\tret = mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_POWER_ON_PRE, 0x218,\n"
        "\t\t\t0x00010132, 0x00010132);\n"
        "\tprestate_bad |= !!ret;\n"
        "\tret = mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_POWER_ON_PRE, 0x290, 0x2, 0x2);\n"
        "\tprestate_bad |= !!ret;\n"
        "\tret = mt6797_a72_diag_toprgu_compare_update(cpu, false, false,\n"
        "\t\t\tMT6797_A72_PHASE_POWER_ON_PRE);\n"
        "\tprestate_bad |= !!ret;\n\n"
        "\tspin_lock(&reset_lock);\n"
        "\tprestate_bad |= reset_flags != 0;\n"
        "\tif (!prestate_bad) {\n"
        "\t\treset_flags = 1;\n"
        "\t\treset_flag_owned = true;\n"
        "\t}\n"
        "\tspin_unlock(&reset_lock);\n\n"
        "\tif (prestate_bad)\n"
        "\t\tgoto rejected;\n\n"
        "\tret = mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_SPM_RESET_RELEASE, 0x218,\n"
        "\t\t\t0x00010132, 0x00010133);\n"
        "\tif (ret) {\n"
        "\t\tfault = true;\n"
        "\t\tgoto rollback;\n"
        "\t}\n"
        "\treset_owned = true;\n"
        "\tret = mt6797_a72_diag_toprgu_compare_update(cpu, false, true,\n"
        "\t\t\tMT6797_A72_PHASE_TOPRGU_ASSERT);\n"
        "\tif (ret) {\n"
        "\t\tfault = true;\n"
        "\t\tgoto rollback;\n"
        "\t}\n"
        "\tpwrap_owned = true;\n"
        "\tret = da9214_a72_diag_compare_update(cpu, false, true,\n"
        "\t\t\tMT6797_A72_PHASE_BUCK_ENABLE);\n"
        "\tif (ret) {\n"
        "\t\tfault = true;\n"
        "\t\tgoto rollback;\n"
        "\t}\n"
        "\tbuck_owned = true;\n"
        "\tudelay(1000);\n"
        "\tret = da9214_a72_diag_compare_update(cpu, true, true,\n"
        "\t\t\tMT6797_A72_PHASE_BUCK_ENABLE_SETTLED);\n"
        "\tif (ret) {\n"
        "\t\tfault = true;\n"
        "\t\tgoto rollback;\n"
        "\t}\n"
        "\tmt6797_a72_obs_lifecycle(cpu, MT6797_A72_PHASE_PREISO_INJECT_STOP,\n"
        "\t\t\t\t 0, 0, 0);\n\n"
        "rollback:\n"
        "\tif (buck_owned && da9214_a72_diag_compare_update(cpu, true, false,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_BUCK_DISABLE))\n"
        "\t\tfault = true;\n"
        "\tif (reset_owned &&\n"
        "\t    (mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\tMT6797_A72_PHASE_ROLLBACK_SPM_RESET, 0x290, 0x2, 0x2) ||\n"
        "\t     mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\tMT6797_A72_PHASE_ROLLBACK_SPM_RESET, 0x218,\n"
        "\t\t0x00010133, 0x00010132)))\n"
        "\t\tfault = true;\n"
        "\tif (pwrap_owned &&\n"
        "\t    mt6797_a72_diag_toprgu_compare_update(cpu, true, false,\n"
        "\t\tMT6797_A72_PHASE_ROLLBACK_PWRAP_DEASSERT))\n"
        "\t\tfault = true;\n"
        "\tif (reset_flag_owned) {\n"
        "\t\tspin_lock(&reset_lock);\n"
        "\t\tif (reset_flags != 1)\n"
        "\t\t\tfault = true;\n"
        "\t\telse\n"
        "\t\t\treset_flags = 0;\n"
        "\t\tspin_unlock(&reset_lock);\n"
        "\t}\n"
        "\tret = da9214_a72_diag_compare_update(cpu, false, false,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL);\n"
        "\tfault |= !!ret;\n"
        "\tret = mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL, 0x218,\n"
        "\t\t\t0x00010132, 0x00010132);\n"
        "\tfault |= !!ret;\n"
        "\tret = mt6797_a72_diag_spm_compare_update(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL, 0x290, 0x2, 0x2);\n"
        "\tfault |= !!ret;\n"
        "\tret = mt6797_a72_diag_toprgu_compare_update(cpu, false, false,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL);\n"
        "\tfault |= !!ret;\n"
        "\tfault |= !mt6797_a72_diag_secure_zero(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL);\n"
        "\tfault |= !mt6797_a72_diag_dcm_zero(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL);\n"
        "\tret = mt6797_a72_diag_clock_capture(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL, &final_clock);\n"
        "\tfault |= !!ret;\n"
        "\tif (!ret) {\n"
        "\t\tfault |= entry_clock.pll_con1 != final_clock.pll_con1;\n"
        "\t\tfault |= entry_clock.muxsel != final_clock.muxsel;\n"
        "\t\tfault |= entry_clock.ckdiv != final_clock.ckdiv;\n"
        "\t}\n"
        "\tfault |= g_cl2_online || cpu_online(8) || cpu_online(9);\n"
        "\tmt6797_a72_obs_fixed_snapshot(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL);\n"
        "\tmt6797_a72_obs_rollback_terminal(cpu,\n"
        "\t\tfault ? MT6797_A72_ROLLBACK_FAULT_RETAIN :\n"
        "\t\t\tMT6797_A72_ROLLBACK_ROLLED_BACK);\n"
        "\treturn -ECANCELED;\n\n"
        "rejected:\n"
        "\tmt6797_a72_obs_fixed_snapshot(cpu,\n"
        "\t\t\tMT6797_A72_PHASE_ROLLBACK_FINAL);\n"
        "\tmt6797_a72_obs_rollback_terminal(cpu,\n"
        "\t\tMT6797_A72_ROLLBACK_REJECTED_PRESTATE);\n"
        "\treturn -ECANCELED;\n"
        "}\n"
        "#endif\n\n",
    )

    replace_once(
        psci,
        "#ifdef CONFIG_MTK_A72_TRANSITION_OBSERVER\n\tint idvfs_ret;\n#endif\n",
        "#ifdef CONFIG_MTK_A72_TRANSITION_OBSERVER\n\tint idvfs_ret;\n#endif\n"
        "#ifdef CONFIG_MTK_A72_PREISO_ROLLBACK_DISCRIMINATOR\n"
        "\tint buck_ret;\n"
        "#endif\n",
    )
    replace_once(
        psci,
        "\t} else if ((cpu == 8) || (cpu == 9)) {\n"
        "\t\tif (bypass_boot > 0) {",
        "\t} else if ((cpu == 8) || (cpu == 9)) {\n"
        "#ifdef CONFIG_MTK_A72_PREISO_ROLLBACK_DISCRIMINATOR\n"
        "\t\tif (cpu == 9) {\n"
        "\t\t\terr = -EPERM;\n"
        "\t\t\tgoto mt6797_a72_boot_out;\n"
        "\t\t}\n"
        "\t\tif (bypass_boot > 0) {\n"
        "\t\t\terr = -EPERM;\n"
        "\t\t\tgoto mt6797_a72_boot_out;\n"
        "\t\t}\n"
        "#endif\n"
        "\t\tif (bypass_boot > 0) {",
    )
    replace_once(
        psci,
        "#ifdef CONFIG_CL2_BUCK_CTRL\n"
        "\t\t\t\tcpu_power_on_buck(cpu, 1);\n"
        "#endif\n"
        "\t\t\t}",
        "#ifdef CONFIG_CL2_BUCK_CTRL\n"
        "#ifdef CONFIG_MTK_A72_PREISO_ROLLBACK_DISCRIMINATOR\n"
        "\t\t\t\tbuck_ret = mt6797_a72_preiso_rollback(cpu);\n"
        "\t\t\t\tif (buck_ret) {\n"
        "\t\t\t\t\terr = buck_ret;\n"
        "\t\t\t\t\tgoto mt6797_a72_boot_out;\n"
        "\t\t\t\t}\n"
        "#else\n"
        "\t\t\t\tcpu_power_on_buck(cpu, 1);\n"
        "#endif\n"
        "#endif\n"
        "\t\t\t}",
    )
    insert_before(
        psci,
        "#ifdef MTK_IRQ_NEW_DESIGN\n\tgic_clear_primask();\n#endif\n\n\treturn err;\n",
        "#ifdef CONFIG_MTK_A72_PREISO_ROLLBACK_DISCRIMINATOR\n"
        "mt6797_a72_boot_out:\n"
        "#endif\n",
    )


STEPS = {
    "abi": abi_step,
    "owners": owner_step,
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
