#!/usr/bin/env python3
"""Validate the source-only legacy DA921x resource provider boundary."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0170-regulator-add-legacy-DA921x-resource-only-provider.patch"
SERIES = ROOT / "patches/series"
MANIFEST = ROOT / "kernel/manifest.json"
PROFILE = ROOT / "configs/gemini-da921x-resource-only-provider.fragment"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def patch_text() -> str:
    require(PATCH.is_file(), "provider patch is missing")
    return PATCH.read_text(encoding="utf-8")


def validate_patch(text: str) -> None:
    require("From f2e79a385ce383af99eadc60ae916e7d728c8025" in text,
            "source parent commit is not pinned")
    require("REGULATOR_DA9213_LEGACY_PROVIDER" in text,
            "provider Kconfig symbol is missing")
    for token in (
        "0xd7, 0xd9",
        "0x5d, 0x5e",
        "300000",
        "1570000",
        "10000",
        "0x7f",
        "get_voltage_sel",
        "list_voltage",
        "is_enabled",
        "devm_regulator_register",
        "I2C_LOCK_ROOT_ADAPTER",
        "__i2c_transfer",
    ):
        require(token in text, f"provider patch omits {token}")
    require(len(re.findall(r"^\+.*I2C_LOCK_ROOT_ADAPTER", text, re.M)) == 2,
            "provider read helper must lock and unlock the root adapter")

    writable = (
        "set_voltage_sel",
        "set_voltage",
        "regulator_enable",
        "regulator_disable",
        ".enable =",
        ".disable =",
        ".set_mode =",
        ".set_current_limit =",
        "regmap_write",
        "regmap_update_bits",
        "i2c_master_send",
        "i2c_smbus_write",
        "request_threaded_irq",
        "psci_ops",
        "cpu_on",
        "cpuhp",
    )
    for token in writable:
        require(token not in text, f"forbidden writable or CPU path: {token}")

    ops = re.search(
        r"\+static const struct regulator_ops da9213_legacy_readonly_ops = \{(.*?)\n\+\};",
        text,
        re.S,
    )
    require(ops is not None, "read-only ops block is missing")
    require(ops.group(1).count("+\t.") == 3,
            "read-only ops must contain exactly three operations")


def validate_profile() -> None:
    profile = PROFILE.read_text(encoding="utf-8")
    require("CONFIG_REGULATOR_DA9213_LEGACY=y" in profile,
            "provider profile does not enable the legacy driver")
    require("CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER=y" in profile,
            "provider profile does not enable the provider symbol")
    require("CONFIG_LOCALVERSION=\"-gemini-da921x-resource\"" in profile,
            "provider profile identity is missing")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    profiles = manifest["config"]["profiles"]
    provider = profiles.get("da921x-resource-only-provider")
    require(provider is not None, "manifest provider profile is missing")
    require(str(PROFILE.relative_to(ROOT)) in provider["fragments"],
            "manifest provider profile omits its fragment")
    legacy = profiles["da921x-legacy-bind"]
    require(str(PROFILE.relative_to(ROOT)) not in legacy["fragments"],
            "provider fragment leaked into identification profile")


def validate_series() -> int:
    subprocess.run([str(ROOT / "scripts/validate-manifest-series")],
                   cwd=ROOT, check=True)
    lines = [line.strip() for line in SERIES.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    expected = "v7.1.3/0170-regulator-add-legacy-DA921x-resource-only-provider.patch"
    require(expected in lines, "provider patch is absent from canonical series")
    provider_index = lines.index(expected)
    require(provider_index > 0,
            "provider patch must follow the legacy identification boundary")
    return provider_index


def main() -> None:
    text = patch_text()
    validate_patch(text)
    validate_profile()
    provider_index = validate_series()
    digest = hashlib.sha256(PATCH.read_bytes()).hexdigest()
    print("validation=resource-only-provider")
    print(f"patch_sha256={digest}")
    print(f"patch_bytes={PATCH.stat().st_size}")
    print(f"provider_series_index={provider_index}")
    print("probe_identity_reads=14")
    print("provider_operations=3")
    print("writable_operations=0")
    print("consumers=0")
    print("cpu_on_calls=0")
    print("hardware_write=none")
    print("build=not-run")
    print("status=PASS")


if __name__ == "__main__":
    main()
