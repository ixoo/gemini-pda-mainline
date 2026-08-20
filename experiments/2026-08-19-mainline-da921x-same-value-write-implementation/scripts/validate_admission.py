#!/usr/bin/env python3
"""Validate canonical admission of the Gate-6 same-value-write patches."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCHES = {
    "0290-i2c-mediatek-extend-Gemini-entry-ledger-attribution.patch":
        "b95d13d3f9210be7988a5f705f2e53739ed86548fd4552a1c564848a101d1a83",
    "0291-regulator-add-bounded-DA921x-same-value-write.patch":
        "e4e89bfcfc2857e1ae31c7f4440e4ad795a308d08d5feddfe27964e76c2b531c",
    "0292-regulator-test-bounded-DA921x-same-value-write.patch":
        "a1b51131595b4f836e089e1a88c5031431477fe46a3db7a12770b98249b8a686",
}
PRODUCTION_FRAGMENT = "configs/gemini-da921x-same-value-write.fragment"
KUNIT_FRAGMENT = "configs/gemini-da921x-same-value-write-kunit.fragment"


class AdmissionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AdmissionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_lines(path: Path) -> tuple[str, ...]:
    return tuple(line for line in path.read_text().splitlines()
                 if line.startswith("CONFIG_") or
                 line.startswith("# CONFIG_"))


def validate() -> None:
    tail = [f"v7.1.3/{name}" for name in PATCHES]
    series = [line for line in (ROOT / "patches/series").read_text().splitlines()
              if line and not line.startswith("#")]
    require(series[-3:] == tail, "canonical patch tail changed")
    require(len(series) == len(set(series)), "canonical series has duplicates")

    for name, expected in PATCHES.items():
        path = ROOT / "patches/v7.1.3" / name
        require(path.is_file() and not path.is_symlink(),
                f"canonical patch is missing or unsafe: {name}")
        require(sha256(path) == expected, f"canonical patch drift: {name}")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profiles = manifest["config"]["profiles"]
    require(len(profiles) == 87, "point-in-time profile audit count changed")
    parent = profiles["da921x-i2c6-firmware-writer-transaction-window"]
    production = profiles["da921x-same-value-write"]
    kunit = profiles["da921x-same-value-write-kunit"]
    require(production == {
        "base": "defconfig",
        "fragments": parent["fragments"] + [PRODUCTION_FRAGMENT],
    }, "production profile ancestry changed")
    require(kunit == {
        "base": "defconfig",
        "fragments": production["fragments"] + [KUNIT_FRAGMENT],
    }, "KUnit profile ancestry changed")

    require(config_lines(ROOT / PRODUCTION_FRAGMENT) == (
        "CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y",
        "CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y",
        "# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set",
        "CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y",
        "CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE=y",
        'CONFIG_LOCALVERSION="-gemini-da921x-same-write"',
    ), "production fragment changed")
    require(config_lines(ROOT / KUNIT_FRAGMENT) == (
        "CONFIG_KUNIT=y",
        "CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST=y",
        'CONFIG_LOCALVERSION="-gemini-da921x-same-write-kunit"',
    ), "KUnit fragment changed")

    subprocess.run([str(ROOT / "scripts/validate-manifest-series")],
                   cwd=ROOT, check=True)
    subprocess.run([str(ROOT / "scripts/test-manifest-series-invariant")],
                   cwd=ROOT, check=True)


def main() -> None:
    validate()
    print("validation=da921x-same-value-write-canonical-admission")
    print("canonical_patches=3")
    print("profiles_checked=87")
    print("focused_profiles=2")
    print("hardware_action=none")
    print("boot_candidate=false")
    print("physical_da921x_write_authorized=false")
    print("cpu8_cpu9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
