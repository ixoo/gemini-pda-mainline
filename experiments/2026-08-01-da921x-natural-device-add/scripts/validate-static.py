#!/usr/bin/env python3
"""Validate the isolated natural device-add experiment inputs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH_NAME = "v7.1.3/0147-i2c-observe-Gemini-DA921x-natural-device-add.patch"
PATCH = ROOT / "patches" / PATCH_NAME
FRAGMENT = ROOT / "configs/gemini-da921x-natural-device-add.fragment"
MANIFEST = ROOT / "kernel/manifest.json"
SERIES = ROOT / "patches/series"
PROFILE = "da921x-natural-device-add"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


patch = PATCH.read_text()
added = "\n".join(
    line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")
)
fragment = FRAGMENT.read_text()
manifest = json.loads(MANIFEST.read_text())
series = [
    line.strip()
    for line in SERIES.read_text().splitlines()
    if line.strip() and not line.startswith("#")
]

require(series[-1] == PATCH_NAME, "natural device-add patch is not canonical tail")
profile = manifest["config"]["profiles"].get(PROFILE)
require(profile is not None, "manifest profile is absent")
require(
    profile["fragments"][-1] == "configs/gemini-da921x-natural-device-add.fragment",
    "profile does not end with the isolated fragment",
)
require(
    fragment.count("CONFIG_I2C_GEMINI_DA921X_NATURAL_DEVICE_ADD_DIAGNOSTIC=y") == 1,
    "natural device-add gate is not enabled exactly once",
)
require(
    fragment.count('CONFIG_LOCALVERSION="-gemini-da921x-devadd"') == 1,
    "local version is not exact",
)

for exact in (
    "gemini_da921x_natural_device_add_begin(&client->dev.kobj)",
    "gemini_da921x_natural_device_add_end(&client->dev.kobj, status)",
    "atomic_set(&gemini_da921x_dual_modalias_stage, 26);",
    "KERNEL_ATTR_RO(gemini_da921x_natural_device_add);",
):
    require(added.count(exact) == 1, f"unexpected count for {exact!r}")
require(patch.count("status = device_register(&client->dev);") == 1,
        "device_register context is not exact")

for forbidden in (
    "i2c_transfer(",
    "regmap_write(",
    "device_unregister(",
    "device_del(",
    "kobject_uevent(",
    "KERNEL_ATTR_RW(gemini_da921x_natural_device_add)",
    "pr_info(",
    "pr_err(",
):
    require(forbidden not in added, f"forbidden added path: {forbidden}")

require(added.count("gemini_da921x_natural_device_add_callsite_entries") >= 3,
        "call-site entry counter is incomplete")
require(added.count("gemini_da921x_natural_device_add_wrapper_entries") >= 3,
        "wrapper entry counter is incomplete")
require(added.count("gemini_da921x_natural_device_add_public_returns") >= 3,
        "public-return counter is incomplete")
require("listeners)" in added and "broadcast_count)" in added,
        "zero-delivery exit checks are absent")

print("validation=da921x-natural-device-add-static")
print(f"profile={PROFILE}")
print(f"patch={PATCH_NAME}")
print("natural_device_register_boundary=present")
print("natural_uevent_callsite_boundary=present")
print("natural_wrapper_boundary=present")
print("read_only_observation=present")
print("trigger=absent")
print("replay=absent")
print("driver_provider_transfer_register_write=absent")
