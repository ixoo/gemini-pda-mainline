#!/usr/bin/env python3
"""Validate the edited MT6797 thermal calibration source contract."""

from __future__ import annotations

import argparse
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        require(token in text, f"{label} missing token: {token}")


def validate(root: Path) -> None:
    thermal = root / "drivers/thermal/mediatek"
    driver = (thermal / "auxadc_thermal.c").read_text(encoding="utf-8")
    header = (thermal / "auxadc_thermal_internal.h").read_text(encoding="utf-8")
    test = (thermal / "auxadc_thermal_test.c").read_text(encoding="utf-8")
    kconfig = (thermal / "Kconfig").read_text(encoding="utf-8")
    makefile = (thermal / "Makefile").read_text(encoding="utf-8")

    require_tokens(header, (
        "mtk_thermal_calibration_status(bool required, int ret)",
        "!required && ret != -EPROBE_DEFER",
        "mtk_thermal_calibration_length_valid(bool required, size_t len)",
        "required ? len == expected : len >= expected",
    ), "policy header")
    require_tokens(driver, (
        '#include "auxadc_thermal_internal.h"',
        "bool requires_calibration;",
        ".requires_calibration = true,",
        "bool calibration_required;",
        "calibration_required = mt->conf->requires_calibration;",
        "ret = PTR_ERR(cell);",
        "mtk_thermal_calibration_length_valid(",
        "mtk_thermal_calibration_length_valid(calibration_required, len)",
        "mtk_thermal_calibration_status(",
        "mtk_thermal_calibration_status(calibration_required, ret)",
    ), "production driver")
    require(driver.count(".requires_calibration = true,") == 1,
            "required calibration must be MT6797-only match data")
    require("if (PTR_ERR(cell) == -EPROBE_DEFER)" not in driver,
            "old missing-cell fallback branch remains")
    require("if (len < 3 * sizeof(u32))" not in driver,
            "old minimum-only length branch remains")
    require_tokens(kconfig, (
        "config MTK_SOC_THERMAL_KUNIT_TEST",
        "depends on KUNIT",
        "depends on MTK_SOC_THERMAL",
        "performs no MMIO",
    ), "Kconfig")
    require(
        "obj-$(CONFIG_MTK_SOC_THERMAL_KUNIT_TEST) += auxadc_thermal_test.o"
        in makefile,
        "KUnit object is not isolated behind its option",
    )
    require(test.count("KUNIT_CASE(") == 9, "KUnit case count changed")
    require_tokens(test, (
        "mtk_thermal_optional_missing_falls_back",
        "mtk_thermal_required_missing_fails",
        "mtk_thermal_optional_invalid_falls_back",
        "mtk_thermal_required_invalid_fails",
        "mtk_thermal_defer_always_propagates",
        "mtk_thermal_optional_length_preserves_minimum",
        "mtk_thermal_required_length_is_exact",
        '.name = "mtk-thermal-calibration-policy"',
    ), "KUnit source")
    for forbidden in (
        "ioremap", "writel(", "readl(", "clk_", "device_reset",
        "nvmem_cell", "platform_device", "debugfs", "sysfs", "procfs",
        "module_param", "/dev/", "boot2",
    ):
        require(forbidden not in test,
                f"KUnit source contains forbidden token: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    validate(args.source_root.resolve())
    print("validation=mt6797-thermal-fail-closed-edited-source")
    print("kunit_cases=9")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
