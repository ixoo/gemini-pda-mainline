#!/usr/bin/env python3
"""Reject unsafe or non-attributable pre-ramoops ledger mutations."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("preledger_validate", SCRIPT_DIR / "validate.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def rejected(manifest: dict[str, object], series: str, patch: str, fragment: str) -> bool:
    try:
        validator.validate_inputs(manifest, series, patch, fragment)
    except (AssertionError, ValueError):
        return True
    return False


def main() -> None:
    manifest = json.loads(validator.MANIFEST_PATH.read_text(encoding="utf-8"))
    series = validator.SERIES_PATH.read_text(encoding="utf-8")
    patch = validator.PATCH_PATH.read_text(encoding="utf-8")
    fragment = validator.FRAGMENT_PATH.read_text(encoding="utf-8")
    validator.validate_inputs(manifest, series, patch, fragment)

    cases: list[tuple[dict[str, object], str, str, str]] = []
    cases.append((manifest, series.replace(validator.PATCH_NAME + "\n", ""), patch, fragment))

    drift = copy.deepcopy(manifest)
    drift["config"]["profiles"][validator.PROFILE]["fragments"].insert(
        -1, "configs/gemini-post-ramoops-checkpoint.fragment"
    )
    cases.append((drift, series, patch, fragment))
    cases.append((manifest, series, patch, fragment + "CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y\n"))
    cases.append((manifest, series, patch.replace("default n", "default y", 1), fragment))
    cases.append((manifest, series, patch.replace("0x444bb000ULL", "0x444ba000ULL", 1), fragment))
    cases.append((manifest, series, patch.replace("GEMINI_PRELEDGER_SLOT_COUNT\t4", "GEMINI_PRELEDGER_SLOT_COUNT\t3", 1), fragment))
    cases.append((manifest, series, patch.replace("crc32=45d42a00", "crc32=00000000", 1), fragment))
    cases.append((manifest, series, patch.replace("memblock_is_region_reserved(addr, size)", "true", 1), fragment))
    cases.append((manifest, series, patch.replace("no-map", "mapped-ok", 1), fragment))
    cases.append((manifest, series, patch.replace("memcpy_toio", "regmap_write", 1), fragment))
    cases.append((manifest, series, patch.replace("gemini_preledger_armed = false;", "gemini_preledger_armed = true;", 1), fragment))
    cases.append((manifest, series, patch.replace("early_initcall(gemini_preledger_early_checkpoint);", "device_initcall(gemini_preledger_early_checkpoint);", 1), fragment))
    cases.append((manifest, series, patch.replace(
        "ret = platform_driver_register(&ramoops_driver);",
        "regulator_set_voltage(NULL, 0, 0);\n+\tret = platform_driver_register(&ramoops_driver);",
        1,
    ), fragment))

    count = sum(rejected(*case) for case in cases)
    if count != len(cases):
        raise AssertionError(f"only {count} of {len(cases)} mutations were rejected")
    print("validation=mainline-pre-ramoops-ledger-mutations")
    print(f"negative_mutations_rejected={count}")
    print("result=pass")


if __name__ == "__main__":
    main()
