#!/usr/bin/env python3
"""Validate an edited Linux tree for the Gate-6 B2 source contract."""

from __future__ import annotations

import argparse
from pathlib import Path


class ValidationError(RuntimeError):
    """Raised when edited Linux source violates the B2 contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        require(token in text, f"{label} missing token: {token}")


def validate(root: Path) -> None:
    bus = root / "drivers/i2c/busses"
    driver = (bus / "i2c-mt65xx.c").read_text(encoding="utf-8")
    header = (bus / "i2c-mt65xx-gemini-write-contract.h").read_text(
        encoding="utf-8")
    test = (bus / "i2c-mt65xx-gemini-write-test.c").read_text(
        encoding="utf-8")
    kconfig = (bus / "Kconfig").read_text(encoding="utf-8")
    makefile = (bus / "Makefile").read_text(encoding="utf-8")

    require_tokens(header, (
        "struct mtk_i2c_idvfs_short_write_plan",
        "mtk_i2c_idvfs_plan_short_write",
        "mtk_i2c_idvfs_completion_result",
        "mtk_i2c_idvfs_result_after_lease",
        "mtk_i2c_idvfs_transfer_once",
    ), "header")
    require_tokens(driver, (
        '#include "i2c-mt65xx-gemini-write-contract.h"',
        "int mtk_i2c_idvfs_plan_short_write(",
        "void mtk_i2c_idvfs_emit_short_write(",
        "int mtk_i2c_idvfs_completion_result(",
        "int mtk_i2c_idvfs_result_after_lease(",
        "int mtk_i2c_idvfs_transfer_once(",
        "idvfs_short_write = i2c->dev_comp == &mt6797_idvfs_compat",
        "use_dma = short_write.use_dma",
        "addr_reg = idvfs_short_write ? short_write.slave_addr",
        "mtk_i2c_idvfs_emit_short_write(",
        "mtk_i2c_idvfs_completion_result(ret,",
        "mtk_i2c_idvfs_result_after_lease(ret, lease_ret)",
    ), "production driver")
    require("if (!ret && lease_ret)" not in driver,
            "positive transfer success still hides lease failure")
    require(driver.count("ret = __i2c_transfer(adap, msgs, num);") == 1,
            "no-retry helper must invoke the core exactly once")
    require(driver.count(
        "i2c_lock_bus(adap, I2C_LOCK_ROOT_ADAPTER);") == 1,
        "one-shot helper must acquire the root adapter exactly once")
    require(driver.count(
        "i2c_unlock_bus(adap, I2C_LOCK_ROOT_ADAPTER);") == 1,
        "one-shot helper must release the root adapter exactly once")
    require_tokens(kconfig, (
        "config I2C_MT65XX_GEMINI_WRITE_TRANSPORT_KUNIT_TEST",
        "depends on KUNIT=y",
        "depends on I2C_MT65XX=y",
        "registers no adapter or client",
    ), "Kconfig")
    require(
        "obj-$(CONFIG_I2C_MT65XX_GEMINI_WRITE_TRANSPORT_KUNIT_TEST) += "
        "i2c-mt65xx-gemini-write-test.o" in makefile,
        "KUnit object is not isolated behind its option")
    require(test.count("KUNIT_CASE(") == 12, "KUnit case count changed")
    require_tokens(test, (
        "MTK_I2C_TEST_ADDR\t0x2a",
        "MTK_I2C_TEST_BYTE0\t0xa5",
        "MTK_I2C_TEST_BYTE1\t0x5a",
        "mtk_i2c_idvfs_transfer_fake_init(&fake, -EAGAIN)",
        "fake.calls, 1U",
        "fake.lock_calls, 1U",
        "fake.unlock_calls, 1U",
        "fake.locked_during",
        "fake.retries_during, 0U",
        "fake.adap.retries, 1U",
        "mtk_i2c_idvfs_lease_failure_overrides_success",
        "mtk_i2c_idvfs_transport_failure_retains_precedence",
        'kunit_test_suite(mtk_i2c_idvfs_write_contract_suite)',
    ), "KUnit source")
    for forbidden in (
        "0x68", "0x69", "0xda", "0x46", "i2c_add_adapter",
        "i2c_new_client", "ioremap", "debugfs", "sysfs", "procfs",
        "module_param", "OFFSET_START", "I2C_TRANSAC_START", "writel(",
    ):
        require(forbidden not in test,
                f"KUnit source contains forbidden token: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate(root)
    print("validation=mainline-i2c6-write-transport-edited-source")
    print("production_coupling=passed")
    print("kunit_cases=12")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
