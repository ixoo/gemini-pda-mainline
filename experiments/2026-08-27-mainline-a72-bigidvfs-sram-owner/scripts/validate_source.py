#!/usr/bin/env python3
"""Validate generated MT6797 A72 BigiDVFS SRAM-owner source."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def public_definition_count(source: str, name: str) -> int:
    pattern = re.compile(
        rf"^[ \t]*int[ \t\r\n]+{re.escape(name)}[ \t\r\n]*\(",
        re.MULTILINE,
    )
    return len(pattern.findall(source))


def collapse_whitespace(source: str) -> str:
    return " ".join(source.split())


def require_order(source: str, tokens: tuple[str, ...], label: str) -> None:
    positions = [source.find(token) for token in tokens]
    require(all(position >= 0 for position in positions),
            f"{label}: missing token")
    require(positions == sorted(positions), f"{label}: order changed")


def bounded_section(source: str, start: str, end: str, label: str) -> str:
    start_position = source.find(start)
    require(start_position >= 0, f"{label}: start absent")
    end_position = source.find(end, start_position)
    require(end_position >= 0, f"{label}: end absent")
    return source[start_position:end_position + len(end)]


def validate_helpers() -> None:
    wrapped = "int\nexample(struct device *dev)\n{\n\treturn 0;\n}\n"
    called = "\treturn example(dev);\n"
    require(public_definition_count(wrapped + called, "example") == 1,
            "definition counter distinguishes wrapped definitions from calls")
    require_order("alpha beta gamma", ("alpha", "beta", "gamma"),
                  "order helper")
    require(bounded_section("before start middle end after", "start", "end",
                            "section helper") == "start middle end",
            "section helper bounds an assertion")


def main() -> None:
    validate_helpers()
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
    source = (root /
              "drivers/soc/mediatek/mt6797-bigidvfs-backend.c").read_text(
                  encoding="utf-8")
    public = (root /
              "include/linux/soc/mediatek/mt6797-bigidvfs-backend.h").read_text(
                  encoding="utf-8")
    internal_path = (root /
                     "drivers/soc/mediatek/mt6797-bigidvfs-sram-internal.h")
    internal = internal_path.read_text(encoding="utf-8")
    normalized = collapse_whitespace(source)

    require(kconfig.count(
        "config MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER\n") == 1,
        "production Kconfig")
    require("depends on MTK_MT6797_DVFSP_BIGIDVFS_BACKEND" in kconfig,
            "owner depends on exact backend")
    require("default n" in kconfig[kconfig.index(
        "config MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER\n"):],
            "owner default-off")
    for token in (
        "#define MT6797_BIGIDVFS_FID_SRAM_LDO_SET\t0xc20003bfUL",
        "#define MT6797_BIGIDVFS_SRAM_CALIBRATION\t0x102222b4U",
        "#define MT6797_BIGIDVFS_SRAM_TARGET_MV_X100\t110000U",
        "#define MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED\t0x8fbU",
        "#define MT6797_BIGIDVFS_SRAM_SETTLE_MIN_US\t240U",
        "struct mt6797_bigidvfs_sram_request",
        "struct mt6797_bigidvfs_sram_result",
        "mt6797_bigidvfs_sram_enable(",
    ):
        require(token in public, f"public contract token: {token}")
    for forbidden in ("0xc20003c0", "FID_SRAM_LDO_GET", "FID_WRITE",
                      "voltage_uv", "cpu_up(", "cpu_down("):
        require(forbidden not in public,
                f"forbidden public interface token: {forbidden}")
    for token in (
        "enum mt6797_bigidvfs_sram_owner_state",
        "struct mt6797_bigidvfs_sram_ops",
        "struct mt6797_bigidvfs_sram_owner",
        "mt6797_bigidvfs_sram_owner_execute(",
    ):
        require(token in internal, f"internal owner token: {token}")

    require(source.count(
        "struct mt6797_bigidvfs_sram_owner sram_owner;") == 1,
        "single backend-owned SRAM state")
    require(source.count(
        "case MT6797_BIGIDVFS_SRAM_CALIBRATION:") == 1,
        "single calibration whitelist entry")
    require(source.count(
        "arm_smccc_smc(MT6797_BIGIDVFS_FID_SRAM_LDO_SET") == 1,
        "single exact secure set adapter")
    require(public_definition_count(
        source, "mt6797_bigidvfs_sram_owner_execute") == 1,
        "single internal owner definition")
    require(public_definition_count(
        source, "mt6797_bigidvfs_sram_enable") == 1,
        "single public adapter definition")
    require(source.count("mt6797_bigidvfs_sram_enable(") == 1,
            "public SRAM API has zero production callers")
    require(source.count("EXPORT_SYMBOL_GPL(mt6797_bigidvfs_sram_enable)") == 1,
            "public API export")
    require("EXPORT_SYMBOL_GPL(mt6797_bigidvfs_sram_owner_execute)" not in
            source, "internal owner is not exported")
    owner_execute = bounded_section(
        normalized,
        "int mt6797_bigidvfs_sram_owner_execute(",
        "int mt6797_bigidvfs_sram_enable(",
        "internal SRAM owner",
    )
    require_order(
        owner_execute,
        (
            "owner->state = MT6797_BIGIDVFS_SRAM_OWNER_INFLIGHT;",
            "owner->request = *request;",
            "owner->result.attempted_steps |= MT6797_BIGIDVFS_SRAM_SERVICE;",
            "ret = ops->set(context, MT6797_BIGIDVFS_SRAM_TARGET_MV_X100);",
            "owner->result.completed_steps |= MT6797_BIGIDVFS_SRAM_SERVICE;",
            "ops->delay(context, MT6797_BIGIDVFS_SRAM_SETTLE_MIN_US, MT6797_BIGIDVFS_SRAM_SETTLE_MAX_US);",
            "MT6797_BIGIDVFS_SRAM_SELECTOR_FIRST",
            "MT6797_BIGIDVFS_SRAM_CALIBRATION_FIRST",
            "MT6797_BIGIDVFS_SRAM_SELECTOR_SECOND",
            "MT6797_BIGIDVFS_SRAM_CALIBRATION_SECOND",
            "owner->state = MT6797_BIGIDVFS_SRAM_OWNER_VERIFIED;",
        ),
        "consume-set-delay-two-sample-verify",
    )
    adapter = bounded_section(
        normalized,
        "int mt6797_bigidvfs_sram_enable(",
        "EXPORT_SYMBOL_GPL(mt6797_bigidvfs_sram_enable);",
        "public SRAM adapter",
    )
    require_order(
        adapter,
        (
            "mutex_lock(&backend->operation_lock);",
            "mt6797_bigidvfs_sram_owner_execute(&backend->sram_owner,",
            "mt6797_bigidvfs_mark_fault(backend);",
            "mutex_unlock(&backend->operation_lock);",
        ),
        "shared backend serialization",
    )
    for token in (
        "request->cpu != 8",
        "!request->provider_held",
        "!request->isolation_crossed",
        "request->cpu8_online",
        "request->cpu9_online",
        "return -EALREADY;",
        "return -EPERM;",
        "owner->result.selector_first != owner->result.selector_second",
        "owner->result.calibration_first != owner->result.calibration_second",
        "~MT6797_BIGIDVFS_SRAM_CALIBRATION_MASK",
        "mt6797_bigidvfs_sram_fail(owner, -EAGAIN, result)",
        "mt6797_bigidvfs_sram_fail(owner, -ERANGE, result)",
    ):
        require(token in source, f"owner safety token: {token}")
    for forbidden in ("CPU_OFF", "cpu_up(", "cpu_down(", "psci_",
                      "regulator_", "reset_control_", "writel(",
                      "gemini_transition_ledger", "mtk_wdt"):
        require(forbidden not in source,
                f"forbidden production composition token: {forbidden}")

    test_path = (root /
                 "drivers/soc/mediatek/mt6797-bigidvfs-sram-owner-test.c")
    if args.phase == "tests":
        test_source = test_path.read_text(encoding="utf-8")
        require(kconfig.count(
            "config MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER_KUNIT_TEST\n") == 1,
            "test Kconfig")
        require(makefile.count("mt6797-bigidvfs-sram-owner-test.o") == 1,
                "test object")
        require(test_source.count(
            "KUNIT_CASE(mt6797_bigidvfs_sram_") == 8,
            "eight focused cases")
        for token in (
            '"mt6797-bigidvfs-sram-owner"',
            "mt6797_bigidvfs_sram_success_test",
            "mt6797_bigidvfs_sram_guards_test",
            "mt6797_bigidvfs_sram_one_shot_test",
            "mt6797_bigidvfs_sram_service_failure_test",
            "mt6797_bigidvfs_sram_read_failures_test",
            "mt6797_bigidvfs_sram_instability_test",
            "mt6797_bigidvfs_sram_selector_test",
            "mt6797_bigidvfs_sram_calibration_test",
            "MT6797_SRAM_TEST_LOG_CAPACITY 6U",
        ):
            require(token in test_source, f"test token: {token}")
        for token in ("arm_smccc", "usleep_range", "udelay(", "readl(",
                      "writel(", "regmap_", "reset_control_", "cpu_up(",
                      "psci_", "gemini_transition_ledger", "mtk_wdt"):
            require(token not in test_source,
                    f"hardware-free test token: {token}")
    else:
        require("MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER_KUNIT_TEST\n\tbool"
                not in kconfig, "tests absent from production phase")
        require(not test_path.exists(), "test source absent")

    print(f"source_phase={args.phase}")
    print("serialized_resource_owner=bigidvfs-backend")
    print("sram_target_mv_x100=110000")
    print("selector_expected=0x8fb")
    print("calibration_samples=2")
    print("focused_kunit_cases=8")
    print("production_callers=0")
    print("physical_effect_calls=0")
    print("device_action=none")
    print("source_validation=pass")


if __name__ == "__main__":
    main()
