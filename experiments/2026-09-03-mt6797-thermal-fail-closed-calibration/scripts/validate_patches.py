#!/usr/bin/env python3
"""Validate the two MT6797 thermal calibration normal patches."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCH_NAMES = (
    "0512-thermal-mediatek-require-valid-MT6797-calibration.patch",
    "0513-thermal-mediatek-test-calibration-requirement-policy.patch",
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def changed_paths(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))


def added_lines(text: str) -> str:
    return "\n".join(line[1:] for line in text.splitlines()
                     if line.startswith("+") and not line.startswith("+++"))


def validate(patch_dir: Path) -> None:
    actual = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(actual == PATCH_NAMES, f"unexpected patch inventory: {actual}")
    production = (patch_dir / PATCH_NAMES[0]).read_text(encoding="utf-8")
    kunit = (patch_dir / PATCH_NAMES[1]).read_text(encoding="utf-8")
    for name, text in zip(PATCH_NAMES, (production, kunit), strict=True):
        require(text.startswith("From "), f"{name}: not a normal format-patch")
        require("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
                in text, f"{name}: archive identity changed")
        require("Signed-off-by:" not in text,
                f"{name}: synthetic sign-off is forbidden")
    require("Subject: [PATCH 1/2] thermal: mediatek: require valid MT6797 calibration"
            in production, "production subject changed")
    require("Subject: [PATCH 2/2] thermal: mediatek: test calibration requirement policy"
            in kunit, "KUnit subject changed")
    require(changed_paths(production) == (
        "drivers/thermal/mediatek/auxadc_thermal.c",
        "drivers/thermal/mediatek/auxadc_thermal_internal.h",
    ), "production patch path inventory changed")
    require(changed_paths(kunit) == (
        "drivers/thermal/mediatek/Kconfig",
        "drivers/thermal/mediatek/Makefile",
        "drivers/thermal/mediatek/auxadc_thermal_test.c",
    ), "KUnit patch path inventory changed")
    production_added = added_lines(production)
    kunit_added = added_lines(kunit)
    for token in (
        "bool requires_calibration;", ".requires_calibration = true,",
        "mtk_thermal_calibration_status(",
        "mtk_thermal_calibration_length_valid(",
        "required ? len == expected : len >= expected",
    ):
        require(token in production_added, f"production addition missing: {token}")
    require(kunit_added.count("KUNIT_CASE(") == 9,
            "KUnit patch case count changed")
    for token in (
        "MTK_SOC_THERMAL_KUNIT_TEST",
        "mtk_thermal_required_missing_fails",
        "mtk_thermal_required_invalid_fails",
        "mtk_thermal_required_length_is_exact",
        "mtk-thermal-calibration-policy",
    ):
        require(token in kunit_added, f"KUnit addition missing: {token}")
    for forbidden in ("ioremap", "writel(", "readl(", "clk_", "device_reset",
                      "nvmem_cell", "platform_device", "module_param", "/dev/"):
        require(forbidden not in kunit_added,
                f"KUnit additions contain forbidden token: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    validate(args.patch_dir.resolve())
    print("validation=mt6797-thermal-fail-closed-format-patches")
    print("patches=2")
    print("changed_paths=5")
    print("synthetic_signoff=absent")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
