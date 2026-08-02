#!/usr/bin/env python3
"""Prepare the owner-effect gate in a source tree with recorder patch 6."""

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one exact source fragment, found {count}")
    path.write_text(text.replace(old, new, 1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    root = parser.parse_args().source_root.resolve()

    psci = root / "arch/arm64/kernel/psci.c"
    replace_once(
        psci,
        """static void mt6797_a72_obs_fixed_snapshot(unsigned int cpu, u16 phase)
{
\tda9214_a72_obs_snapshot(cpu, phase);
""",
        """static void mt6797_a72_obs_fixed_snapshot(unsigned int cpu, u16 phase)
{
\tif (!mt6797_a72_obs_accepts_sampling(cpu))
\t\treturn;

\tda9214_a72_obs_snapshot(cpu, phase);
""",
        "composite pure-snapshot guard",
    )
    replace_once(
        psci,
        """#ifdef CONFIG_MTK_A72_TRANSITION_OBSERVER
\t\tda9214_a72_obs_buckb_config(cpu, true,
\t\t\t\t\t    MT6797_A72_PHASE_BUCK_ENABLE);
#else
\t\tBUG_ON(da9214_config_interface(0x0, 0x0, 0xF, 0) < 0);
\t\tBUG_ON(da9214_config_interface(0x5E, 0x1, 0x1, 0) < 0);
#endif
""",
        """#ifdef CONFIG_MTK_A72_TRANSITION_OBSERVER
\t\tif (mt6797_a72_obs_accepts_sampling(cpu)) {
\t\t\tda9214_a72_obs_buckb_config(cpu, true,
\t\t\t\t\t    MT6797_A72_PHASE_BUCK_ENABLE);
\t\t} else {
\t\t\tda9214_config_interface(0x0, 0x0, 0xF, 0);
\t\t\tda9214_config_interface(0x5E, 0x1, 0x1, 0);
\t\t}
#else
\t\tBUG_ON(da9214_config_interface(0x0, 0x0, 0xF, 0) < 0);
\t\tBUG_ON(da9214_config_interface(0x5E, 0x1, 0x1, 0) < 0);
#endif
""",
        "BUCKB-enable vendor fallback",
    )
    replace_once(
        psci,
        """#ifdef CONFIG_MTK_A72_TRANSITION_OBSERVER
\t\tda9214_a72_obs_snapshot(cpu,
\t\t\t\t\tMT6797_A72_PHASE_BUCK_ENABLE_SETTLED);
#endif
""",
        """#ifdef CONFIG_MTK_A72_TRANSITION_OBSERVER
\t\tif (mt6797_a72_obs_accepts_sampling(cpu))
\t\t\tda9214_a72_obs_snapshot(cpu,
\t\t\t\t\tMT6797_A72_PHASE_BUCK_ENABLE_SETTLED);
#endif
""",
        "settled-buck pure-snapshot guard",
    )
    replace_once(
        psci,
        """\tret = da9214_a72_obs_buckb_config(cpu, false,
\t\t\t\t\t  MT6797_A72_PHASE_BUCK_DISABLE);
\tsmc_ret = BigiDVFSSRAMLDODisable();
""",
        """\tif (mt6797_a72_obs_accepts_sampling(cpu)) {
\t\tret = da9214_a72_obs_buckb_config(cpu, false,
\t\t\t\t\t  MT6797_A72_PHASE_BUCK_DISABLE);
\t} else {
\t\tret = da9214_config_interface(0x0, 0x0, 0xF, 0);
\t\tret = da9214_config_interface(0x5E, 0x0, 0x1, 0);
\t}
\tsmc_ret = BigiDVFSSRAMLDODisable();
""",
        "BUCKB-disable vendor fallback",
    )

    da9214 = root / "drivers/misc/mediatek/power/mt6797/da9214.c"
    replace_once(
        da9214,
        """\tunsigned char selected = 0;
\tint ret;

\tif (!new_client) {
""",
        """\tunsigned char selected = 0;
\tint ret;

\tif (!mt6797_a72_obs_accepts_sampling(cpu))
\t\treturn 0;
\tif (!new_client) {
""",
        "DA9214 pure-snapshot entry guard",
    )

    spm = root / "drivers/misc/mediatek/base/power/spm_v2/mt_spm.c"
    replace_once(
        spm,
        """\tbool temporary;
\tunsigned int i;

\tbase = mt6797_a72_obs_spm_base(&temporary);
""",
        """\tbool temporary;
\tunsigned int i;

\tif (!mt6797_a72_obs_accepts_sampling(cpu))
\t\treturn;
\tbase = mt6797_a72_obs_spm_base(&temporary);
""",
        "SPM pure-snapshot entry guard",
    )
    replace_once(
        spm,
        """\tbool temporary;

\tbase = mt6797_a72_obs_spm_base(&temporary);
""",
        """\tbool temporary;

\tif (!mt6797_a72_obs_accepts_sampling(cpu))
\t\treturn false;
\tbase = mt6797_a72_obs_spm_base(&temporary);
""",
        "SPM real-mutation fallback gate",
    )

    secure = root / "drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c"
    replace_once(
        secure,
        """\tstruct mt6797_a72_obs_secure snapshot = { };
\tunsigned int i;

\tfor (i = 0; i < ARRAY_SIZE(mt6797_a72_secure_registers); i++) {
""",
        """\tstruct mt6797_a72_obs_secure snapshot = { };
\tunsigned int i;

\tif (!mt6797_a72_obs_accepts_sampling(cpu))
\t\treturn;
\tfor (i = 0; i < ARRAY_SIZE(mt6797_a72_secure_registers); i++) {
""",
        "secure pure-snapshot entry guard",
    )

    clock = root / "drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c"
    replace_once(
        clock,
        """\tstruct mt6797_a72_obs_clock snapshot = { .status = -ENODEV };
\tunsigned long flags;

\tif (!spin_trylock_irqsave(&g_mt6797_0x1001AXXX_lock, flags)) {
""",
        """\tstruct mt6797_a72_obs_clock snapshot = { .status = -ENODEV };
\tunsigned long flags;

\tif (!mt6797_a72_obs_accepts_sampling(cpu))
\t\treturn;
\tif (!spin_trylock_irqsave(&g_mt6797_0x1001AXXX_lock, flags)) {
""",
        "clock pure-snapshot entry guard",
    )

    dcm = root / "drivers/misc/mediatek/base/power/mt6797/mt_dcm.c"
    replace_once(
        dcm,
        """\tcpu = mt6797_a72_obs_active_cpu();
\tspin_lock_irqsave(&mt6797_a72_obs_mp2_dcm_lock, flags);
""",
        """\tcpu = mt6797_a72_obs_active_cpu();
\tif (mt6797_a72_obs_is_cpu(cpu)) {
\tspin_lock_irqsave(&mt6797_a72_obs_mp2_dcm_lock, flags);
""",
        "DCM observed-branch entry",
    )
    replace_once(
        dcm,
        """\tif (mt6797_a72_obs_is_cpu(cpu))
\t\tmt6797_a72_obs_dcm(cpu,
\t\t\ton == MCUSYS_DCM_ON ? MT6797_A72_PHASE_DCM_ENABLE :
\t\t\t\t\t     MT6797_A72_PHASE_DCM_DISABLE,
\t\t\t&snapshot);
#else
\tif (on == MCUSYS_DCM_ON) {
""",
        """\t\tmt6797_a72_obs_dcm(cpu,
\t\t\ton == MCUSYS_DCM_ON ? MT6797_A72_PHASE_DCM_ENABLE :
\t\t\t\t\t     MT6797_A72_PHASE_DCM_DISABLE,
\t\t\t&snapshot);
\t\treturn 0;
\t}
#endif
\tif (on == MCUSYS_DCM_ON) {
""",
        "DCM original-vendor fallback",
    )
    replace_once(
        dcm,
        """\t}
#endif

\treturn 0;
}

#ifdef CONFIG_MTK_A72_TRANSITION_OBSERVER
void mt6797_a72_obs_dcm_snapshot(unsigned int cpu, u16 phase)
""",
        """\t}

\treturn 0;
}

#ifdef CONFIG_MTK_A72_TRANSITION_OBSERVER
void mt6797_a72_obs_dcm_snapshot(unsigned int cpu, u16 phase)
""",
        "DCM obsolete conditional close",
    )
    text = dcm.read_text()
    block_start = text.find(
        "\tif (mt6797_a72_obs_is_cpu(cpu)) {\n"
        "\tspin_lock_irqsave(&mt6797_a72_obs_mp2_dcm_lock, flags);\n"
    )
    block_end_marker = "\t\treturn 0;\n\t}\n#endif\n"
    block_end = text.find(block_end_marker, block_start)
    if block_start < 0 or block_end < 0:
        raise SystemExit("DCM observed block indentation markers changed")
    block_end += len(block_end_marker)
    lines = text[block_start:block_end].splitlines(keepends=True)
    indented = [lines[0]]
    indented.extend("\t" + line for line in lines[1:-2])
    indented.extend(lines[-2:])
    dcm.write_text(text[:block_start] + "".join(indented) + text[block_end:])
    replace_once(
        dcm,
        """\t};
\tunsigned long flags;

\tspin_lock_irqsave(&mt6797_a72_obs_mp2_dcm_lock, flags);
""",
        """\t};
\tunsigned long flags;

\tif (!mt6797_a72_obs_accepts_sampling(cpu))
\t\treturn;
\tspin_lock_irqsave(&mt6797_a72_obs_mp2_dcm_lock, flags);
""",
        "DCM pure-snapshot entry guard",
    )

    print("prepared=owner-effect-gate-v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
