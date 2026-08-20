#!/usr/bin/env python3
"""Validate the three generated Gate-6 implementation patches."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0290-i2c-mediatek-extend-Gemini-entry-ledger-attribution.patch",
    "0291-regulator-add-bounded-DA921x-same-value-write.patch",
    "0292-regulator-test-bounded-DA921x-same-value-write.patch",
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def paths(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))


def additions(text: str) -> str:
    return "\n".join(line[1:] for line in text.splitlines()
                     if line.startswith("+") and not line.startswith("+++"))


def validate(patch_dir: Path) -> None:
    actual = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(actual == PATCHES, f"unexpected patch inventory: {actual}")
    texts = [(patch_dir / name).read_text(encoding="utf-8") for name in PATCHES]
    for name, text in zip(PATCHES, texts, strict=True):
        require(text.startswith("From "), f"{name}: not format-patch")
        require("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in text,
                f"{name}: archive identity changed")
        require("Signed-off-by:" not in text, f"{name}: synthetic sign-off forbidden")

    require("Subject: [PATCH 1/3] i2c: mediatek: extend Gemini entry ledger" in texts[0],
            "patch 0290 subject changed")
    require("Subject: [PATCH 2/3] regulator: add bounded DA921x same-value" in texts[1],
            "patch 0291 subject changed")
    require("Subject: [PATCH 3/3] regulator: test bounded DA921x same-value" in texts[2],
            "patch 0292 subject changed")
    require(paths(texts[0]) == (
        "drivers/i2c/busses/Kconfig",
        "drivers/i2c/busses/i2c-mt65xx.c",
        "include/linux/i2c-mt65xx-gemini-ledger.h",
    ), "patch 0290 paths changed")
    require(paths(texts[1]) == (
        "drivers/regulator/Kconfig",
        "drivers/regulator/da9213-legacy-regulator.c",
        "drivers/regulator/da9213-legacy-write-contract.h",
    ), "patch 0291 paths changed")
    require(paths(texts[2]) == (
        "drivers/regulator/Kconfig",
        "drivers/regulator/Makefile",
        "drivers/regulator/da9213-legacy-write-test.c",
    ), "patch 0292 paths changed")

    ledger, production, kunit = map(additions, texts)
    for token in ("entry_ledger=v2", "u8 second_byte;", "second_byte_valid",
                  "mtk_i2c_gemini_verify_read_ledger",
                  "lockdep_assert_held(&adapter->bus_lock)"):
        require(token in ledger, f"0290 missing: {token}")
    for token in ("run-same-value-write-20260819-a",
                  "u8 payload[2] = { 0xda, 0x46 }",
                  "i2c_lock_bus(adapter, I2C_LOCK_ROOT_ADAPTER)",
                  "adapter->retries = 0", ".transfer = __i2c_transfer",
                  "ops->delay(10000, 11000)", "second_writes=0"):
        require(token in production, f"0291 missing: {token}")
    require(production.count("da9213_legacy_same_value_write(") == 2,
            "0291 must contain one definition and one call")
    for token in ("DA9213_TEST_ADDRESS\t0x2a", "DA9213_TEST_ACTIONS\t12",
                  "da9213_same_value_transfer_failures",
                  "da9213_same_value_mismatches",
                  "da9213_same_value_ledger_refusal",
                  "fake.write_payload[1]", "fake.adapter.retries, 1"):
        require(token in kunit, f"0292 missing: {token}")
    require(kunit.count("KUNIT_CASE(") == 6, "KUnit case count changed")
    for forbidden in ("i2c_add_adapter", "i2c_new_client", "ioremap", "writel(",
                      "I2C_TRANSAC_START"):
        require(forbidden not in kunit, f"KUnit hardware token: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    validate(args.patch_dir.resolve())
    print("validation=da921x-same-value-write-format-patches")
    print("patches=3")
    print("changed_paths=9")
    print("synthetic_signoff=absent")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
