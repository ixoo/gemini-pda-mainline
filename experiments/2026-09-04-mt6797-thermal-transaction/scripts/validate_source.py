#!/usr/bin/env python3
"""Validate the generated MT6797 thermal transaction source."""

from __future__ import annotations

import argparse
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def ordered(text: str, markers: list[tuple[str, str]]) -> None:
    position = -1
    for label, marker in markers:
        found = text.find(marker, position + 1)
        require(found >= 0, f"missing ordered marker {label}: {marker!r}")
        require(found > position, f"out-of-order marker: {label}")
        position = found


def section(text: str, start: str, end: str) -> str:
    require(text.count(start) == 1, f"non-unique section start: {start!r}")
    first = text.index(start)
    require(end in text[first:], f"section end absent: {end!r}")
    return text[first : text.index(end, first)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root

    thermal = (root / "drivers/thermal/mediatek/auxadc_thermal.c").read_text()
    internal = (
        root / "drivers/thermal/mediatek/auxadc_thermal_internal.h"
    ).read_text()
    test = (
        root / "drivers/thermal/mediatek/mt6797_auxadc_transaction_test.c"
    ).read_text()
    kconfig = (root / "drivers/thermal/mediatek/Kconfig").read_text()
    makefile = (root / "drivers/thermal/mediatek/Makefile").read_text()

    executor = section(
        internal,
        "mtk_thermal_transaction_execute(",
        "#endif /* __MTK_AUXADC_THERMAL_INTERNAL_H */",
    )
    ordered(
        executor,
        [
            ("AUXADC clock", "ops->enable_auxadc_clock"),
            ("thermal clock", "ops->enable_thermal_clock"),
            ("thermal reset", "ops->reset_thermal"),
            ("APMIXED", "ops->configure_apmixed"),
            ("idle", "ops->wait_for_idle"),
            ("pause", "ops->pause_disable_banks"),
            ("channel clear", "ops->clear_auxadc_channel"),
            ("prepare", "ops->prepare_bank"),
            ("channel commit", "ops->commit_auxadc_channel"),
            ("enable", "ops->enable_bank"),
            ("release", "ops->release_bank"),
            ("first sample", "ops->first_sample"),
            ("ready", "state->ready = true"),
        ],
    )
    close = section(
        internal,
        "mtk_thermal_transaction_close(",
        "static inline bool\nmtk_thermal_transaction_ops_valid(",
    )
    ordered(
        close,
        [
            ("pause", "ops->pause_disable_banks"),
            ("channel", "ops->disable_auxadc_channel"),
            ("APMIXED", "ops->restore_apmixed"),
            ("reset", "ops->assert_thermal_reset"),
            ("thermal clock", "ops->disable_thermal_clock"),
            ("AUXADC clock", "ops->disable_auxadc_clock"),
        ],
    )

    require("return value & ~GENMASK(5, 4);" in internal, "APMIXED mask")
    require("return !(value >> 16);" in internal, "thermal AHB idle")
    require("return !(value & BIT(0));" in internal, "AUXADC idle")
    require(
        "(raw & GENMASK(11, 0)) && temperature >= -20000" in internal,
        "first-sample raw/range gate",
    )

    prepare = section(
        thermal,
        "static int mt6797_thermal_prepare_bank(",
        "static int mt6797_thermal_commit_auxadc_channel(",
    )
    require("TEMP_AHBTO" not in prepare, "MT6797 must not program AHB timeout")
    require("TEMP_MONCTL0" not in prepare, "prepare must not enable a bank")
    ordered(
        prepare,
        [
            ("timing", "TEMP_MONCTL1"),
            ("poll", "TEMP_AHBPOLL"),
            ("sampling", "TEMP_MSRCTL0"),
            ("mux", "TEMP_ADCMUX"),
            ("PNP address", "TEMP_PNPMUXADDR"),
            ("valid", "TEMP_ADCVALIDMASK"),
            ("sensor map", "conf->sensor_mux_values"),
            ("final write control", "TEMP_ADCWRITECTRL_ADC_PNP_WRITE"),
        ],
    )

    probe = section(
        thermal,
        "static int mtk_thermal_probe(",
        "static void mtk_thermal_remove(",
    )
    ordered(
        probe,
        [
            ("calibration", "mtk_thermal_get_calibration_data"),
            ("thermal map", "devm_platform_get_and_ioremap_resource"),
            ("AUXADC map", '"mediatek,auxadc"'),
            ("APMIXED map", '"mediatek,apmixedsys"'),
            ("exclusive reset", "devm_reset_control_get_exclusive"),
            ("transaction", "mtk_thermal_transaction_execute"),
            ("zone", "devm_thermal_of_zone_register"),
        ],
    )
    require("if (!*base)" in thermal, "mapping failure check")
    require("devm_add_action_or_reset" in thermal, "mapping unwind")
    require("readl_poll_timeout" in thermal, "bounded idle polling")
    require("MT6797_FIRST_SAMPLE_ATTEMPTS" in thermal, "bounded sample loop")
    require(
        "if (!(raw & GENMASK(11, 0)))\n\t\treturn THERMAL_TEMP_INVALID;"
        in thermal,
        "raw zero must fail closed",
    )
    for forbidden in (
        "AUXADC_MISC",
        "devm_request_irq",
        "request_irq(",
        ".suspend =",
        ".resume =",
    ):
        require(forbidden not in thermal, f"forbidden production token: {forbidden}")

    require("#define MT6797_TEST_BANKS 6" in test, "six-bank fixture")
    require(
        "#define MT6797_TEST_FALLIBLE_CALLS 31" in test,
        "failure matrix size",
    )
    ordered(
        test,
        [
            ("success", "mt6797_transaction_success_order"),
            ("failure matrix", "mt6797_transaction_all_failures_close"),
            ("invalid start", "mt6797_transaction_rejects_invalid_start"),
            ("APMIXED", "mt6797_transaction_apmixed_mask"),
            ("idle", "mt6797_transaction_idle_predicates"),
            ("sample", "mt6797_transaction_first_sample_gate"),
        ],
    )
    require(
        "config MTK_SOC_THERMAL_TRANSACTION_KUNIT_TEST" in kconfig,
        "KUnit option",
    )
    require(
        "CONFIG_MTK_SOC_THERMAL_TRANSACTION_KUNIT_TEST" in makefile,
        "KUnit object",
    )

    print("production_path_count=2")
    print("kunit_path_count=3")
    print("bank_count=6")
    print("fallible_operation_count=31")
    print("thermal_dt_enabled=no")
    print("auxadc_dt_enabled=no")
    print("irq_or_watchdog_action=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as error:
        raise SystemExit(f"error: {error}")
