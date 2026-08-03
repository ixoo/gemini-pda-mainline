#!/usr/bin/env python3
"""Validate generated one-way CPU8 patches and their applied source."""

from __future__ import annotations

import argparse
from pathlib import Path


class ValidationError(RuntimeError):
    pass


PATHS = {
    "psci": "arch/arm64/kernel/psci.c",
    "smp": "arch/arm64/kernel/smp.c",
    "header": "include/linux/mt6797_a72_transition_observer.h",
    "ext_wd": "drivers/watchdog/mediatek/include/ext_wd_drv.h",
    "wdt": "drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c",
    "common": "drivers/watchdog/mediatek/wdk/wd_common_drv.c",
    "idvfs": "drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c",
    "dcm": "drivers/misc/mediatek/base/power/mt6797/mt_dcm.c",
    "kconfig": "drivers/misc/mediatek/base/power/Kconfig",
}


def require_once(text: str, token: str, label: str) -> None:
    count = text.count(token)
    if count != 1:
        raise ValidationError(f"{label}: expected one {token!r}, found {count}")


def require_order(text: str, tokens: tuple[str, ...], label: str) -> None:
    positions = [text.find(token) for token in tokens]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ValidationError(f"{label}: ordering failed for {tokens!r}")


def validate_files(files: dict[str, str]) -> None:
    missing = set(PATHS) - set(files)
    if missing:
        raise ValidationError(f"missing source texts: {sorted(missing)}")
    psci = files["psci"]
    smp = files["smp"]
    common = files["common"]
    wdt = files["wdt"]
    idvfs = files["idvfs"]
    dcm = files["dcm"]
    header = files["header"]
    kconfig = files["kconfig"]

    require_once(kconfig, "config MTK_A72_ONE_WAY_CPU8", "Kconfig option")
    for dependency in (
        "depends on SMP && HOTPLUG_CPU && CL2_BUCK_CTRL",
        "depends on MTK_A72_TRANSITION_OBSERVER",
        "depends on MTK_WATCHDOG && MTK_WD_KICKER",
        "depends on PSTORE && PSTORE_CONSOLE && PSTORE_RAM",
    ):
        if dependency not in kconfig:
            raise ValidationError(f"Kconfig dependency absent: {dependency}")

    takeover = common[common.index("int mtk_wd_a72_recovery_takeover"):]
    takeover = takeover[: takeover.index("static void wdk_work_callback")]
    require_order(
        takeover,
        (
            "spin_lock(&lock)",
            "g_enable = 0",
            "mtk_wdt_recovery_arm(12, state)",
            "if (ret && !state->owned)",
            "g_enable = 1",
            "spin_unlock(&lock)",
        ),
        "kicker takeover",
    )
    if "cpu_hotplug_disable" in takeover or "cpu_hotplug_enable" in takeover:
        raise ValidationError("takeover recursively changes CPU-hotplug state")

    low = wdt[wdt.index("int mtk_wdt_recovery_arm"):]
    low = low[: low.index("void mtk_wdt_restart")]
    for token in (
        "timeout != 12",
        "mtk_wdt_recovery_owned = true",
        "state->length_after",
        "state->mode_after",
    ):
        if token not in low:
            raise ValidationError(f"low-level watchdog contract absent: {token}")
    readback_contract = (
        "(state->mode_after & (MTK_WDT_MODE_ENABLE |\n"
        "\t\tMTK_WDT_MODE_EXTEN | MTK_WDT_MODE_IRQ |\n"
        "\t\tMTK_WDT_MODE_DUAL_MODE | MTK_WDT_MODE_EXT_POL |\n"
        "\t\tMTK_WDT_MODE_AUTO_RESTART)) !=\n"
        "\t    (MTK_WDT_MODE_ENABLE | MTK_WDT_MODE_EXTEN |\n"
        "\t     MTK_WDT_MODE_AUTO_RESTART)"
    )
    if readback_contract not in low:
        raise ValidationError("exact watchdog automatic-reset readback absent")
    if "READ_ONCE(mtk_wdt_recovery_owned)" not in wdt:
        raise ValidationError("later restart interlock absent")

    boot = psci[psci.index("static int mt6797_a72_one_way_boot"):]
    boot = boot[: boot.index("int mt6797_a72_one_way_secondary_complete")]
    require_order(
        boot,
        (
            "mt6797_a72_obs_accepts_sampling(cpu)",
            "mtk_wd_a72_recovery_takeover(&watchdog)",
            "atomic_xchg(&mt6797_a72_one_way_attempted, 1)",
            'stage = "spm-reset"',
            'stage = "pwrap-assert"',
            'stage = "buck-enable"',
            'stage = "buck-settle"',
            'stage = "isolation-write"',
            'stage = "pwrap-deassert"',
            'stage = "sram-readback"',
            'stage = "psci"',
            "psci_ops.cpu_on",
        ),
        "one-way forward dominance",
    )
    require_once(boot, "postiso_fault:\n", "post-isolation fault label")
    rollback = boot[boot.index("rollback:\n"): boot.index("postiso_fault:\n")]
    if "bool rollback_fault = false" not in boot:
        raise ValidationError("independent rollback-failure state absent")
    if "fault = true" in boot:
        raise ValidationError("forward failure contaminates rollback result")
    for token in (
        "MT6797_A72_PHASE_ROLLBACK_BUCK_DISABLE",
        "0x00010133, 0x00010132",
        "MT6797_A72_PHASE_ROLLBACK_PWRAP_DEASSERT",
        "rollback_fault = true",
    ):
        if token not in rollback:
            raise ValidationError(f"pre-isolation rollback missing: {token}")
    postiso = boot[boot.index("postiso_fault:\n"):]
    for forbidden in (
        "da9214_a72_diag_compare_update",
        "mt6797_a72_diag_spm_compare_update",
        "BigiDVFSSRAMLDODisable",
        "psci_ops.cpu_off",
        "cpu_power_off_buck",
    ):
        if forbidden in postiso:
            raise ValidationError(f"post-isolation guessed inverse present: {forbidden}")
    for marker in (
        '"rejected-prestate"',
        '"rolled-back-preiso"',
        '"fault-retain-preiso"',
        '"fault-retain-postiso"',
    ):
        if marker not in boot:
            raise ValidationError(f"terminal marker absent: {marker}")

    require_once(psci, "if (cpu == 9) {", "CPU9 early rejection")
    require_order(
        psci,
        (
            "if (cpu == 9) {",
            'pr_info("one-way: reject CPU9 before A72 action',
            "err = -EPERM",
            "goto mt6797_a72_one_way_out",
        ),
        "CPU9 rejection",
    )
    disable = psci[psci.index("static int cpu_psci_cpu_disable"):]
    disable = disable[: disable.index("static void cpu_psci_cpu_die")]
    if "if (cpu == 8 || cpu == 9)" not in disable or "return -EPERM" not in disable:
        raise ValidationError("CPU8/9 CPU_OFF rejection absent")

    complete = psci[psci.index("int mt6797_a72_one_way_secondary_complete"):]
    complete = complete[: complete.index("static int cpu_power_on_buck")]
    require_order(
        complete,
        (
            "!completed || !cpu_online(8) || cpu_online(9)",
            "mt6797_a72_one_way_dcm_enable(cpu)",
            "g_cl2_online |= 1",
            '"cpu8-online-held"',
        ),
        "secondary completion and DCM",
    )
    require_order(
        smp,
        (
            "secondary_completed =",
            "wait_for_completion_timeout(&cpu_running",
            "mt6797_a72_one_way_secondary_complete(cpu",
            "secondary_completed && cpu_online(cpu)",
        ),
        "generic SMP completion handoff",
    )

    helper = idvfs[idvfs.index("int mt6797_a72_one_way_sram_set_verify"):]
    helper = helper[: helper.index("/* 0x11017000")]
    require_order(
        helper,
        (
            "BigiDVFSSRAMLDOSet(110000)",
            "udelay(240)",
            "SEC_BIGIDVFS_READ(0x102222b0)",
            "SEC_BIGIDVFS_READ(0x102222b4)",
            "selector_first != selector_second",
            "calibration_first != calibration_second",
            "(calibration_second & 0xffff0000)",
            "!(calibration_second & 0xffff)",
            "(selector_second & 0xfff) != 0x8fb",
        ),
        "SRAM request and independent readback",
    )
    if "calibration_first" in psci[psci.index("static void mt6797_a72_one_way_marker"):psci.index("static void mt6797_a72_one_way_checkpoint")]:
        raise ValidationError("terminal marker exposes calibration")

    dcm_helper = dcm[dcm.index("int mt6797_a72_one_way_dcm_enable"):]
    dcm_helper = dcm_helper[: dcm_helper.index("int dcm_mcusys_little")]
    for token in (
        "if (cpu != 8 || !cpu_online(8) || cpu_online(9))",
        "snapshot.before & snapshot.mask",
        "(snapshot.toggle & snapshot.mask) != 0x0f",
        "(snapshot.final & snapshot.mask) != 0x0d",
    ):
        if token not in dcm_helper:
            raise ValidationError(f"DCM exact helper contract absent: {token}")

    for declaration in (
        "mt6797_a72_one_way_sram_set_verify",
        "mt6797_a72_one_way_dcm_enable",
        "mt6797_a72_one_way_secondary_complete",
    ):
        if declaration not in header:
            raise ValidationError(f"one-way declaration absent: {declaration}")
def read_source(source: Path) -> dict[str, str]:
    return {name: (source / path).read_text() for name, path in PATHS.items()}


def validate_patch_inventory(patch_dir: Path) -> None:
    expected = (
        "0001-diagnostic-add-exclusive-A72-recovery-takeover.patch",
        "0002-diagnostic-add-one-way-SRAM-and-DCM-owners.patch",
        "0003-diagnostic-run-one-way-CPU8-startup.patch",
    )
    series = tuple((patch_dir / "series").read_text().splitlines())
    if series != expected:
        raise ValidationError(f"unexpected generated series: {series!r}")
    for name in expected:
        text = (patch_dir / name).read_text()
        if "Signed-off-by:" in text:
            raise ValidationError(f"synthetic DCO sign-off in {name}")
        if "noreply@gemini-a72.invalid" not in text:
            raise ValidationError(f"experiment identity absent in {name}")
    added = "\n".join(
        line[1:]
        for name in expected
        for line in (patch_dir / name).read_text().splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for forbidden in (
        "BigiDVFSEnable_hp();",
        "BigiDVFSSRAMLDODisable();",
        "psci_ops.cpu_off(",
    ):
        if forbidden in added:
            raise ValidationError(f"forbidden new operation present: {forbidden}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    validate_patch_inventory(args.patch_dir)
    validate_files(read_source(args.source))
    print("PASS: one-way CPU8 watchdog, owners, rollback, completion, and forbiddance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
