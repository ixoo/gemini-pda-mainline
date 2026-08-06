#!/usr/bin/env python3
"""Reject representative mutations of the resource-only provider boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = Path(__file__).with_name("validate.py")
SPEC = importlib.util.spec_from_file_location("provider_validate", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def main() -> None:
    original = VALIDATOR.patch_text()
    mutations = {
        "writable-set-voltage": (".get_voltage_sel =", ".set_voltage_sel ="),
        "writable-enable": (".is_enabled =", ".enable ="),
        "writable-disable": (".is_enabled =", ".disable ="),
        "writable-mode": (".is_enabled =", ".set_mode ="),
        "missing-root-lock": ("I2C_LOCK_ROOT_ADAPTER", "I2C_LOCK_MUTATED"),
        "missing-direct-read": ("__i2c_transfer", "i2c_transfer"),
        "wrong-vsel-a": ("0xd7, 0xd9", "0xd8, 0xda"),
        "wrong-enable-b": ("0x5d, 0x5e", "0x5c, 0x5f"),
        "wrong-voltage-floor": ("300000", "301000"),
        "provider-symbol-removed": (
            "REGULATOR_DA9213_LEGACY_PROVIDER",
            "REGULATOR_DA9213_LEGACY_PROVIDR",
        ),
    }

    rejected = 0
    for name, (old, new) in mutations.items():
        count = -1 if name in {"missing-root-lock", "provider-symbol-removed"} else 1
        mutated = original.replace(old, new, count)
        try:
            VALIDATOR.validate_patch(mutated)
        except RuntimeError:
            print(f"mutation={name} result=rejected")
            rejected += 1
        else:
            raise RuntimeError(f"mutation was accepted: {name}")

    print(f"mutations_rejected={rejected}/{len(mutations)}")
    print("status=PASS")


if __name__ == "__main__":
    main()
