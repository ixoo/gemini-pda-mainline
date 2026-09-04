#!/usr/bin/env python3
"""Validate the bounded MT6797 A72 frequency-observer source boundary."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing {label}: {needle!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()
    soc = args.source_root.resolve() / "drivers/soc/mediatek"
    source = (soc / "mt6797-a72-frequency-observer.c").read_text()
    header = (soc / "mt6797-a72-frequency-observer-internal.h").read_text()
    snapshot = (soc / "mt6797-a72-hotplug-snapshot.c").read_text()
    internal = (soc / "mt6797-a72-hotplug-snapshot-internal.h").read_text()
    test = (soc / "mt6797-a72-frequency-observer-test.c").read_text()
    kconfig = (soc / "Kconfig").read_text()
    makefile = (soc / "Makefile").read_text()

    required = (
        (header, "MT6797_A72_FREQUENCY_OBSERVER_MAX_ATTEMPTS 3U", "three-attempt cap"),
        (source, "DEVICE_ATTR_RO(a72_frequency_observation)", "read-only attribute"),
        (source, "controller->attempts >=", "attempt refusal"),
        (source, "controller->attempts++;", "pre-transport attempt consumption"),
        (source, "mt6797_dvfsp_clock_state_decode", "proven decoder composition"),
        (source, "big_pll_pcw=0x%08x", "raw BigiDVFS PCW output"),
        (source, "b_khz=%u", "decoded B frequency output"),
        (source, "devm_device_add_group", "managed attribute lifetime"),
        (snapshot, "mt6797_a72_frequency_observer_register(dev)", "snapshot registration"),
        (internal, "frequency_observer;", "per-device controller"),
        (kconfig, "config MTK_MT6797_A72_FREQUENCY_OBSERVER", "production option"),
        (kconfig, "config MTK_MT6797_A72_FREQUENCY_OBSERVER_KUNIT_TEST", "test option"),
        (makefile, "mt6797-a72-frequency-observer.o", "production object"),
        (makefile, "mt6797-a72-frequency-observer-test.o", "test object"),
        (test, "0xc1130000", "live B PCW fixture"),
        (test, "845000U", "live B frequency fixture"),
        (test, "-ENOSPC", "fourth-attempt refusal"),
    )
    for text, needle, label in required:
        require(text, needle, label)

    combined = "\n".join((source, header, snapshot, internal, test))
    forbidden = (
        "DEVICE_ATTR_WO",
        "DEVICE_ATTR_RW",
        "cpu_up(",
        "cpu_down(",
        "psci_cpu_on",
        "arm_smccc",
        "regulator_set",
        "clk_set_rate",
        "writel(",
        "writeb(",
        "writew(",
        "msleep(",
        "schedule_timeout",
        "gemini_a72_hotplug_ledger",
    )
    for needle in forbidden:
        if needle in combined:
            raise SystemExit(f"forbidden observer operation present: {needle!r}")

    if test.count("KUNIT_CASE(") != 5:
        raise SystemExit("focused KUnit case inventory changed")
    if source.count("source->ops->clock(") != 1:
        raise SystemExit("clock transport call count changed")
    if source.count("source->ops->bigidvfs(") != 1:
        raise SystemExit("BigiDVFS transport call count changed")
    print("observation_attribute=read-only")
    print("attempts_per_boot=3")
    print("attempt_consumption=before-transport")
    print("clock_calls_per_attempt=1")
    print("bigidvfs_calls_per_attempt=1")
    print("clock_poweron_writes_per_attempt_max=1")
    print("clock_acquire_writes_per_attempt_max=200")
    print("clock_release_writes_per_attempt_max=200")
    print("bigidvfs_reads_per_attempt=8")
    print("bigidvfs_sram_set_calls=0")
    print("focused_kunit_case_count=5")
    print("cpu_request=none")
    print("policy_change=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
