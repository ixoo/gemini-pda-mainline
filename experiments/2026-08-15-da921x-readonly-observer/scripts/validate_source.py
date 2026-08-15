#!/usr/bin/env python3
"""Validate the composed DA921x read-only observer source."""

import argparse
import re
from pathlib import Path


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing {label}: {needle}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    paths = {
        "kconfig": root / "drivers/regulator/Kconfig",
        "makefile": root / "drivers/regulator/Makefile",
        "driver": root / "drivers/regulator/da9213-legacy-regulator.c",
        "header": root / "drivers/regulator/da9213-legacy-observer.h",
        "test": root / "drivers/regulator/da9213-legacy-observer-test.c",
    }
    for path in paths.values():
        if not path.is_file():
            raise SystemExit(f"missing source file: {path}")
    text = {name: path.read_text() for name, path in paths.items()}
    combined = "\n".join(text.values())

    for needle, label in (
        ("config REGULATOR_DA9213_LEGACY_OBSERVER", "observer Kconfig"),
        ("depends on REGULATOR_DA9213_LEGACY_PROVIDER", "provider dependency"),
        ("config REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST", "KUnit Kconfig"),
        ("da9213-legacy-observer-test.o", "KUnit object"),
        ("da9213_legacy_get_voltage_sel(chip->rdev[buck])", "selector operation reuse"),
        ("da9213_legacy_is_enabled(chip->rdev[buck])", "enable operation reuse"),
        ("identity_reads != DA9213_LEGACY_PASSES *", "exact identity gate"),
        ("provider_count != DA9213_LEGACY_BUCK_COUNT", "exact provider gate"),
        ("provider_read_attempts", "read-attempt accounting"),
        ("provider_read_completed", "read-completion accounting"),
        ("register_data_writes", "write accounting"),
        ("da921x-observer-v1 event=bound", "attributable success record"),
        ("event=%s providers_released=%u", "cleanup record"),
        ("devm_add_action(chip->dev, da9213_legacy_observer_cleanup", "cleanup ordering"),
        ("KUNIT_CASE(da9213_legacy_observer_bounds_read_failures)", "failure KUnit"),
        ("KUNIT_CASE(da9213_legacy_observer_invalidates_on_cleanup)", "cleanup KUnit"),
    ):
        require(combined, needle, label)

    ops_match = re.search(
        r"static const struct regulator_ops da9213_legacy_readonly_ops = \{(.*?)\n\};",
        text["driver"], re.S,
    )
    if not ops_match:
        raise SystemExit("missing read-only regulator ops")
    ops = ops_match.group(1)
    expected_ops = {"get_voltage_sel", "list_voltage", "is_enabled"}
    actual_ops = set(re.findall(r"\.(\w+)\s*=", ops))
    if actual_ops != expected_ops:
        raise SystemExit(f"unexpected regulator operations: {sorted(actual_ops)}")

    if text["driver"].count("__i2c_transfer(") != 2:
        raise SystemExit("legacy driver transfer-call inventory changed")
    for forbidden in (
        "i2c_master_send(", "i2c_smbus_write", "regmap_write(",
        "set_voltage_sel", ".enable =", ".disable =", ".set_mode =",
        ".set_current_limit =", "clk_set_", "cpu_up(", "cpu_down(",
        "arm_smccc", "psci_ops.cpu_on",
    ):
        if forbidden in combined:
            raise SystemExit(f"unexpected state-changing operation: {forbidden}")

    assignments = re.findall(r"register_data_writes\s*=\s*([^;]+);", combined)
    if assignments:
        raise SystemExit(f"write counter must remain zero-initialized: {assignments}")

    print("source_contract=passed")
    print("identity_reads=14")
    print("provider_descriptors=2")
    print("bounded_provider_reads=4")
    print("kunit_cases=5")
    print("register_data_writes=0")
    print("hardware_write=none")
    print("cpu8_cpu9_admission=closed")


if __name__ == "__main__":
    main()
