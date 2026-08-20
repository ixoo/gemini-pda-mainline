#!/usr/bin/env python3
"""Validate the edited Gate-6 implementation source."""

from __future__ import annotations

import argparse
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def between(text: str, start: str, end: str) -> str:
    require(text.count(start) == 1, f"source boundary changed: {start}")
    require(text.count(end) >= 1, f"source boundary changed: {end}")
    return text.split(start, 1)[1].split(end, 1)[0]


def validate(root: Path) -> None:
    controller = (root / "drivers/i2c/busses/i2c-mt65xx.c").read_text()
    i2c_kconfig = (root / "drivers/i2c/busses/Kconfig").read_text()
    public_header = (root / "include/linux/i2c-mt65xx-gemini-ledger.h").read_text()
    regulator = (root / "drivers/regulator/da9213-legacy-regulator.c").read_text()
    regulator_header = (root / "drivers/regulator/da9213-legacy-write-contract.h").read_text()
    regulator_kconfig = (root / "drivers/regulator/Kconfig").read_text()
    regulator_makefile = (root / "drivers/regulator/Makefile").read_text()
    kunit = (root / "drivers/regulator/da9213-legacy-write-test.c").read_text()

    for token in (
        "u8 second_byte;", "bool second_byte_valid;",
        "entry_ledger=v2", "p1=%02x p1v=%u",
        "mtk_i2c_gemini_verify_read_ledger", "lockdep_assert_held(&adapter->bus_lock)",
        "record->second_byte_valid || !record->complete",
        "EXPORT_SYMBOL_GPL(mtk_i2c_gemini_verify_read_ledger)",
    ):
        require(token in controller, f"controller contract missing: {token}")
    require(controller.count("record->second_byte = msgs[0].buf[1]") == 1,
            "second-byte capture changed")
    require("struct mtk_i2c_gemini_read_expectation" in public_header,
            "public expectation type missing")
    require("A read-only verifier can match" in i2c_kconfig,
            "ledger Kconfig boundary missing")

    execution = between(regulator,
                        "int da9213_legacy_same_value_execute(",
                        "#endif\n\n#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE)")
    for token in (
        "i2c_lock_bus(adapter, I2C_LOCK_ROOT_ADAPTER)",
        "ret = ops->verify_ledger(adapter)",
        "adapter->retries = 0", "adapter->retries = saved_retries",
        "i2c_unlock_bus(adapter, I2C_LOCK_ROOT_ADAPTER)",
        "ops->delay(10000, 11000)",
        "u8 payload[2] = { 0xda, 0x46 }",
        "DA9213_LEGACY_SAME_VALUE_FAILED_NO_WRITE",
        "DA9213_LEGACY_SAME_VALUE_FAULTED",
    ):
        require(token in regulator, f"production contract missing: {token}")
    require(execution.count("da9213_legacy_same_value_write(") == 1,
            "execution must have one write call")
    require("i2c_transfer(" not in execution,
            "locked production sequence must not call i2c_transfer")
    require("__i2c_transfer" not in execution,
            "generic sequence must use its production-coupled ops seam")
    for forbidden in ("PAGE_CON", "cpu_up(", "add_cpu(", "regulator_enable(",
                      "regulator_set_voltage("):
        require(forbidden not in execution, f"forbidden execution token: {forbidden}")

    runtime = between(regulator,
                      "#define DA9213_LEGACY_SAME_VALUE_TOKEN",
                      "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT)")
    for token in (
        '"run-same-value-write-20260819-a"',
        ".verify_ledger = da9213_legacy_verify_startup_ledger",
        ".transfer = __i2c_transfer", ".delay = usleep_range",
        "ARRAY_SIZE(da9213_legacy_startup_ledger)",
        "!cpu_online(8) && !cpu_online(9) && num_online_cpus() == 8",
        "same_value_write=v1", "second_writes=0",
    ):
        require(token in runtime, f"runtime coupling missing: {token}")
    require(runtime.count("{ 0x") == 20, "startup expectation count changed")
    require("devm_device_add_group(chip->dev" in regulator and
            "&da9213_legacy_same_value_group" in regulator,
            "one-shot group is not installed")
    require("DA9213_LEGACY_SAME_VALUE_POSTSTATE_COUNT\t4" in regulator_header and
            "DA9213_LEGACY_SAME_VALUE_PREFLIGHT_COUNT\t5" in regulator_header,
            "result bounds changed")
    require("config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE" in regulator_kconfig,
            "production Kconfig missing")
    require("config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST" in regulator_kconfig,
            "KUnit Kconfig missing")
    require("da9213-legacy-write-test.o" in regulator_makefile,
            "KUnit object missing")

    require(kunit.count("KUNIT_CASE(") == 6, "KUnit case count changed")
    for token in (
        "DA9213_TEST_ADDRESS\t0x2a", "DA9213_TEST_ACTIONS\t12",
        "for (ordinal = 1; ordinal <= DA9213_TEST_ACTIONS; ordinal++)",
        "if (ordinal == 6)", "fake.write_payload[0]", "fake.write_payload[1]",
        "fake.retries_during[i], 0U", "fake.adapter.retries, 1",
        "da9213_same_value_ledger_refusal", "fake.transfer_calls, 0U",
        "KUNIT_EXPECT_FALSE(test, fake.unlocked_transfer)",
        "KUNIT_EXPECT_TRUE(test, fake.delay_locked)",
    ):
        require(token in kunit, f"KUnit coverage missing: {token}")
    for forbidden in ("i2c_add_adapter", "i2c_new_client", "ioremap", "writel(",
                      "I2C_TRANSAC_START"):
        require(forbidden not in kunit, f"KUnit hardware token: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    validate(args.source_root.resolve())
    print("validation=da921x-same-value-write-edited-source")
    print("logical_patches=3")
    print("kunit_cases=6")
    print("failure_ordinals=12")
    print("mismatch_ordinals=11")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
