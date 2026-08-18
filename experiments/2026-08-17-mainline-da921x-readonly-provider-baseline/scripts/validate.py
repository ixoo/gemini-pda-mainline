#!/usr/bin/env python3
"""Validate the LK-repaired DA921x read-only provider source boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH_REL = "v7.1.3/0282-arm64-dts-mediatek-add-Gemini-LK-CPU-clock-rates.patch"
PATCH_SHA256 = "f08aca1b6bf9e0e2c59835edc975b78763aa6fdc6172f52fdc0c690982cc7f17"
FRAGMENT_REL = "configs/gemini-da921x-lk-clock-readonly-provider.fragment"
PROFILE = "da921x-lk-clock-readonly-provider"
PARENT = "da921x-modules-arm64-entry-ledger"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def additions(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    patch = ROOT / "patches" / PATCH_REL
    patch_text = patch.read_text(encoding="utf-8")
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    require(digest == PATCH_SHA256, "CPU-clock patch checksum changed")

    series = [
        line.strip() for line in (ROOT / "patches/series").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    require(series[-1] == PATCH_REL, "CPU-clock patch is not canonical tail")
    require(series.count(PATCH_REL) == 1, "CPU-clock patch is not unique")

    added = additions(patch_text)
    rates = {
        1391000000: 4,
        1950000000: 4,
        2288000000: 2,
    }
    require(added.count("&cpu") == 10, "patch does not update exactly ten CPUs")
    for rate, count in rates.items():
        require(added.count(f"clock-frequency = <{rate}>;") == count,
                f"wrong CPU count for {rate}")
    for forbidden in (
        "status =", "enable-method", "compatible =", "cpu_up(", "cpu_down(",
        "psci_ops.cpu_on", "arm_smccc", "clock-frequency = <0>",
    ):
        require(forbidden not in added, f"CPU patch adds forbidden change: {forbidden}")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profiles = manifest["config"]["profiles"]
    profile = profiles[PROFILE]
    parent = profiles[PARENT]
    require(profile.get("patch_series", "patches/series") == "patches/series",
            "profile does not use canonical series")
    require(profile["base"] == parent["base"], "profile base changed")
    require(profile["fragments"] == parent["fragments"] + [FRAGMENT_REL],
            "profile is not an exact parent extension")

    fragment = (ROOT / FRAGMENT_REL).read_text(encoding="utf-8")
    required = (
        "CONFIG_NVMEM=y",
        "CONFIG_NVMEM_MTK_ATAG_DEVINFO=y",
        "CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y",
        "# CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST is not set",
        'CONFIG_LOCALVERSION="-gemini-da921x-lkro"',
    )
    for line in required:
        require(fragment.count(line) == 1, f"fragment gate missing or duplicated: {line}")
    for forbidden in (
        "ARM64_MT6797_A72_PROVIDER_OWNER=y", "MTK_MT6797_A72_POWER=y",
        "set_voltage", "REGULATOR_ALLOW_BYPASS", "CPU_HOTPLUG_STATE_CONTROL",
    ):
        require(forbidden not in fragment,
                f"fragment opens forbidden boundary: {forbidden}")

    provider_patch = (ROOT / "patches/v7.1.3/0170-regulator-add-legacy-DA921x-resource-only-provider.patch").read_text()
    observer_patch = (ROOT / "patches/v7.1.3/0278-regulator-observe-legacy-DA921x-read-only-provider.patch").read_text()
    provider_added = additions(provider_patch)
    observer_added = additions(observer_patch)
    for operation in (".get_voltage_sel", ".list_voltage", ".is_enabled"):
        require(operation in provider_added, f"read-only provider operation missing: {operation}")
    for forbidden in (
        ".set_voltage_sel", ".enable =", ".disable =", ".set_mode =",
        ".set_current_limit =", "i2c_master_send(", "i2c_smbus_write",
        "regmap_write(", "regmap_update_bits(", "cpu_up(", "cpu_down(",
    ):
        require(forbidden not in provider_added + observer_added,
                f"provider/observer adds state-changing operation: {forbidden}")
    require("register_data_writes=%u" in observer_added,
            "observer lost zero-write attribution")
    require("da921x-observer-v1 event=bound" in observer_added,
            "observer bound record is absent")

    print("validation=mainline-da921x-readonly-provider-baseline")
    print(f"cpu_clock_patch_sha256={digest}")
    print("CPU_clock_properties=10")
    print("profile_parent=exact-runtime-proven-entry-ledger-extension")
    print("LK_devinfo_NVMEM=read-only")
    print("provider_operations=get_voltage_sel,list_voltage,is_enabled")
    print("regulator_consumers=0")
    print("register_data_write_operations=0")
    print("CPU8_CPU9_admission=closed")


if __name__ == "__main__":
    main()
