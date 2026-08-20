#!/usr/bin/env python3
"""Validate the generated positive-provider patch review."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0293-regulator-restore-DA921x-provider-release-registration.patch",
    "0294-regulator-add-positive-DA921x-Buck-B-provider-transaction.patch",
    "0295-regulator-test-positive-DA921x-Buck-B-provider-transaction.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def paths(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))


def additions(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def additions_for_path(text: str, path: str) -> str:
    marker = f"diff --git a/{path} b/{path}\n"
    require(text.count(marker) == 1, f"patch path boundary changed: {path}")
    section = text.split(marker, 1)[1].split("\ndiff --git ", 1)[0]
    return additions(section)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    patch_dir = parser.parse_args().patch_dir.resolve()
    actual = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(actual == PATCHES, f"unexpected patch inventory: {actual}")
    texts = [(patch_dir / name).read_text(encoding="utf-8") for name in PATCHES]

    for name, text in zip(PATCHES, texts, strict=True):
        require(text.startswith("From "), f"{name}: not a format patch")
        require(
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in text,
            f"{name}: archive identity changed",
        )
        require("Signed-off-by:" not in text, f"{name}: synthetic sign-off forbidden")
    require("Subject: [PATCH 1/3] regulator: restore DA921x provider release" in texts[0],
            "repair subject changed")
    require("Subject: [PATCH 2/3] regulator: add positive DA921x Buck-B" in texts[1],
            "transaction subject changed")
    require("Subject: [PATCH 3/3] regulator: test positive DA921x Buck-B" in texts[2],
            "test subject changed")
    require(paths(texts[0]) == ("drivers/regulator/da9213-legacy-regulator.c",),
            "repair patch paths changed")
    require(paths(texts[1]) == (
        "arch/arm64/Kconfig",
        "drivers/regulator/Kconfig",
        "drivers/regulator/da9213-legacy-provider-contract.h",
        "drivers/regulator/da9213-legacy-regulator.c",
    ), "transaction patch paths changed")
    require(paths(texts[2]) == (
        "drivers/regulator/Kconfig",
        "drivers/regulator/Makefile",
        "drivers/regulator/da9213-legacy-provider-test.c",
    ), "test patch paths changed")

    repair = additions(texts[0])
    transaction = additions(texts[1])
    transaction_driver = additions_for_path(
        texts[1], "drivers/regulator/da9213-legacy-regulator.c"
    )
    test = additions(texts[2])
    require(repair.strip() == ".release = da9213_legacy_provider_release,",
            "repair patch must add only release registration")
    for token in (
        "REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION",
        "u8 payload[2] = { 0x5e, value }",
        "0x01, false",
        "0x00, true",
        "request->transaction_generation",
        "request->transaction_cookie",
        "i2c_lock_bus(adapter, I2C_LOCK_ROOT_ADAPTER)",
        "adapter->retries = 0",
        ".transfer = __i2c_transfer",
        "DA9213_LEGACY_PROVIDER_FAULT_RETAINED",
    ):
        require(token in transaction, f"transaction token missing: {token}")
    require(transaction.count("i2c_lock_bus(") == 2,
            "transaction root-lock count changed")
    for forbidden in (
        "PAGE_CON",
        "regulator_enable(",
        "regulator_set_voltage(",
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
        "writel(",
    ):
        require(forbidden not in transaction_driver,
                f"forbidden transaction token: {forbidden}")
    require(test.count("KUNIT_CASE(") == 6, "KUnit case count changed")
    for token in (
        "DA9213_PROVIDER_TEST_ADDRESS\t0x2a",
        "fake.fail_ordinal = ordinal",
        "fake.short_ordinal = ordinal",
        "1, 3, 4, 5, 7, 9, 10, 11",
        "fake.mismatch_ordinal = 2",
    ):
        require(token in test, f"test token missing: {token}")
    for forbidden in ("i2c_add_adapter", "i2c_new_client", "ioremap", "writel("):
        require(forbidden not in test, f"hardware test token: {forbidden}")

    print("validation=da921x-positive-provider-patches")
    print("patches=3")
    print("kunit_cases=6")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
