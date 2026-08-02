#!/usr/bin/env python3
"""Validate the Stage 27 post-event identification lifecycle inputs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROFILE = "da921x-post-event-lifecycle"
FRAGMENT_NAME = "configs/gemini-da921x-post-event-lifecycle.fragment"
FRAGMENT = ROOT / FRAGMENT_NAME
MANIFEST = ROOT / "kernel/manifest.json"
SERIES = ROOT / "patches/series"
DRIVER_PATCH = ROOT / "patches/v7.1.3/0124-regulator-add-read-only-legacy-DA921x-identification.patch"
ORACLE_PATCH = ROOT / "patches/v7.1.3/0126-i2c-mediatek-add-read-only-I2C6-lifecycle-oracle.patch"
RUNTIME = ROOT / "experiments/2026-08-01-da921x-post-event-lifecycle/scripts/run-lifecycle-check.sh"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


manifest = json.loads(MANIFEST.read_text())
profiles = manifest["config"]["profiles"]
profile = profiles.get(PROFILE)
require(profile is not None, "profile is absent")
expected = profiles["da921x-natural-device-add"]["fragments"] + [FRAGMENT_NAME]
require(profile["fragments"] == expected, "profile does not exactly extend Stage 26")
require("patch_series" not in profile, "profile bypasses the canonical series")

series = [
    line.strip()
    for line in SERIES.read_text().splitlines()
    if line.strip() and not line.startswith("#")
]
require(len(series) == 136, "canonical patch count changed")
require(series[-1].endswith("0147-i2c-observe-Gemini-DA921x-natural-device-add.patch"),
        "Stage 26 observation is not the canonical tail")

fragment = FRAGMENT.read_text()
for exact in (
    "CONFIG_REGULATOR_DA9213_LEGACY=y",
    'CONFIG_LOCALVERSION="-gemini-da921x-life27"',
    "g_ether.iProduct=Gemini-L-DA921x-Life27",
    "maxcpus=8",
    "initcall_blacklist=mt6797_a72_power_driver_init",
):
    require(fragment.count(exact) == 1, f"fragment token is not exact: {exact}")

driver = DRIVER_PATCH.read_text()
for exact in (
    "DA9213_LEGACY_PASSES\t\t2",
    "__i2c_transfer(client->adapter, msgs, ARRAY_SIZE(msgs));",
    "devm_i2c_new_dummy_device",
    "legacy direct-address identity matched; no regulators exposed",
):
    require(exact in driver, f"driver contract token absent: {exact}")
for forbidden in (
    "devm_regulator_register",
    "regmap_write",
    ".remove =",
    ".shutdown =",
):
    require(forbidden not in driver, f"driver gained forbidden path: {forbidden}")

oracle = ORACLE_PATCH.read_text()
for exact in (
    "oracle_combined_pointer_reads",
    "oracle_register_data_write_messages",
    "oracle_other_address_transfers",
    "mtk_i2c_record_lifecycle_oracle(i2c, msgs, num);",
):
    require(exact in oracle, f"oracle token absent: {exact}")

runtime = RUNTIME.read_text()
for exact in (
    "/bin/busybox mount -o remount,rw /sys",
    "/bin/busybox mount -o remount,ro /sys",
    'printf \'%s\' 1-0068 >"$driver/unbind"',
    'printf \'%s\' 1-0068 >"$driver/bind"',
    'require_phase initial "$initial_status" 14 8 6',
    'require_phase post_unbind "$post_unbind_status" 14 8 6',
    'require_phase post_rebind "$post_rebind_status" 28 16 12',
    '[ "$(counter "$status" dma_starts)" = 0 ] || abort "$phase-dma_starts"',
    '[ "$(/bin/busybox cat /sys/kernel/gemini_da921x_dual_modalias_stage)" = 20 ]',
    'dummy_driver=/sys/bus/i2c/drivers/dummy',
    'wait_for_page2_dummy || abort rebound-page2-dummy-timeout',
    'while [ "$attempt" -lt 30 ]; do',
    "trap cleanup EXIT HUP INT TERM",
):
    require(runtime.count(exact) == 1, f"runtime boundary is not exact: {exact}")
for forbidden in (
    "i2c_transfer",
    "i2cset",
    "insmod",
    "/dev/mmc",
    "/proc/sysrq-trigger",
    "reboot -",
):
    require(forbidden not in runtime, f"runtime helper gained forbidden path: {forbidden}")

print("validation=da921x-post-event-lifecycle-static")
print(f"profile={PROFILE}")
print("baseline=runtime-proven-stage-26")
print("driver_delta=module-to-built-in")
print("initial_unbind_rebind=14-to-14-to-28")
print("sysfs_cleanup_trap=present")
print("provider_register_write_a72_storage=absent")
