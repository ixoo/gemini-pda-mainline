#!/usr/bin/env python3
"""Validate provider-readiness repair source after each phase."""

from __future__ import annotations

import argparse
from pathlib import Path


PHASES = ("dependency", "binding", "tests")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def section(text: str, start: str, end: str) -> str:
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def validate_dependency(root: Path) -> None:
    observer = (
        root
        / "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer.c"
    ).read_text(encoding="utf-8")
    internal = (
        root
        / "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer-internal.h"
    ).read_text(encoding="utf-8")

    capture = section(observer, "mt6797_a72_pp_capture(", "static struct device *")
    order = (
        "memset(snapshot, 0, sizeof(*snapshot))",
        "if (!provider)",
        "return -EPROBE_DEFER",
        "ops->platform(context, platform, &snapshot->platform)",
        "ops->checkpoint(context, 0)",
        "ops->provider(context, &snapshot->provider)",
        "ops->checkpoint(context, 1)",
    )
    positions = [capture.index(token) for token in order]
    require(positions == sorted(positions), "provider gate precedes all capture effects")
    require(capture.count("ops->platform(") == 1, "one platform call")
    require(capture.count("ops->checkpoint(") == 2, "two checkpoints")
    require(capture.count("ops->provider(") == 1, "one provider call")
    require("for (" not in capture and "while (" not in capture, "no capture retry")
    require("struct device *provider" in capture, "capture provider argument")
    require("struct device *provider" in internal, "header provider argument")

    helper = section(
        observer,
        "mt6797_a72_platform_provider_get_provider(",
        "static void mt6797_a72_pp_log",
    )
    helper_order = (
        'of_parse_phandle(dev->of_node, "mediatek,provider", 0)',
        'of_device_is_compatible(node, "dlg,da9214-legacy")',
        "of_find_i2c_device_by_node(node)",
        "device_is_bound(&provider->dev)",
        "return &provider->dev",
    )
    positions = [helper.index(token) for token in helper_order]
    require(positions == sorted(positions), "exact provider resolution order")
    require(helper.count("of_find_i2c_device_by_node(") == 1, "one I2C lookup")
    require(helper.count("of_node_put(node)") == 2, "node release on both paths")
    require(helper.count("put_device(&provider->dev)") == 1, "unready ref release")
    for forbidden in ("i2c_transfer(", "i2c_smbus_", "regmap_", "readl(", "writel("):
        require(forbidden not in helper, f"lookup hardware operation: {forbidden}")

    probe = section(
        observer,
        "static int mt6797_a72_platform_provider_probe",
        "static const struct of_device_id",
    )
    probe_order = (
        "mt6797_a72_platform_provider_get_device(dev)",
        "mt6797_a72_platform_provider_get_provider(dev)",
        "mt6797_a72_pp_capture(platform, provider",
        "mt6797_a72_pp_log(dev, &snapshot)",
        "put_device(provider)",
        "put_device(platform)",
    )
    positions = [probe.index(token) for token in probe_order]
    require(positions == sorted(positions), "probe holds both refs through capture/log")
    require(probe.count("mt6797_a72_pp_capture(") == 1, "one capture")
    require(probe.count("put_device(provider)") == 1, "provider release")
    require(probe.count("put_device(platform)") == 1, "platform release")
    require("provider_ready_gate=passed" in observer, "terminal readiness token")
    require(observer.count("mt6797_a72_provider_snapshot(") == 1, "provider call unchanged")
    for forbidden in (
        "mt6797_a72_provider_acquire(",
        "mt6797_a72_provider_release(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "i2c_transfer(",
        "regmap_write(",
        "cpu_up(",
        "cpu_down(",
    ):
        require(forbidden not in observer, f"forbidden production operation: {forbidden}")


def validate_binding(root: Path) -> None:
    binding = (
        root
        / "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-platform-provider-snapshot-observer.yaml"
    ).read_text(encoding="utf-8")
    require(binding.count("mediatek,provider") == 3, "provider property/required/example")
    require("Phandle to the bound legacy DA9214 regulator endpoint." in binding,
            "provider binding description")
    require("mediatek,provider = <&da9214>;" in binding, "provider example")
    require("additionalProperties: false" in binding, "closed binding")


def validate_tests(root: Path) -> None:
    tests = (
        root
        / "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer-test.c"
    ).read_text(encoding="utf-8")
    require(tests.count("KUNIT_CASE(") == 7, "seven focused cases")
    not_ready = section(
        tests,
        "static void mt6797_platform_provider_not_ready_test",
        "static void mt6797_platform_provider_success_test",
    )
    for token in (
        "memset(&snapshot, 0xff, sizeof(snapshot))",
        "mt6797_a72_pp_capture(&platform, NULL",
        "ret, -EPROBE_DEFER",
        "state.platform_calls, 0U",
        "state.provider_calls, 0U",
        "state.event_count, 0U",
        "mt6797_pp_expect_zero(test, &snapshot)",
    ):
        require(token in not_ready, f"not-ready proof: {token}")
    require(tests.count("struct device provider = { };") == 6, "ready providers")
    require(tests.count("mt6797_a72_pp_capture(&platform, &provider") == 7,
            "every ready call passes provider")
    for forbidden in (
        "arm_smccc_smc(",
        "readl(",
        "writel(",
        "i2c_transfer(",
        "gemini_protected_readback_ledger_checkpoint(",
        "mt6797_a72_provider_snapshot(",
        "cpu_up(",
    ):
        require(forbidden not in tests, f"test physical operation: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    validators = {
        "dependency": (validate_dependency,),
        "binding": (validate_dependency, validate_binding),
        "tests": (validate_dependency, validate_binding, validate_tests),
    }
    for validator in validators[args.phase]:
        validator(root)
    print(f"source_validation={args.phase}-pass")


if __name__ == "__main__":
    main()
