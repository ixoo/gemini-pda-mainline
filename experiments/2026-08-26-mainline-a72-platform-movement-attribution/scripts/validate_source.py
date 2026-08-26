#!/usr/bin/env python3
"""Validate exact platform-movement source invariants."""

from __future__ import annotations

import argparse
from pathlib import Path


MOVEMENTS = (
    "SPM_CPU_PWR_STATUS", "SPM_CPU_PWR_STATUS_2ND", "MP2_CPUSYS_PWR_CON",
    "MP2_CPU0_PWR_CON", "MP2_CPU1_PWR_CON", "CPU_EXT_BUCK_ISO",
    "MP2_SYNC_DCM", "CCI_MP2_PORT", "PWRAP_RESET",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: Path) -> str:
    require(path.is_file(), f"missing source: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    soc = root / "drivers/soc/mediatek"
    public = read(root / "include/linux/soc/mediatek/mt6797-a72-platform-state.h")
    internal = read(soc / "mt6797-a72-platform-state-internal.h")
    platform = read(soc / "mt6797-a72-platform-state.c")
    observer_header = read(soc / "mt6797-a72-platform-provider-clock-observer-internal.h")
    observer = read(soc / "mt6797-a72-platform-provider-clock-observer.c")

    for index, name in enumerate(MOVEMENTS):
        require(f"MT6797_A72_PLATFORM_MOVED_{name} = BIT({index})" in public,
                f"movement bit {index}: {name}")
        require(f"MT6797_A72_PLATFORM_MOVED_{name}" in platform,
                f"movement used: {name}")
    require("MT6797_A72_PLATFORM_MOVED_ALL = GENMASK(8, 0)" in public,
            "exact movement range")
    require("struct mt6797_a72_platform_state_failure" in public,
            "public failure detail")
    require("mt6797_a72_platform_state_snapshot_detailed" in public,
            "detailed public API")
    require("mt6797_a72_platform_state_snapshot(struct device *dev" in public,
            "legacy API preserved")
    require("struct mt6797_state_capture_ops" in internal,
            "injected capture ops")
    require(platform.count("ops->read_once(context, &first)") == 1,
            "exact first read")
    require(platform.count("ops->read_once(context, &second)") == 1,
            "exact second read")
    require("return -EBUSY;" in platform and "return -EAGAIN;" in platform,
            "distinct busy and movement returns")
    require(platform.index("return -EBUSY;") < platform.index("return -EAGAIN;"),
            "CCI busy precedence")
    require("failure->movement_mask = movement;" in platform and
            "failure->samples_valid = true;" in platform, "failure detail population")
    require("snapshot->valid = true;" in platform, "stable publication")
    require("while (" not in platform and "for (" not in platform, "no loop")
    require("udelay(" not in platform and "msleep(" not in platform, "no delay")
    require("writel(" not in platform, "no added write")
    require("struct mt6797_a72_platform_state_failure *failure" in observer_header,
            "observer platform detail callback")
    require("struct mt6797_a72_platform_state_failure *platform_failure" in observer_header,
            "observer capture detail")
    for token in (
        "movement=%03x", "cpu=%08x/%08x", "cpu2=%08x/%08x",
        "cpusys=%08x/%08x", "cpu0=%08x/%08x", "cpu1=%08x/%08x",
        "iso=%08x/%08x", "dcm=%08x/%08x", "cci-port=%08x/%08x",
        "pwrap=%u/%u",
    ):
        require(token in observer, f"movement log token: {token}")
    require(observer.count("mt6797_a72_platform_state_snapshot_detailed(") == 1,
            "one detailed platform call")
    require("ops->platform(context, platform, &snapshot->platform," in observer,
            "detail propagated")
    require("ret == -EAGAIN &&" in observer, "exact movement log gate")
    for forbidden in ("cpu_up(", "cpu_down(", "psci_ops", "kernel_restart(",
                      "i2c_transfer(", "gemini_protected_readback_ledger_checkpoint(2"):
        require(forbidden not in platform + observer, f"forbidden production action: {forbidden}")

    if args.phase == "tests":
        kconfig = read(soc / "Kconfig")
        makefile = read(soc / "Makefile")
        platform_test = read(soc / "mt6797-a72-platform-state-test.c")
        observer_test = read(soc / "mt6797-a72-platform-provider-clock-observer-test.c")
        require("config MTK_MT6797_A72_PLATFORM_STATE_KUNIT_TEST" in kconfig,
                "platform KUnit config")
        require("mt6797-a72-platform-state-test.o" in makefile,
                "platform KUnit object")
        for name in MOVEMENTS:
            require(f"MT6797_A72_PLATFORM_MOVED_{name}" in platform_test,
                    f"KUnit movement: {name}")
        for token in (
            "mt6797_state_stable_test", "mt6797_state_read_errors_test",
            "mt6797_state_cci_busy_precedence_test",
            "mt6797_state_each_movement_test", "mt6797_state_masked_noise_test",
            "state.calls, 1U", "state.calls, 2U", "ret, -EBUSY",
            "ret, -EAGAIN", "failure.movement_mask",
        ):
            require(token in platform_test, f"platform KUnit token: {token}")
        require(platform_test.count("KUNIT_CASE(") == 5, "five platform KUnit cases")
        require("state.platform_samples_valid = true;" in observer_test,
                "observer detail fixture")
        require("platform_failure.movement_mask" in observer_test,
                "observer detail assertion")
        require(observer_test.count("KUNIT_CASE(") == 8,
                "eight preserved observer KUnit cases")
    print(f"source_validation={args.phase}:pass")
    print("movement_bits=9")
    print("hardware_reads_per_complete_pair=unchanged")
    print("device_action=none")


if __name__ == "__main__":
    main()
