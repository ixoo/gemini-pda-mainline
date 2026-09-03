#!/usr/bin/env python3
"""Validate the disconnected CPU9 physical-executor source."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;]*?\)\s*\{{", source,
                      re.S)
    require(match is not None, f"missing function: {name}")
    depth = 0
    for offset in range(match.end() - 1, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():offset + 1]
    raise ValueError(f"unterminated function: {name}")


def validate(root: pathlib.Path, require_tests: bool) -> None:
    relative = pathlib.Path("drivers/soc/mediatek")
    kconfig = (root / relative / "Kconfig").read_text()
    makefile = (root / relative / "Makefile").read_text()
    header = (root / relative /
              "mt6797-a72-hotplug-executor-internal.h").read_text()
    source = (root / relative / "mt6797-a72-hotplug-executor.c").read_text()
    psci = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    require(kconfig.count("config MTK_MT6797_A72_HOTPLUG_EXECUTOR\n") == 1,
            "executor Kconfig missing or duplicated")
    require(kconfig.count(
        "config MTK_MT6797_A72_HOTPLUG_EXECUTOR_KUNIT_TEST\n") == 1,
        "executor test Kconfig missing or duplicated")
    block = kconfig.split("config MTK_MT6797_A72_HOTPLUG_EXECUTOR\n", 1)[1]
    block = block.split("config MTK_MT6797_A72_HOTPLUG_EXECUTOR_KUNIT_TEST", 1)[0]
    require("\tdefault n\n" in block, "executor is not default-off")
    require("\tselect " not in block, "executor selects a dependency")
    require(makefile.count(
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_EXECUTOR) += "
        "mt6797-a72-hotplug-executor.o\n") == 1,
        "executor Makefile entry changed")
    require(makefile.count(
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_EXECUTOR_KUNIT_TEST) += "
        "mt6797-a72-hotplug-executor-test.o\n") == 1,
        "executor test Makefile entry changed")

    required_header = (
        "MT6797_A72_HOTPLUG_CPU8_STATUS BIT(7)",
        "MT6797_A72_HOTPLUG_CPU9_STATUS BIT(6)",
        "MT6797_A72_HOTPLUG_EXT_ISO_MASK BIT(1)",
        "MT6797_A72_HOTPLUG_DCM_MASK GENMASK(6, 0)",
        "MT6797_A72_HOTPLUG_CCI_REQUEST_MASK GENMASK(1, 0)",
        "MT6797_A72_HOTPLUG_AFFINITY_LEVEL0 0U",
        "MT6797_A72_HOTPLUG_AFFINITY_OFF 1",
        "atomic_t consumed;", "atomic_t lifecycle;",
        "u64 watchdog_identity;", "u32 cpu_off_authorizations;",
        "u32 affinity_calls;", "u32 snapshots;", "u32 cpu8_callbacks;",
        "int (*watchdog_validate)(void *context, u64 identity);",
        "int (*affinity_info)(void *context, unsigned int cpu,",
        "int mt6797_a72_hotplug_executor_target_returned(",
    )
    for token in required_header:
        require(token in header, f"header contract missing: {token}")

    forbidden = (
        "psci_ops.", "arm_smccc", "mtk_wdt_recovery_takeover",
        "readl(", "writel(", "ioread", "iowrite", "regmap_",
        "cpu_down(", "cpu_up(", "device_offline(",
    )
    for token in forbidden:
        require(token not in source + header,
                f"physical backend connected: {token}")
    for callback in (".cpu_down_preflight", ".cpu_down_validate",
                     ".cpu_down_complete", ".cpu_down_failed"):
        require(callback not in psci, f"production callback bound: {callback}")
    require("return false;" in function_body(psci,
            "mt6797_psci_cpu_can_disable"), "disable veto opened")

    classifier = function_body(
        source, "mt6797_a72_hotplug_readback_proves_cpu9_off")
    for token in (
        "mt6797_a72_hotplug_status_exact(baseline, true)",
        "mt6797_a72_hotplug_status_exact(post_state, false)",
        "spm_mp2_cpusys_pwr_con", "spm_mp2_cpu0_pwr_con",
        "MT6797_A72_HOTPLUG_EXT_ISO_MASK",
        "MT6797_A72_HOTPLUG_DCM_MASK",
        "MT6797_A72_HOTPLUG_CCI_REQUEST_MASK",
        "memcmp(baseline->provider", "memcmp(baseline->clock",
        "memcmp(baseline->bigidvfs",
    ):
        require(token in classifier, f"classifier gate missing: {token}")
    require("->spm_pwr_status" not in classifier,
            "general SPM status promoted to a predicate")
    require("spm_mp2_cpu1_pwr_con" not in classifier,
            "CPU9 core control promoted without a public mask")

    commit = function_body(source, "mt6797_a72_hotplug_executor_commit")
    require("result->off_committed = true;" in commit and
            "result->cpu_off_authorizations = 1;" in commit,
            "CPU_OFF commit boundary changed")
    require("MT6797_A72_HOTPLUG_AFTER" in commit and
            "MT6797_A72_HOTPLUG_STAGE_OFF_COMMIT" in commit,
            "durable post-commit checkpoint missing")
    kill = function_body(source, "mt6797_a72_hotplug_executor_kill")
    require(kill.count("ops->affinity_info(") == 1,
            "affinity call is not exactly one source site")
    require("result->affinity_calls++;" in kill and
            "MT6797_A72_HOTPLUG_AFFINITY_LEVEL0" in kill and
            "MT6797_A72_HOTPLUG_AFFINITY_OFF" in kill,
            "affinity budget or predicate changed")
    require(kill.count("ops->snapshot(") == 1 and
            kill.count("ops->cpu8_callback(") == 1 and
            kill.count("ops->prove_off(") == 1,
            "post-affinity proof sequence changed")
    returned = function_body(
        source, "mt6797_a72_hotplug_executor_target_returned")
    require("mt6797_a72_hotplug_fault" in returned,
            "returned CPU_OFF is not terminal")
    require("retry" not in source.lower(), "retry path added")

    if require_tests:
        test_source = (root / relative /
                       "mt6797-a72-hotplug-executor-test.c").read_text()
        require(test_source.count("KUNIT_CASE(mt6797_hotplug_") == 8,
                "focused test count changed")
        for name in (
            "success", "entry_rejections", "precommit_rejection",
            "target_return_is_fault", "affinity_is_one_shot",
            "readback_rejections", "postcommit_callback_fault",
            "order_and_one_shot",
        ):
            require(f"KUNIT_CASE(mt6797_hotplug_{name})" in test_source,
                    f"missing KUnit case: {name}")
        for token in forbidden:
            require(token not in test_source,
                    f"test connected physical backend: {token}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    parser.add_argument("--require-tests", action="store_true")
    args = parser.parse_args()
    try:
        validate(args.source_root.resolve(), args.require_tests)
    except (OSError, ValueError) as exc:
        print(f"physical_executor_source=fail reason={exc}", file=sys.stderr)
        return 1
    print("physical_executor_source=pass")
    print("cpu_off_authorizations=1")
    print("affinity_call_sites=1")
    print("post_affinity_snapshots=1")
    print("cpu8_callbacks=1")
    print("watchdog_mutations=0")
    print("production_callbacks_bound=false")
    print("cpu_can_disable=false")
    if args.require_tests:
        print("focused_kunit_cases=8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
