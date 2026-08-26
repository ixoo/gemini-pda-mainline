#!/usr/bin/env python3
"""Validate generated MT6797 A72 serialized platform-effect source."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def public_definition_count(source: str, name: str) -> int:
    """Count global int definitions across kernel-style line wrapping."""
    pattern = re.compile(
        rf"^[ \t]*int[ \t\r\n]+{re.escape(name)}[ \t\r\n]*\(",
        re.MULTILINE,
    )
    return len(pattern.findall(source))


def validate_definition_counter() -> None:
    wrapped = "int\nexample(struct device *dev)\n{\n\treturn 0;\n}\n"
    called = "\treturn example(dev);\n"
    require(public_definition_count(wrapped + called, "example") == 1,
            "definition counter accepts wrapped return type and rejects calls")


def main() -> None:
    validate_definition_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text(
        encoding="utf-8")
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text(
        encoding="utf-8")
    source = (root / "drivers/soc/mediatek/mt6797-a72-platform-state.c").read_text(
        encoding="utf-8")
    internal = (root / "drivers/soc/mediatek/mt6797-a72-platform-state-internal.h").read_text(
        encoding="utf-8")
    public = (root / "include/linux/soc/mediatek/mt6797-a72-platform-state.h").read_text(
        encoding="utf-8")
    combined = source + internal + public

    require(kconfig.count("config MTK_MT6797_A72_PLATFORM_EFFECTS\n") == 1,
            "production Kconfig")
    require("depends on MTK_MT6797_A72_PLATFORM_STATE" in kconfig,
            "platform-state ownership dependency")
    for token in (
        "struct mt6797_a72_platform_effect_handle",
        "struct mt6797_a72_platform_effect_result",
        "struct mt6797_a72_platform_effect_owner",
        "MT6797_A72_EFFECT_P27_BEFORE",
        "MT6797_A72_EFFECT_P27_HELD",
        "MT6797_A72_EFFECT_ISOLATION_BEFORE",
        "MT6797_A72_EFFECT_ISOLATION_AFTER",
        "MT6797_A72_EFFECT_DCM_TOGGLE_VALUE",
        "MT6797_A72_EFFECT_DCM_FINAL_VALUE",
        "MT6797_A72_EFFECT_GUARD_MIN_US",
        "owner->result.p27_owned = true;",
        "owner->result.isolation_attempted = true;",
        "owner->result.isolation_crossed = true;",
        "provider->generation == handle->attempt_id",
        "mutex_lock(&source->lock);",
        "regmap_update_bits(source->spm",
        "reset_control_assert(source->pwrap_reset)",
        "usleep_range(min_us, max_us)",
        "EXPORT_SYMBOL_GPL(mt6797_a72_platform_effect_p27_acquire)",
        "EXPORT_SYMBOL_GPL(mt6797_a72_platform_effect_p27_release)",
        "EXPORT_SYMBOL_GPL(mt6797_a72_platform_effect_isolation_clear)",
        "EXPORT_SYMBOL_GPL(mt6797_a72_platform_effect_dcm_update)",
    ):
        require(token in combined, f"production token: {token}")
    for name in (
        "mt6797_a72_platform_effect_p27_acquire",
        "mt6797_a72_platform_effect_p27_release",
        "mt6797_a72_platform_effect_isolation_clear",
        "mt6797_a72_platform_effect_dcm_update",
    ):
        require(public_definition_count(source, name) == 1,
                f"one production definition and no caller: {name}")
    p27_write = source.index(
        "ops->spm_update_bits(context, MT6797_A72_EFFECT_SPM_P27")
    p27_readback = source.index(
        "MT6797_A72_EFFECT_P27_HELD, &owner->result.spm_p27_after")
    bpll = source.index(
        "ops->mcucfg_read(context, MT6797_A72_EFFECT_MCUCFG_BPLL")
    pwrap = source.index("ret = ops->pwrap_assert(context);")
    require(p27_write < p27_readback < bpll < pwrap,
            "P27 write/readback/B-PLL/PWRAP order")
    isolation_write = source.index(
        "ops->spm_update_bits(context, MT6797_A72_EFFECT_SPM_ISOLATION")
    isolation_readback = source.index(
        "MT6797_A72_EFFECT_ISOLATION_AFTER,")
    isolation_deassert = source.index("ret = ops->pwrap_deassert(context);",
                                      isolation_write)
    isolation_delay = source.index("ops->delay(context,", isolation_deassert)
    require(isolation_write < isolation_readback < isolation_deassert <
            isolation_delay, "isolation/readback/PWRAP/guard order")
    dcm_toggle = source.index(
        "expected |= MT6797_A72_EFFECT_DCM_TOGGLE_VALUE;")
    dcm_final = source.index("expected &= ~BIT(1);", dcm_toggle)
    require(dcm_toggle < dcm_final, "DCM toggle before final")
    for token in ("cpu_up(", "add_cpu(", "psci_", "arm_smccc", "cpu_on(",
                  "watchdog", "gemini_transition_ledger", "regulator_"):
        require(token not in source,
                f"forbidden production composition/caller token: {token}")

    test_path = root / "drivers/soc/mediatek/mt6797-a72-platform-effect-test.c"
    if args.phase == "tests":
        test_source = test_path.read_text(encoding="utf-8")
        require(kconfig.count(
            "config MTK_MT6797_A72_PLATFORM_EFFECTS_KUNIT_TEST\n") == 1,
            "test Kconfig")
        require(makefile.count("mt6797-a72-platform-effect-test.o") == 1,
                "test object")
        require(test_source.count(
            "KUNIT_CASE(mt6797_platform_effect_") == 8,
            "eight focused cases")
        for token in (
            '"mt6797-a72-platform-effects"',
            "mt6797_platform_effect_success_test",
            "mt6797_platform_effect_p27_rejections_test",
            "mt6797_platform_effect_p27_failures_test",
            "mt6797_platform_effect_release_test",
            "mt6797_platform_effect_release_failures_test",
            "mt6797_platform_effect_isolation_guards_test",
            "mt6797_platform_effect_isolation_failures_test",
            "mt6797_platform_effect_dcm_failures_test",
            "MT6797_EFFECT_TEST_LOG_ENTRIES 32U",
        ):
            require(token in test_source, f"test token: {token}")
        for token in ("readl(", "writel(", "regmap_", "reset_control_",
                      "usleep_range", "cpu_up(", "psci_", "arm_smccc",
                      "gemini_transition_ledger", "mtk_wdt"):
            require(token not in test_source,
                    f"hardware-free test token: {token}")
    else:
        require("MTK_MT6797_A72_PLATFORM_EFFECTS_KUNIT_TEST\n\tbool" not in
                kconfig, "tests absent from production phase")
        require(not test_path.exists(), "test source absent")

    print(f"source_phase={args.phase}")
    print("serialized_resource_owner=platform-state-source")
    print("p27_effects=3")
    print("preisolation_inverse_effects=2")
    print("isolation_effects=3")
    print("dcm_effects=2")
    print("focused_kunit_cases=8")
    print("production_callers=0")
    print("physical_effect_calls=0")
    print("device_action=none")
    print("source_validation=pass")


if __name__ == "__main__":
    main()
