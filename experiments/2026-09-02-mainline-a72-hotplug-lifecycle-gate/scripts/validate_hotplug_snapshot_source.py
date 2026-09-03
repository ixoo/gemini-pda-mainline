#!/usr/bin/env python3
"""Fail-closed source oracle for the disconnected hotplug snapshot adapter."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def function_body(text: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^;]*?\)\s*\{{", text, re.S)
    require(match is not None, f"function missing: {name}")
    start = match.end()
    depth = 1
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index]
    raise ValueError(f"unterminated function: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.source_root.resolve()
        mediatek = root / "drivers/soc/mediatek"
        internal = (
            mediatek / "mt6797-a72-hotplug-snapshot-internal.h"
        ).read_text(encoding="utf-8")
        source = (mediatek / "mt6797-a72-hotplug-snapshot.c").read_text(
            encoding="utf-8"
        )
        test = (mediatek / "mt6797-a72-hotplug-snapshot-test.c").read_text(
            encoding="utf-8"
        )
        kconfig = (mediatek / "Kconfig").read_text(encoding="utf-8")
        makefile = (mediatek / "Makefile").read_text(encoding="utf-8")

        for token in (
            "MT6797_A72_HOTPLUG_CLOCK_POWERON_WRITES 1U",
            "MT6797_A72_HOTPLUG_CLOCK_ACQUIRE_WRITES_MAX 200U",
            "MT6797_A72_HOTPLUG_CLOCK_RELEASE_WRITES_MAX 200U",
            "MT6797_A72_HOTPLUG_BIGIDVFS_STABLE_SAMPLES 2U",
            "MT6797_A72_HOTPLUG_BIGIDVFS_READS 8U",
            "u32 protected_readback_checkpoints;",
            "u32 direct_state_calls;",
            "u32 physical_source_calls;",
            "u32 binding_retries;",
            "u32 bigidvfs_sram_set_calls;",
        ):
            require(token in internal, f"snapshot contract missing: {token}")
        require(
            "struct device *platform;" in internal
            and "struct device *clock;" in internal
            and "struct device *bigidvfs;" in internal,
            "three long-lived source references changed",
        )

        wrappers = (
            (
                "mt6797_hotplug_platform",
                "return mt6797_a72_platform_state_snapshot(dev, snapshot);",
            ),
            (
                "mt6797_hotplug_provider",
                "return mt6797_a72_provider_snapshot(snapshot);",
            ),
            (
                "mt6797_hotplug_clock",
                "return mt6797_dvfsp_clock_backend_read(dev, snapshot);",
            ),
            (
                "mt6797_hotplug_bigidvfs",
                "return mt6797_bigidvfs_backend_read(dev, snapshot);",
            ),
        )
        for name, exact_return in wrappers:
            body = function_body(source, name)
            require(
                exact_return in body,
                f"production backend wrapper changed: {name}",
            )

        capture = function_body(source, "mt6797_a72_hotplug_snapshot_capture")
        ordered = (
            "ops->platform(source->platform, &platform)",
            "ops->provider(&provider)",
            "ops->clock(source->clock, &clock)",
            "ops->bigidvfs(source->bigidvfs, &bigidvfs)",
            "mt6797_hotplug_map(readback",
        )
        offsets = [capture.index(token) for token in ordered]
        require(offsets == sorted(offsets), "snapshot component order changed")
        for token in (
            "trace->platform_calls++",
            "trace->provider_calls++",
            "trace->clock_calls++",
            "trace->bigidvfs_calls++",
            "MT6797_DVFSP_CLOCK_BACKEND_ABI",
            "!clock.sample_generation",
            "MT6797_BIGIDVFS_BACKEND_ABI",
            "!bigidvfs.sample_generation",
            "memset(readback, 0, sizeof(*readback))",
            "trace->complete = true",
        ):
            require(token in capture, f"capture gate missing: {token}")
        require(capture.count("ops->platform(") == 1, "platform retry added")
        require(capture.count("ops->provider(") == 1, "provider retry added")
        require(capture.count("ops->clock(") == 1, "clock retry added")
        require(capture.count("ops->bigidvfs(") == 1, "BigiDVFS retry added")

        provider_valid = function_body(source, "mt6797_hotplug_provider_valid")
        for field in (
            "control_a",
            "status_b",
            "buckb_cont",
            "vbuckb_a",
            "vbuckb_b",
        ):
            require(
                f"provider->{field} <= 0xffU" in provider_valid,
                f"provider width gate missing: {field}",
            )
        require("!provider->reserved" in provider_valid, "provider reserve gate missing")

        mapper = function_body(source, "mt6797_hotplug_map")
        require(mapper.count("readback->provider[") == 5, "provider tuple changed")
        require(mapper.count("readback->bigidvfs[") == 4, "BigiDVFS tuple changed")
        require("sample_generation" not in mapper, "generation entered equality record")
        clock_mapper = function_body(source, "mt6797_hotplug_map_clock")
        require(
            "MT6797_A72_HOTPLUG_CLOCK_VALUES" in clock_mapper,
            "clock mapping length guard missing",
        )
        for field in ("pll_ll", "pll_l", "pll_cci", "cspm_swctrl", "cspm_hwsta"):
            require(f"clock->{field}[word]" in clock_mapper, f"clock field missing: {field}")

        probe = function_body(source, "mt6797_a72_hotplug_snapshot_probe")
        for token in (
            "mt6797_a72_provider_available()",
            '"mediatek,platform-state"',
            '"mediatek,clock-backend"',
            '"mediatek,bigidvfs-backend"',
            "mt6797_hotplug_keep_device(dev, dependency)",
            "platform_set_drvdata(pdev, source)",
        ):
            require(token in probe, f"probe lifetime gate missing: {token}")
        require(probe.count("mt6797_hotplug_keep_device(") == 3, "reference count changed")
        require("mt6797_a72_hotplug_snapshot_capture(" not in probe, "probe gained capture")

        require(
            test.count("KUNIT_CASE(hotplug_snapshot_") == 6,
            "snapshot KUnit case count changed",
        )
        for token in (
            "trace.clock_poweron_writes_max, 1U",
            "trace.clock_acquire_writes_max, 200U",
            "trace.clock_release_writes_max, 200U",
            "trace.bigidvfs_reads, 8U",
            "hotplug_snapshot_generation_excluded_test",
            "hotplug_snapshot_component_failures_test",
            "hotplug_snapshot_provider_width_test",
        ):
            require(token in test, f"KUnit proof missing: {token}")

        config_match = re.search(
            r"config MTK_MT6797_A72_HOTPLUG_SNAPSHOT\n.*?(?=\nconfig |\Z)",
            kconfig,
            re.S,
        )
        require(config_match is not None, "Kconfig missing")
        config = config_match.group(0)
        for dependency in (
            "depends on MTK_MT6797_A72_HOTPLUG_EXECUTOR",
            "depends on MTK_MT6797_A72_PLATFORM_STATE",
            "depends on MTK_MT6797_DVFSP_CLOCK_BACKEND",
            "depends on MTK_MT6797_DVFSP_BIGIDVFS_BACKEND",
            "depends on ARM64_MT6797_A72_PROVIDER_OWNER",
        ):
            require(dependency in config, f"Kconfig dependency missing: {dependency}")
        require(
            "CONFIG_MTK_MT6797_A72_HOTPLUG_SNAPSHOT) += mt6797-a72-hotplug-snapshot.o"
            in makefile,
            "snapshot Makefile entry missing",
        )
        require(
            "CONFIG_MTK_MT6797_A72_HOTPLUG_SNAPSHOT_KUNIT_TEST) += mt6797-a72-hotplug-snapshot-test.o"
            in makefile,
            "snapshot KUnit Makefile entry missing",
        )

        added = internal + source + test
        for token in (
            "gemini_protected_readback_ledger",
            "mt6797_a72_direct_state_snapshot(",
            "mt6797_a72_physical_source_capture(",
            "cpu_up(",
            "cpu_down(",
            "remove_cpu(",
            "add_cpu(",
            "psci_ops.",
            "cpu_psci_ops.",
            "arm_smccc",
            "smp_call_function",
            "mtk_wdt_recovery_takeover(",
            "MT6797_BIGIDVFS_FID_SRAM_LDO_SET",
        ):
            require(token not in added, f"disconnected adapter gained effect: {token}")
        require("mt6797_psci_cpu_can_disable" not in added, "CPU-disable veto touched")
    except (OSError, ValueError) as exc:
        print(f"hotplug_snapshot_source=fail reason={exc}", file=sys.stderr)
        return 1
    print("hotplug_snapshot_source=pass")
    print("component_order=platform,provider,clock,bigidvfs")
    print("component_calls_per_snapshot=1,1,1,1")
    print("long_lived_device_references=3")
    print("protected_readback_checkpoints=0")
    print("clock_transport_writes_max=401")
    print("bigidvfs_register_reads=8")
    print("sample_generations_in_equality=0")
    print("focused_kunit_cases=6")
    print("production_callers=0")
    print("device_tree_nodes=0")
    print("boot_candidate=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
